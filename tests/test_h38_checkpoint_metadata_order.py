"""Synthetic safetensors-HEADER-only tests: no tensor values or CUDA."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/benchmark/inspect-h38-checkpoint-metadata-order.py"
RUNNER = ROOT / "scripts/benchmark/check-h38-checkpoint-metadata-order.sh"
spec = importlib.util.spec_from_file_location("h38_ckpt_metadata", SCRIPT)
assert spec and spec.loader
ckpt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ckpt)


def create_fixture(root: Path, *, revisit: bool = False) -> None:
    """Make 18 tiny valid-header checkpoint shards; no safetensors dependency."""
    files = [f"model-{i:05d}-of-00018.safetensors" for i in range(1, 19)]
    per_file: list[dict[str, bytes]] = [{} for _ in files]
    for layer in range(48):
        shard = layer * 18 // 48
        for i in range(2):
            key = f"model.layers.{layer}.mlp.experts.0.w{i}_weight"
            per_file[shard][key] = bytes([layer % 256])
    if revisit:
        per_file[-1]["model.layers.0.mlp.experts.0.w99_weight"] = b"1"
    index: dict[str, str] = {}
    for filename, tensors in zip(files, per_file):
        offsets: dict[str, dict] = {}
        body = b""
        for key, data in sorted(tensors.items()):
            offsets[key] = {"dtype": "U8", "shape": [len(data)],
                            "data_offsets": [len(body), len(body) + len(data)]}
            body += data
            index[key] = filename
        raw = json.dumps(offsets, separators=(",", ":")).encode("utf-8")
        (root / filename).write_bytes(struct.pack("<Q", len(raw)) + raw + body)
    (root / "model.safetensors.index.json").write_text(
        json.dumps({"weight_map": index}), encoding="utf-8"
    )


def synthetic_key_reader(path: Path) -> list[str]:
    with path.open("rb") as fh:
        length = struct.unpack("<Q", fh.read(8))[0]
        return sorted(json.loads(fh.read(length)))


class H38CheckpointMetadataOrderTests(unittest.TestCase):
    def test_valid_48_layers_18_shards(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            create_fixture(root)
            result = ckpt.scan_checkpoint(root, synthetic_key_reader)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["shard_count"], 18)
            self.assertEqual(result["routed_expert_tensor_count"], 96)
            self.assertEqual(result["routed_expert_layer_count"], 48)
            self.assertEqual(result["routed_expert_revisited_layers"], [])
            self.assertEqual(result["routed_expert_max_overlapping_intervals"], 1)
            self.assertEqual(
                result["scenario_peak_routed_bytes_release_at_last_routed_key"], 2)
            self.assertFalse(result["exact_h38_loader_order_contract_verified"])
            self.assertFalse(result["all_layerwise_weight_buffers_bounded"])
            self.assertFalse(result["host_stability_qualified"])

    def test_revisit_across_shards_fails_even_with_all_layers_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            create_fixture(root, revisit=True)
            result = ckpt.scan_checkpoint(root, synthetic_key_reader)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["routed_expert_revisited_layers"], [0])
            self.assertGreater(result["routed_expert_max_overlapping_intervals"], 1)

    def test_index_missing_or_mismatched_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            create_fixture(root)
            index = root / "model.safetensors.index.json"
            index.unlink()
            with self.assertRaisesRegex(ValueError, "missing_model_safetensors_index"):
                ckpt.scan_checkpoint(root, synthetic_key_reader)
            create_fixture(root)
            meta = json.loads(index.read_text(encoding="utf-8"))
            key = next(iter(meta["weight_map"]))
            meta["weight_map"][key] = "model-00018-of-00018.safetensors"
            index.write_text(json.dumps(meta), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "index_header_mapping_mismatch"):
                ckpt.scan_checkpoint(root, synthetic_key_reader)

    def test_header_bounds_and_key_order_mismatch_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            create_fixture(root)
            bad = root / "model-00001-of-00018.safetensors"
            old = bad.read_bytes()
            bad.write_bytes(struct.pack("<Q", ckpt.MAX_HEADER + 1) + old[8:])
            with self.assertRaisesRegex(ValueError, "invalid_header_bounds"):
                ckpt.scan_checkpoint(root, synthetic_key_reader)
            bad.write_bytes(old)
            with self.assertRaisesRegex(ValueError, "safe_open_header_key_mismatch"):
                ckpt.scan_checkpoint(root, lambda p: [])

    def test_extra_and_path_traversal_shards_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            create_fixture(root)
            (root / "unindexed.safetensors").write_bytes(b"dummy")
            with self.assertRaisesRegex(ValueError, "unindexed_shard_files_present"):
                ckpt.scan_checkpoint(root, synthetic_key_reader)
            (root / "unindexed.safetensors").unlink()
            index = root / "model.safetensors.index.json"
            data = json.loads(index.read_text(encoding="utf-8"))
            key = next(iter(data["weight_map"]))
            data["weight_map"][key] = "../outside.safetensors"
            index.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe_or_invalid_index_entries"):
                ckpt.scan_checkpoint(root, synthetic_key_reader)

    def test_runner_is_strictly_read_only(self) -> None:
        code = RUNNER.read_text(encoding="utf-8")
        for required in (
            "--runtime runc --network none --read-only",
            "--cap-drop ALL --security-opt no-new-privileges",
            "--pull never", "--user 65534:65534",
            "H38_CKPT_METADATA_MODEL_DIR", "absolute_checkpoint_directory_required",
            "type=bind", "readonly", "dirty_checkout", "H38_image_id_mismatch",
        ):
            self.assertIn(required, code)
        for dangerous in ("--gpus all", "docker build", "docker pull ",
                          "systemctl", "drop_caches", "compact_memory", "sysctl -w"):
            self.assertNotIn(dangerous, code)
        result = subprocess.run(["bash", "-n", str(RUNNER)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        env = dict(os.environ)
        env.pop("H38_CKPT_METADATA_TARGET_SHA", None)
        env.pop("H38_CKPT_METADATA_MODEL_DIR", None)
        result = subprocess.run(["bash", str(RUNNER)], env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing_exact_checkout_sha", result.stderr)

    def test_tempfile_mount_is_private_bounded_and_only_writable_location(self) -> None:
        code = RUNNER.read_text(encoding="utf-8")
        # Regression for original DGX INVALID: Python tempfile on a fully
        # read-only rootfs had no writable tmp directory as UID 65534.
        self.assertIn(
            "--tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777",
            code,
        )
        self.assertIn("--env TMPDIR=/tmp", code)
        self.assertEqual(code.count("--tmpfs "), 1)
        self.assertEqual(code.count("--mount "), 2)
        self.assertIn("--runtime runc --network none --read-only", code)
        self.assertIn("--user 65534:65534", code)
        self.assertIn("type=bind,src=${MODEL_DIR},dst=/opt/checkpoint,readonly", code)
        for unsafe in ("--privileged", "--user 0:0", "--gpus all",
                       "chmod -R", "docker exec", "--network host"):
            self.assertNotIn(unsafe, code)

    def test_tmpfs_is_not_a_host_checkpoint_write_mount(self) -> None:
        code = RUNNER.read_text(encoding="utf-8")
        self.assertIn("--tmpfs /tmp:", code)
        self.assertNotIn("dst=/tmp", code)
        self.assertNotIn("src=/tmp", code)
        self.assertNotIn("src=${MODEL_DIR},dst=/opt/checkpoint,rw", code)

    def test_no_payload_access_in_analyzer_source(self) -> None:
        code = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn(".get_tensor(", code)
        self.assertNotIn(".get_slice(", code)
        self.assertNotIn("torch.load(", code)
        self.assertIn("handle.read(length)", code)
        self.assertIn("return list(handle.keys())", code)


if __name__ == "__main__":
    unittest.main()
