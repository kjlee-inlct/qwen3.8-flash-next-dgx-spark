"""Fail-closed bounded journal-only follow-up for an exited managed runtime."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/lifecycle/inspect-readonly-runtime-stop-journal.sh"


class ManagedRuntimeStopJournalReadOnlyTests(unittest.TestCase):
    def test_bash_syntax(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT)], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_sha_rejects_before_journal_read(self) -> None:
        env = os.environ.copy()
        env.pop("QWEN38_STOP_JOURNAL_TARGET_SHA", None)
        result = subprocess.run(
            ["bash", str(SCRIPT)], env=env,
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("exact_checkout_sha_required", result.stderr)
        self.assertNotIn("bounded_service_journal", result.stdout)

    def test_only_unit_bounded_no_mutation_journal(self) -> None:
        data = SCRIPT.read_text(encoding="utf-8")
        for mark in (
            "QWEN38_STOP_JOURNAL_TARGET_SHA",
            "checkout_sha_mismatch",
            "dirty_checkout",
            "expected_host_timezone_asia_seoul",
            "qwen38-flash-next.service",
            '--since "2026-10-07 21:55:00"',
            '--until "2026-10-07 22:25:00"',
            "--lines 160",
            "--unit",
            "journalctl --no-pager --quiet",
            "RUNTIME_STOP_JOURNAL=COLLECTED_READ_ONLY",
            "RUNTIME_STOP_JOURNAL=INCONCLUSIVE_OR_READ_FAILURE",
            "RUNTIME_STOP_CAUSE=NOT_YET_CLASSIFIED",
            "RUNTIME_RESTART_OR_MODEL_LAUNCH=BLOCKED",
            "MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED",
        ):
            self.assertIn(mark, data)
        for forbidden in (
            "journalctl -f", "journalctl --follow",
            "journalctl --vacuum", "systemctl restart", "systemctl start",
            "docker run", "docker start", "docker restart", "docker rm",
            "--purge-all", "--purge-model", "sudo ",
            "git fetch", "git pull", "git reset", "git switch",
            "kill ", "rm -", "chmod ", "tee ",
            "torch", "vllm serve",
        ):
            self.assertNotIn(forbidden, data)

    def test_journal_never_claims_stop_reason_or_host_stability(self) -> None:
        data = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("RUNTIME_STOP_CAUSE=PROVEN", data)
        self.assertNotIn("HOST_STABILITY=PASS", data)
        self.assertNotIn("MANAGED_LIFECYCLE_LIVE_E2E=PASS", data)


if __name__ == "__main__":
    unittest.main()
