"""Offline fixture-only source gate tests; no HuggingFace/Docker/GPU calls."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/model/audit_catplusplus_loader_source.py"
SPEC = importlib.util.spec_from_file_location("catplusplus_source_audit", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def config(qkvz: bool = True) -> dict:
    layers = {
        "model.layers.0.linear_attn.in_proj_qkvz": {"quant_algo": "MXFP8"},
        "model.layers.1.mlp.experts": {"quant_algo": "NVFP4"},
    }
    if not qkvz:
        layers.pop("model.layers.0.linear_attn.in_proj_qkvz")
    return {
        "quantization_config": {
            "quant_method": "modelopt_mixed",
            "quant_algo": "MIXED_PRECISION",
            "quantized_layers": layers,
        },
        "text_config": {"ple_embedding_dtype": "float8_e4m3fn"},
    }


def launcher() -> str:
    return (
        "#!/usr/bin/env bash\n"
        "sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'\n"
        "python3 -m sglang.launch_server \\\n"
        " --host 0.0.0.0 --ple-offload-embedding \\\n"
        " --ple-offload-backend file \\\n"
        " --enable-hierarchical-cache \\\n"
        " --hicache-storage-backend file \\\n"
        " --mem-fraction-static 0.925 \\\n"
        " --speculative-algorithm NEXTN \\\n"
        " --speculative-num-steps 2 \\\n"
        " --moe-runner-backend flashinfer_cutlass\n"
    )


def prepare(folder: Path, *, fused=True, shell=None) -> None:
    (folder / "extra/inference").mkdir(parents=True)
    (folder / "config.json").write_text(
        json.dumps(config(qkvz=fused)), encoding="utf-8")
    (folder / AUDIT.LAUNCHER).write_text(
        launcher() if shell is None else shell, encoding="utf-8")


class LoaderSourceAuditTests(unittest.TestCase):
    def test_pinned_two_file_allowlist_and_no_weight_paths(self) -> None:
        self.assertEqual(set(AUDIT.ALLOWED), {
            "config.json",
            "extra/inference/inference_qwen38_flash_next_sglang.sh",
        })
        for path in ("model-00001-of-00096.safetensors",
                     "extra/packages/vllm.bundle", "README.md", "../etc/passwd"):
            with self.assertRaisesRegex(AUDIT.SourceAuditBlocked,
                                        "NOT_ALLOWLISTED"):
                AUDIT.source_bytes(path, None)

    def test_valid_source_declarations_are_not_runtime_admission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare(root)
            result = AUDIT.audit(root)
            self.assertEqual(result["revision"], AUDIT.REVISION)
            self.assertEqual(result["transport"], "OFFLINE_FIXTURE")
            self.assertEqual(result["source_declarations"],
                             "PRESENT_NOT_ENGINE_ATTESTED")
            self.assertTrue(result["config"]["fused_qkvz_quantization_declared"])
            self.assertTrue(result["config"]["fp8_ple_dtype_declared"])
            self.assertTrue(result["publisher_launcher"]["script_operational_hazards"]["sudo_command"])
            self.assertTrue(result["publisher_launcher"]["script_operational_hazards"]["public_bind"])
            self.assertTrue(result["publisher_launcher"]["script_operational_hazards"]["cache_drop_command"])
            self.assertFalse(result["engine_source_or_wheel_attested"])
            self.assertFalse(result["physical_gb10_memory_attested"])
            self.assertEqual(result["live_admission"],
                             "BLOCKED_ENGINE_LOADER_AND_MEMORY_NOT_ATTESTED")
            self.assertFalse(result["gpu_execution"])
            self.assertFalse(result["weight_download"])

    def test_fused_alias_requires_explicit_mxfp8_per_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare(root)
            cfg = config()
            key = "model.layers.0.linear_attn.in_proj_qkvz"
            for bad_algo in ("NVFP4", None):
                with self.subTest(quant_algo=bad_algo):
                    if bad_algo is None:
                        cfg["quantization_config"]["quantized_layers"][key].pop("quant_algo", None)
                    else:
                        cfg["quantization_config"]["quantized_layers"][key]["quant_algo"] = bad_algo
                    (root / "config.json").write_text(
                        json.dumps(cfg), encoding="utf-8")
                    result = AUDIT.audit(root)
                    self.assertEqual(result["source_declarations"],
                                     "MISSING_EXPECTED_DECLARATIONS")
                    self.assertEqual(result["config"]["fused_qkvz_quantized_alias_count"], 1)
                    self.assertEqual(result["config"]["fused_qkvz_mxfp8_alias_count"], 0)
                    self.assertEqual(result["config"]["fused_qkvz_non_mxfp8_alias_count"], 1)
                    self.assertFalse(result["config"]["fused_qkvz_quantization_declared"])

    def test_missing_fused_alias_is_not_silently_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare(root, fused=False)
            result = AUDIT.audit(root)
            self.assertEqual(result["source_declarations"],
                             "MISSING_EXPECTED_DECLARATIONS")

    def test_missing_ple_offload_flag_is_not_silently_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare(root, shell="python3 -m sglang.launch_server")
            result = AUDIT.audit(root)
            self.assertEqual(result["source_declarations"],
                             "MISSING_EXPECTED_DECLARATIONS")

    def test_offline_cli_source_only_and_reports_blocked_live(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare(root)
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "audit",
                 "--offline-dir", str(root)],
                cwd=ROOT, capture_output=True, text=True, timeout=10,
                check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("CATPLUSPLUS_SOURCE_QKVZ_ALIAS_COUNT=1",
                          result.stdout)
            self.assertIn("CATPLUSPLUS_SOURCE_DECLARATIONS=PRESENT_NOT_ENGINE_ATTESTED",
                          result.stdout)
            self.assertIn("CATPLUSPLUS_LAUNCHER_HAZARD_SUDO_COMMAND=PRESENT_DO_NOT_EXECUTE",
                          result.stdout)
            self.assertIn("CATPLUSPLUS_LIVE_ADMISSION=BLOCKED_", result.stdout)
            self.assertIn("CATPLUSPLUS_DOCKER_WEIGHTS_HOST_MUTATION=NONE",
                          result.stdout)
            self.assertNotIn("READY=PASS", result.stdout)

    def test_fixture_symlink_and_large_source_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare(root)
            (root / AUDIT.CONFIG).unlink()
            (root / AUDIT.CONFIG).symlink_to(root / AUDIT.LAUNCHER)
            with self.assertRaisesRegex(AUDIT.SourceAuditBlocked, "SYMLINK"):
                AUDIT.audit(root)
            (root / AUDIT.CONFIG).unlink()
            (root / AUDIT.CONFIG).write_bytes(b"x" * (AUDIT.ALLOWED[AUDIT.CONFIG] + 1))
            with self.assertRaisesRegex(AUDIT.SourceAuditBlocked, "OVERSIZED"):
                AUDIT.audit(root)

    def test_bad_quant_table_rejected(self) -> None:
        cfg = config()
        cfg["quantization_config"]["quantized_layers"] = None
        with self.assertRaisesRegex(AUDIT.SourceAuditBlocked, "QUANTIZED_LAYER"):
            AUDIT.scan_config(cfg)

    def test_remote_never_follows_redirects(self) -> None:
        fake_req = mock.Mock()
        handler = AUDIT.NoRedirect()
        with self.assertRaisesRegex(AUDIT.SourceAuditBlocked, "REDIRECT"):
            handler.redirect_request(fake_req, None, 302, "Found", {}, "https://unexpected.invalid")

    def test_no_unbounded_network_or_exec_surface(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("subprocess.run(", "subprocess.Popen(", "os.system(",
                          "docker run", "docker start", "hf download",
                          "snapshot_download(", "shell=True"):
            self.assertNotIn(forbidden, source)
        self.assertIn("reply.read(limit + 1)", source)


if __name__ == "__main__":
    unittest.main()
