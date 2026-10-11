"""Read-only monitor-trigger capture and strict synthetic log filtering."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/lifecycle/inspect-readonly-monitor-trigger.sh"


class MonitorTriggerReadonlyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "fixture-repo"
        dst = self.root / "scripts/lifecycle/inspect-readonly-monitor-trigger.sh"
        dst.parent.mkdir(parents=True)
        shutil.copyfile(SCRIPT, dst)
        self.script = dst
        self.home = Path(self.tmp.name) / "safe-home"
        self.state = self.home / "state" / "qwen38-spark"
        self.state.mkdir(parents=True)
        self.log = self.state / "monitor.log"
        self.git("init", "-q")
        self.git("add", "scripts/lifecycle/inspect-readonly-monitor-trigger.sh")
        self.git("-c", "user.name=Fixture",
                 "-c", "user.email=fixture@example.test",
                 "commit", "-qm", "synthetic")
        self.sha = self.git("rev-parse", "HEAD").stdout.strip()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True, text=True, check=True, timeout=10)

    def run_script(self, *, pin: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["XDG_STATE_HOME"] = str(self.home / "state")
        if pin:
            env["QWEN38_MONITOR_TRIGGER_TARGET_SHA"] = self.sha
        else:
            env.pop("QWEN38_MONITOR_TRIGGER_TARGET_SHA", None)
        return subprocess.run(
            ["bash", str(self.script)], env=env,
            capture_output=True, text=True, timeout=10)

    def test_script_bash_syntax(self) -> None:
        r = subprocess.run(
            ["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_requires_exact_sha_before_read(self) -> None:
        self.log.write_text("2026-10-07 22:18:16 PROTECT stopping x gracefully\n")
        result = self.run_script(pin=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("exact_checkout_sha_required", result.stderr)
        self.assertNotIn("bounded_monitor_trigger_samples", result.stdout)

    def test_bounded_structured_lines_only_and_no_writes(self) -> None:
        sample = (
            "2026-10-07 22:08:35 monitor started: container=qwen38 mode=protect\n"
            "2026-10-07 22:12:50 WARNING memory margin low protect=4/5: "
            "noncmafree=123MiB swapgrowth=333MiB\n"
            "2026-10-07 22:18:16 PROTECT stopping qwen38 gracefully to "
            "preserve host stability\n"
            "2026-10-07 22:10:00 SECRET user-prompt=never-display\n"
            "2026-10-08 22:18:16 PROTECT stopping wrong-day\n"
        )
        self.log.write_text(sample, encoding="utf-8")
        original = self.log.read_bytes()
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.log.read_bytes(), original)
        self.assertIn("monitor_matching_lines=3", result.stdout)
        self.assertIn("swapgrowth=333MiB", result.stdout)
        self.assertIn("PROTECT stopping qwen38", result.stdout)
        self.assertNotIn("user-prompt=never-display", result.stdout)
        self.assertNotIn("wrong-day", result.stdout)
        self.assertIn("MONITOR_TRIGGER_READONLY=COLLECTED_READ_ONLY",
                      result.stdout)
        self.assertIn("PROTECTION_THRESHOLD_CAUSE=NOT_YET_CLASSIFIED",
                      result.stdout)

    def test_missing_log_does_not_succeed(self) -> None:
        result = self.run_script()
        self.assertEqual(result.returncode, 2)
        self.assertIn("monitor_log_absent_unsafe_or_unreadable", result.stderr)

    def test_symlink_log_fails_closed(self) -> None:
        target = self.home / "fake.txt"
        target.write_text("2026-10-07 22:18:16 PROTECT stopping x gracefully\n")
        self.log.symlink_to(target)
        result = self.run_script()
        self.assertEqual(result.returncode, 2)
        self.assertIn("monitor_log_absent_unsafe_or_unreadable", result.stderr)

    def test_no_matching_samples_inconclusive(self) -> None:
        self.log.write_text(
            "2026-10-08 00:00:00 WARNING memory margin low protect=1/5\n")
        result = self.run_script()
        self.assertEqual(result.returncode, 3)
        self.assertIn("monitor_matching_lines=0", result.stdout)
        self.assertIn("MONITOR_TRIGGER_READONLY=INCONCLUSIVE_OR_READ_FAILURE",
                      result.stdout)

    def test_oversized_log_fails_before_read(self) -> None:
        with self.log.open("wb") as out:
            out.truncate(64 * 1024 * 1024 + 1)
        result = self.run_script()
        self.assertEqual(result.returncode, 2)
        self.assertIn("monitor_log_too_large_for_bounded_read", result.stderr)

    def test_no_mutating_commands_or_e2e_claims(self) -> None:
        data = SCRIPT.read_text(encoding="utf-8")
        for mark in (
            "QWEN38_MONITOR_TRIGGER_TARGET_SHA", "checkout_sha_mismatch",
            "dirty_checkout", "MAX_BYTES=$((64 * 1024 * 1024))",
            "monitor_output_truncated=YES",
            "MONITOR_TRIGGER_READONLY=COLLECTED_READ_ONLY",
            "PROTECTION_THRESHOLD_CAUSE=NOT_YET_CLASSIFIED",
            "RUNTIME_RESTART_OR_MODEL_LAUNCH=BLOCKED",
        ):
            self.assertIn(mark, data)
        for unsafe in (
            "docker stop", "docker start", "docker run", "docker rm",
            "systemctl restart", "systemctl start", "sudo ", "chmod ",
            "rm -", "journalctl -f", "git reset", "git switch", "git pull",
            "git fetch", "kill ", "tee ", "torch", "vllm serve",
        ):
            self.assertNotIn(unsafe, data)
        self.assertNotIn("HOST_STABILITY=PASS", data)
        self.assertNotIn("MANAGED_LIFECYCLE_LIVE_E2E=PASS", data)


if __name__ == "__main__":
    unittest.main()
