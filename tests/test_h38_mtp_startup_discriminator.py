from __future__ import annotations

import stat
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNNER = ROOT / "scripts" / "benchmark" / "run-h38-mtp-startup-discriminator.sh"


class H38MtpStartupDiscriminatorTests(unittest.TestCase):
    def test_runner_is_executable_and_shell_valid(self) -> None:
        self.assertTrue(RUNNER.stat().st_mode & stat.S_IXUSR)
        result = subprocess.run(
            ["bash", "-n", str(RUNNER)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_runner_changes_only_speculative_decode_for_candidate(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("MODEL_PROFILE=orcarouter", text)
        self.assertIn('VLLM_IMAGE="${H38_IMAGE}"', text)
        self.assertIn('KV_MEM="${KV_BYTES}"', text)
        self.assertIn("QSA_EXACT_TOPK=1", text)
        self.assertIn("SPEC=none", text)
        self.assertIn("VLLM_PLE_MMAP=1", text)
        self.assertIn("QWEN38_MARLIN_CANONICAL_ORDER=1", text)
        self.assertIn("QWEN38_MARLIN_CANONICAL_SCOPE=decoder", text)
        self.assertIn('if "--speculative-config" in cmd:', text)
        self.assertIn('if "VLLM_PLE_CPU_OFFLOAD=1" in env:', text)
        self.assertIn('value("--gpu-memory-utilization") != "0.80"', text)
        self.assertIn('value("--max-num-batched-tokens") != "8192"', text)
        self.assertIn('"--no-enable-prefix-caching"', text)
        self.assertIn('"--no-enable-flashinfer-autotune"', text)
        self.assertIn('"--no-async-scheduling"', text)

    def test_runner_preserves_protection_policy(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        for expected in (
            "--min-available-gib 6",
            "--min-free-gib 2",
            "--free-gate-gib 10",
            "--min-swap-free-gib 8",
            "--swap-activity-gate-mib 256",
            "--consecutive 5",
            "--protect",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("--no-monitor", text)

    def test_runner_preserves_stopped_managed_predecessor(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("managed service is active; this discriminator requires", text)
        self.assertIn(
            "Managed predecessor remains in its original stopped post-protection state.",
            text,
        )
        self.assertNotIn("update-release.sh", text)
        self.assertNotIn("install.sh", text)
        self.assertNotIn('systemctl start "${UNIT}"', text)
        self.assertNotIn('systemctl stop "${UNIT}"', text)

    def test_runner_keeps_strict_rm_classification(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("NV_ERR_NO_MEMORY|_memdescAllocInternal", text)
        self.assertIn('HOST_STABILITY="FAIL"', text)
        self.assertIn("FUNCTIONAL_PASS_HOST_FAIL", text)
        self.assertIn("FUNCTIONAL_NOT_REACHED_HOST_FAIL", text)

    def test_runner_requires_exact_clean_checkout_and_idle_stopped_baseline(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("H38_MTP_DISCRIMINATOR_TARGET_SHA", text)
        self.assertIn("rev-parse HEAD", text)
        self.assertIn("status --porcelain=v1 --untracked-files=all", text)
        self.assertIn("assert_idle", text)
        self.assertIn(
            "restored managed predecessor container is unexpectedly running",
            text,
        )
        self.assertIn("stale rollback container exists", text)


if __name__ == "__main__":
    unittest.main()
