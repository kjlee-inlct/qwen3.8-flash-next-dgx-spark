from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
GATE = ROOT / "scripts" / "run-h38-managed-followup-gates.sh"


class H38ManagedFollowupGateTests(unittest.TestCase):
    def test_followup_gate_shell_syntax(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(GATE)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_followup_requires_same_passing_migration_evidence(self) -> None:
        text = GATE.read_text(encoding="utf-8")
        self.assertIn("H38_MANAGED_TARGET_SHA", text)
        self.assertIn("H38_MANAGED_MIGRATION_EVIDENCE", text)
        self.assertIn("checkout SHA mismatch", text)
        self.assertIn("working tree is dirty", text)
        self.assertIn("migration evidence target mismatch", text)
        self.assertIn("functional=PASS", text)
        self.assertIn("host_stability=PASS", text)
        self.assertIn("script_rc=0", text)
        self.assertIn("baseline-decode-median.txt", text)

    def test_followup_reuses_canonical_determinism_and_decode_gates(self) -> None:
        text = GATE.read_text(encoding="utf-8")
        self.assertIn("run-h38-production-gate.sh", text)
        self.assertIn('H38_GATE_MODEL="${MODEL}"', text)
        self.assertIn("orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4", text)
        self.assertIn("--decode-tokens 384", text)
        self.assertIn("--decode-repeats 5", text)
        self.assertIn("ratio >= 0.90", text)
        self.assertIn("performance_ratio", text)

    def test_followup_uses_supported_locked_managed_restart(self) -> None:
        text = GATE.read_text(encoding="utf-8")
        self.assertIn("operation-lock.sh", text)
        self.assertIn("acquire_operation_lock", text)
        self.assertIn("sudo_with_operation_lock", text)
        self.assertIn('bash "${MANAGE_SERVICE}" create --runtime-root "${CURRENT_LINK}" --start --yes', text)
        self.assertIn("managed restart did not replace the container", text)
        self.assertIn("runtime commit attestation", text)
        self.assertIn('bash "${DOCTOR}" --strict', text)
        self.assertIn("runtime adoption marker is still pending", text)

    def test_followup_keeps_host_stability_independent_and_fail_closed(self) -> None:
        text = GATE.read_text(encoding="utf-8")
        self.assertIn("DETERMINISM=", text)
        self.assertIn("PERFORMANCE=", text)
        self.assertIn("RESTART_ATTESTATION=", text)
        self.assertIn("HOST_STABILITY=", text)
        self.assertIn("NV_ERR_NO_MEMORY|_memdescAllocInternal", text)
        self.assertIn("kernel_window_rc", text)
        self.assertIn("rm_oom_count", text)
        self.assertIn("protected_stop", text)
        self.assertIn("strict NVIDIA RM no-memory evidence observed", text)
        self.assertIn("memory protection intervened", text)
        self.assertIn("upload-summary.txt", text)

    def test_followup_revalidates_exact_h38_runtime_identity(self) -> None:
        text = GATE.read_text(encoding="utf-8")
        self.assertIn("vllm-orcarouter-v029-h38-decoder-scope:v1", text)
        self.assertIn("qwen38.h38scope", text)
        self.assertIn("QWEN38_MARLIN_CANONICAL_ORDER=1", text)
        self.assertIn("QWEN38_MARLIN_CANONICAL_SCOPE=decoder", text)
        self.assertIn("VLLM_PLE_MMAP=1", text)
        self.assertIn("VLLM_QSA_EXACT_TOPK=1", text)
        self.assertIn("--kv-cache-memory-bytes", text)
        self.assertIn("17179869184", text)
        self.assertIn("OOMKilled", text)


if __name__ == "__main__":
    unittest.main()
