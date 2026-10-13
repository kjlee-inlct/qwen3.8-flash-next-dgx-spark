"""Tests for read-only preserved H38 launch configuration analysis."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/benchmark/inspect-h38-preserved-loader-config.py"
RUNNER = ROOT / "scripts/benchmark/check-h38-preserved-loader-config.sh"
spec = importlib.util.spec_from_file_location("h38_archive_inspector", SCRIPT)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def fixture(folder: Path, extra: list[str] | None = None,
            prefetch_log: bool = True) -> None:
    cmd = ["--model", "/model", "--served-model-name", "orcarouter"]
    cmd.extend(extra or [])
    inspect = [{
        "Image": audit.IMAGE_ID,
        "Config": {
            "Image": audit.IMAGE,
            "Cmd": cmd,
            "Env": [
                "VLLM_PLE_MMAP=1",
                "VLLM_QSA_EXACT_TOPK=1",
                "QWEN38_MARLIN_CANONICAL_ORDER=1",
                "QWEN38_MARLIN_CANONICAL_SCOPE=decoder",
                "HUGGING_FACE_HUB_TOKEN=SECRET_DO_NOT_EXPOSE",
            ],
        },
        "Mounts": [{
            "Destination": "/model",
            "Source": "/home/inlc/models/qwen3.8-flash-next-orcarouter",
        }],
    }]
    (folder / "candidate-inspect.json").write_text(
        json.dumps(inspect), encoding="utf-8")
    (folder / "candidate-cmd.json").write_text(
        json.dumps(cmd), encoding="utf-8")
    if prefetch_log:
        (folder / "startup-phase.txt").write_text(
            "Auto-prefetch is disabled because network fs not detected\n",
            encoding="utf-8")


class PreservedLoaderTests(unittest.TestCase):
    def test_absence_of_flag_not_claimed_as_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            fixture(folder)
            result = audit.analyze(folder)
            self.assertEqual(result["explicit_loader_cli_flags"]["load_format"],
                             {"state": "NOT_EXPLICIT", "value": None})
            self.assertEqual(result["recorded_safetensors_prefetch_log"],
                             "AUTO_PREFETCH_DISABLED_LOG_OBSERVED")
            self.assertFalse(result["actual_effective_vllm_load_config_proven"])
            self.assertFalse(result["actual_tensor_iteration_proven"])
            self.assertFalse(result["metadata_order_gate_overridden"])

    def test_explicit_flag_and_sanitized_loader_extra_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            fixture(folder, [
                "--load-format=safetensors",
                "--safetensors-load-strategy", "lazy",
                "--enable-expert-parallel",
                "--model-loader-extra-config",
                '{"enable_multithread_load":false,"num_threads":4,"private_key":"secret"}',
            ], prefetch_log=False)
            data = audit.analyze(folder)
            flags = data["explicit_loader_cli_flags"]
            self.assertEqual(flags["load_format"]["value"], "safetensors")
            self.assertEqual(flags["safetensors_load_strategy"]["value"], "lazy")
            self.assertEqual(flags["enable_expert_parallel"]["value"], "present")
            self.assertEqual(flags["model_loader_extra_config"]["value"],
                             {"enable_multithread_load": False, "num_threads": 4})
            self.assertEqual(flags["model_loader_extra_config"]["other_fields_present_count"], 1)
            self.assertNotIn("secret", json.dumps(data))
            self.assertEqual(data["recorded_safetensors_prefetch_log"],
                             "NO_PREFETCH_LOG_EVIDENCE")

    def test_speculative_json_always_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            fixture(folder, ["--speculative-config", '{"draft":"PASSWORD_PRIVATE"}'])
            data = audit.analyze(folder)
            self.assertEqual(data["recorded_speculative_config"],
                             {"state": "EXPLICIT_REDACTED", "value": None})
            self.assertNotIn("PASSWORD_PRIVATE", json.dumps(data))

    def test_fail_closed_archive_missing_or_corrupt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with self.assertRaisesRegex(ValueError, "missing_capture"):
                audit.analyze(folder)
            fixture(folder)
            (folder / "candidate-cmd.json").write_text('["wrong"]', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "saved_cmd_differs"):
                audit.analyze(folder)
            fixture(folder)
            path = folder / "candidate-inspect.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data[0]["Image"] = "sha256:other"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "candidate_image_id_mismatch"):
                audit.analyze(folder)

    def test_symlinked_capture_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            fixture(folder)
            path = folder / "candidate-cmd.json"
            path.rename(folder / "other.json")
            path.symlink_to(folder / "other.json")
            with self.assertRaisesRegex(ValueError, "unsafe_or_non_file"):
                audit.analyze(folder)

    def test_duplicate_flag_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            fixture(folder, ["--load-format", "safetensors", "--load-format=eager"])
            with self.assertRaisesRegex(ValueError, "ambiguous_duplicate_flag"):
                audit.analyze(folder)

    def test_cli_redacts_secrets_and_host_mount_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            fixture(folder)
            run = subprocess.run(["python3", str(SCRIPT), "--archive-dir",
                                  str(folder)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("H38_PRESERVED_LOADER_CONFIG_GATE=PASS", run.stdout)
            self.assertNotIn("SECRET_DO_NOT_EXPOSE", run.stdout)
            self.assertNotIn("/home/inlc/models", run.stdout)

    def test_runner_never_starts_docker_or_changes_service(self) -> None:
        code = RUNNER.read_text(encoding="utf-8")
        for marker in ("exact_checkout_sha_required", "dirty_checkout",
                       "preserved_archive_not_available",
                       "scope=existing_archive_only_no_docker_no_model_no_gpu_no_service",
                       "python3 -B"):
            self.assertIn(marker, code)
        for unsafe in ("docker run", "docker start", "systemctl ",
                       "sudo ", "sysctl ", "drop_caches", "chmod ",
                       "rm -rf", "mkdir -p"):
            self.assertNotIn(unsafe, code)
        syntax = subprocess.run(["bash", "-n", str(RUNNER)],
                                capture_output=True, text=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        env = dict(os.environ)
        env.pop("H38_PRESERVED_LOADER_TARGET_SHA", None)
        env.pop("H38_PRESERVED_LOADER_ARCHIVE_DIR", None)
        guard = subprocess.run(["bash", str(RUNNER)], env=env,
                               capture_output=True, text=True)
        self.assertEqual(guard.returncode, 2)
        self.assertIn("exact_checkout_sha_required", guard.stderr)


if __name__ == "__main__":
    unittest.main()
