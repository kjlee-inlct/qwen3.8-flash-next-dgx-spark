from __future__ import annotations

import stat
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
GATE = ROOT / "scripts" / "benchmark" / "run-h38-managed-migration-gate.sh"
H38_ENTRY = ROOT / "scripts" / "prepare-h38-image.sh"


class H38ManagedMigrationGateTests(unittest.TestCase):
    def test_live_gate_shell_syntax_and_executable_mode(self) -> None:
        self.assertTrue(
            GATE.stat().st_mode & stat.S_IXUSR,
            "managed H38 live gate must remain executable in git archive releases",
        )
        result = subprocess.run(
            ["bash", "-n", str(GATE)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_h38_image_entrypoint_is_stable_and_executable(self) -> None:
        self.assertTrue(H38_ENTRY.stat().st_mode & stat.S_IXUSR)
        text = H38_ENTRY.read_text(encoding="utf-8")
        self.assertIn("runtime/prepare-h38-image.sh", text)

    def test_gate_requires_exact_clean_checkout_and_previous_attestation(self) -> None:
        text = GATE.read_text(encoding="utf-8")
        self.assertIn("H38_MANAGED_TARGET_SHA", text)
        self.assertIn("rev-parse HEAD", text)
        self.assertIn("status --porcelain=v1 --untracked-files=all", text)
        self.assertIn("previous runtime commit attestation is missing", text)
        self.assertIn("previous runtime attestation does not match immutable current release", text)
        self.assertIn("previous runtime attestation does not match the live container", text)
        self.assertIn("OOMKilled", text)
        self.assertIn("stale runtime rollback container exists before migration", text)

    def test_gate_uses_only_atomic_cross_release_refresh(self) -> None:
        text = GATE.read_text(encoding="utf-8")
        self.assertIn(
            'bash "${UPDATE_RELEASE}" "${TARGET_SHA}" --refresh-profile-defaults',
            text,
        )
        self.assertNotIn("./install.sh --model orcarouter --refresh-profile-defaults", text)
        self.assertNotIn('bash "${UPDATE_TRANSITION}" prepare "${TARGET_SHA}"', text)
        self.assertIn("release-profile refresh transition is not idle", text)
        self.assertIn("settings transaction is not idle or has stale artifact", text)
        self.assertIn("runtime adoption marker is still pending", text)
        self.assertIn("runtime-adopt-${suffix}.env", text)

    def test_gate_records_matched_baseline_and_h38_identity(self) -> None:
        text = GATE.read_text(encoding="utf-8")
        self.assertIn("--decode-tokens 384", text)
        self.assertIn("--decode-repeats 5", text)
        self.assertIn("baseline-decode-median.txt", text)
        self.assertIn("vllm-orcarouter-v029-h38-decoder-scope:v1", text)
        self.assertIn("qwen38.h38scope", text)
        self.assertIn("QWEN38_MARLIN_CANONICAL_ORDER=1", text)
        self.assertIn("QWEN38_MARLIN_CANONICAL_SCOPE=decoder", text)
        self.assertIn("VLLM_PLE_MMAP=1", text)
        self.assertIn("VLLM_QSA_EXACT_TOPK=1", text)
        self.assertIn("--kv-cache-memory-bytes", text)
        self.assertIn("17179869184", text)
        self.assertIn('bash "${DOCTOR}" --strict', text)

    def test_gate_keeps_functional_and_host_stability_independent(self) -> None:
        text = GATE.read_text(encoding="utf-8")
        self.assertIn("FUNCTIONAL=", text)
        self.assertIn("HOST_STABILITY=", text)
        self.assertIn("NV_ERR_NO_MEMORY|_memdescAllocInternal", text)
        self.assertIn("kernel-window.rc", text)
        self.assertIn("KERNEL_WINDOW_RC", text)
        self.assertIn("kernel evidence window collection failed", text)
        self.assertIn('elif [[ "${KERNEL_WINDOW_RC}" != 0 ]]', text)
        self.assertIn("strict NVIDIA RM no-memory evidence observed", text)
        self.assertIn("memory protection intervened during measured migration window", text)
        self.assertIn("H38_MANAGED_FUNCTIONAL=", text)
        self.assertIn("H38_MANAGED_HOST_STABILITY=", text)
        self.assertIn("upload-summary.txt", text)

    def test_benchmark_gate_uses_stable_cross_category_entrypoints(self) -> None:
        text = GATE.read_text(encoding="utf-8")
        self.assertNotIn("/scripts/lib/", text)
        self.assertNotIn("/scripts/lifecycle/", text)
        self.assertNotIn("/scripts/runtime/", text)
        self.assertIn("/scripts/state_file.py", text)
        self.assertIn("/scripts/release-profile-refresh-transition.sh", text)
        self.assertIn("/scripts/prepare-h38-image.sh", text)


if __name__ == "__main__":
    unittest.main()
