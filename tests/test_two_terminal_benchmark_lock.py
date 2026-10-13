"""The bench-vs-wizard lock tests run only commands inside a temporary HOME."""
from __future__ import annotations
import fcntl
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/benchmark/with-wizard-lock.sh"

class WizardBenchLockTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.state = self.home / "state" / "qwen38-spark"
        self.state.mkdir(parents=True)
        self.lock = self.state / "operation.lock"
        self.lock.write_bytes(b"")
        self.env = {**os.environ, "XDG_STATE_HOME": str(self.home / "state"), "HOME": str(self.home)}

    def run_wrapper(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT), "--", *args],
            env=self.env, cwd=ROOT, text=True, capture_output=True,
            timeout=12, check=False,
        )

    def test_holds_lock_while_command_succeeds(self) -> None:
        proc = self.run_wrapper("bash", "-c", "printf synthetic-benchmark")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "synthetic-benchmark")
        self.assertIn("BENCH_WIZARD_LOCK=ACQUIRED", proc.stderr)
        self.assertIn("BENCH_COMMAND_RC=0", proc.stderr)

    def test_preexisting_wizard_lock_refuses_running_command(self) -> None:
        with self.lock.open("rb") as fd:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            proc = self.run_wrapper("bash", "-c", "echo SHOULD_NOT_EXECUTE")
            self.assertEqual(proc.returncode, 3, proc.stderr)
            self.assertIn("BENCH_WIZARD_LOCK=BUSY", proc.stderr)
            self.assertNotIn("SHOULD_NOT_EXECUTE", proc.stdout)

    def test_returns_command_failure_status(self) -> None:
        proc = self.run_wrapper("bash", "-c", "exit 17")
        self.assertEqual(proc.returncode, 17, proc.stderr)
        self.assertIn("BENCH_COMMAND_RC=17", proc.stderr)

    def test_missing_lock_never_creates_new_file(self) -> None:
        self.lock.unlink()
        proc = self.run_wrapper("bash", "-c", "echo SHOULD_NOT_EXECUTE")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertFalse(self.lock.exists())

    def test_symlinked_lock_rejected(self) -> None:
        self.lock.unlink()
        alternative = self.home / "alternative.lock"
        alternative.write_bytes(b"")
        self.lock.symlink_to(alternative)
        proc = self.run_wrapper("bash", "-c", "echo SHOULD_NOT_EXECUTE")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertNotIn("SHOULD_NOT_EXECUTE", proc.stdout)

    def test_wrapper_contains_no_start_stop_delete_actions(self) -> None:
        body = SCRIPT.read_text(encoding="utf-8")
        for action in ("docker run", "docker start", "docker rm", "systemctl restart", "swapoff", "rm -rf"):
            self.assertNotIn(action, body)

if __name__ == "__main__":
    unittest.main()
