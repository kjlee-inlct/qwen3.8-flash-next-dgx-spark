"""Synthetic-only catplusplus M1 workflow compatibility and safety tests."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/runtime/catplusplus-m1.py"
SPEC = importlib.util.spec_from_file_location("catplusplus_m1", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class CatplusplusM1Tests(unittest.TestCase):
    @staticmethod
    def call(action: str, state: str | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if state is not None:
            env["XDG_STATE_HOME"] = state
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), action],
            text=True, capture_output=True, env=env, check=False, timeout=10,
        )

    def test_plan_parity_has_all_12_safe_stage_markers(self):
        result = self.call("plan")
        self.assertEqual(result.returncode, 0, result.stderr)
        for required in (
            "02 EXACT_PROTECTED_OLD_IDENTITY_AND_LIFECYCLE_LOCK",
            "03 UNIQUE_CANDIDATE_DOCKER_CREATE_ONLY",
            "04 PERSIST_EXACT_ID_AND_ARM_WATCHDOG_BEFORE_START",
            "05 EXACT_ID_START_AND_WATCHDOG_HEARTBEAT",
            "06 EXACT_MODEL_API_READY",
            "07 POST_READY_180_SECOND_SOAK",
            "08 INFERENCE_SMOKE_AND_RM_AUDIT",
            "09 TERMINAL_B_BENCH_ADMISSION_WITH_LEASE",
            "10 LLAMA_BENCHY_C1_PP512_2048_TG128_WARMUP1_RUNS3",
            "11 FOREGROUND_EXPLICIT_STOP_EXACT_ID",
            "12 PRESERVE_RAW_JSON_KERNEL_MEMORY_AND_DOCKER_EVIDENCE",
            "CATPLUSPLUS_M1_START_CONTROLLER=NOT_IMPLEMENTED",
            "CATPLUSPLUS_M1_KV16G=PROPOSED_UNQUALIFIED",
            "CATPLUSPLUS_M1_BENCHMARK=NOT_MEASURED",
        ):
            self.assertIn(required, result.stdout)
        self.assertEqual(result.stdout.count("CATPLUSPLUS_M1_STAGE="), 12)

    def test_status_missing_state_does_not_create_directory(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root) / "nonexistent"
            result = self.call("status", str(state))
            self.assertEqual(result.returncode, 0)
            self.assertIn("CATPLUSPLUS_M1_SESSION=ABSENT", result.stdout)
            self.assertIn("CATPLUSPLUS_M1_LIVE_READY=NOT_QUALIFIED", result.stdout)
            self.assertFalse(state.exists())

    def test_preflight_is_explicitly_blocked_and_never_claims_ready(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.call("preflight", root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("CATPLUSPLUS_M1_GATE_CHECKPOINT=BLOCKED_", result.stdout)
            self.assertIn("CATPLUSPLUS_M1_GATE_MIXED_LOADER=BLOCKED_", result.stdout)
            self.assertIn("CATPLUSPLUS_M1_GATE_FP8_PLE=BLOCKED_", result.stdout)
            self.assertIn("CATPLUSPLUS_M1_GATE_MEMORY_RM=BLOCKED_", result.stdout)
            self.assertIn("CATPLUSPLUS_M1_ADMISSION=BLOCKED_", result.stdout)
            self.assertIn("CATPLUSPLUS_M1_DOCKER_GPU_MODEL_DOWNLOAD=NOT_PERFORMED", result.stdout)
            self.assertNotIn("PREFLIGHT=PASS", result.stdout)

    def test_run_and_bench_admission_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            for action in ("run", "bench-admission"):
                with self.subTest(action=action):
                    result = self.call(action, root)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("CATPLUSPLUS_M1_DOCKER_ACTION=NONE", result.stdout)
                    self.assertIn("CATPLUSPLUS_M1_BENCHMARK=NOT_MEASURED", result.stdout)
                    self.assertNotIn("READY_FOR_BENCH=", result.stdout)

    def test_reconcile_without_journal_is_read_only_noop(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.call("reconcile", root)
            self.assertEqual(result.returncode, 0)
            self.assertIn("CATPLUSPLUS_M1_RECONCILE=NO_SESSION_OR_JOURNAL", result.stdout)
            self.assertFalse((Path(root) / "qwen38-spark").exists())

    def test_cannot_launder_fake_ready_journal_or_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root) / "qwen38-spark/catplusplus-m1"
            state.mkdir(parents=True)
            journal = state / "active.json"
            record = {"schema": 1, "model": MOD.MODEL,
                      "revision": MOD.REVISION, "phase": "ready_for_bench",
                      "id": "a" * 64}
            journal.write_text(json.dumps(record), encoding="utf-8")
            result = self.call("status", root)
            self.assertEqual(result.returncode, 0)
            self.assertIn("SESSION=JOURNAL_UNATTESTED", result.stdout)
            self.assertIn("SESSION_DOCKER_ID=NOT_ATTESTED", result.stdout)
            self.assertNotIn("BENCH_ADMISSION=PASS", result.stdout)
            result = self.call("bench-admission", root)
            self.assertEqual(result.returncode, 2)
            journal.unlink()
            journal.symlink_to(Path(root) / "untrusted")
            result = self.call("status", root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("journal path is a symlink", result.stderr)

    def test_source_audit_offline_fixture_advances_only_static_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "extra/inference").mkdir(parents=True)
            (root / "config.json").write_text(json.dumps({
                "quantization_config": {
                    "quant_method": "modelopt_mixed",
                    "quant_algo": "MIXED_PRECISION",
                    "quantized_layers": {
                        "model.layers.0.linear_attn.in_proj_qkvz": {
                            "quant_algo": "MXFP8",
                        },
                    },
                },
                "text_config": {"ple_embedding_dtype": "float8_e4m3fn"},
            }), encoding="utf-8")
            (root / "extra/inference/inference_qwen38_flash_next_sglang.sh").write_text(
                "python3 -m sglang.launch_server "
                "--ple-offload-embedding --ple-offload-backend file\n",
                encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "source-audit",
                 "--offline-dir", str(root)],
                cwd=ROOT, capture_output=True, text=True, check=False, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                "CATPLUSPLUS_M1_SOURCE_DECLARATIONS=PRESENT_NOT_ENGINE_ATTESTED",
                result.stdout)
            self.assertIn("CATPLUSPLUS_M1_FUSED_QKVZ_ALIAS_COUNT=1", result.stdout)
            self.assertIn("CATPLUSPLUS_M1_FUSED_QKVZ_MXFP8_ALIAS_COUNT=1", result.stdout)
            self.assertIn("CATPLUSPLUS_M1_FUSED_QKVZ_NON_MXFP8_ALIAS_COUNT=0", result.stdout)
            self.assertIn("CATPLUSPLUS_M1_FP8_PLE_DTYPE=float8_e4m3fn", result.stdout)
            self.assertIn("CATPLUSPLUS_M1_ENGINE_LOADER=NOT_ATTESTED_BY_SOURCE_TEXT",
                          result.stdout)
            self.assertIn("CATPLUSPLUS_M1_LIVE_ADMISSION=BLOCKED_", result.stdout)
            self.assertIn("CATPLUSPLUS_M1_DOCKER_GPU_MODEL_DOWNLOAD=NOT_PERFORMED",
                          result.stdout)

    def test_offline_fixture_must_not_change_live_action_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "run",
                 "--offline-dir", tmp],
                cwd=ROOT, capture_output=True, text=True, check=False, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertIn("--offline-dir is only permitted for source-audit",
                          result.stderr)

    def test_python_m1_is_never_an_unapproved_live_runner(self):
        script = SCRIPT.read_text(encoding="utf-8")
        for banned in (
            '"docker", "run"', '"docker", "create"', '"docker", "start"',
            '"docker", "stop"', "subprocess.run(", "subprocess.Popen(",
            "urllib.request", "urlopen(", "hf download", "snapshot_download(",
        ):
            self.assertNotIn(banned, script)
        with mock.patch.object(MOD, "read_journal", return_value=None), \
             mock.patch.object(MOD, "plan", wraps=MOD.plan):
            self.assertEqual(MOD.blocked("run"), 2)


if __name__ == "__main__":
    unittest.main()
