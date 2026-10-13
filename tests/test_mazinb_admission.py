"""Fail-closed smoke checks for read-only mazinb admission."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/wizard/mazinb-admission.sh"
EXAMPLE_ID = "a" * 64


class MazinbAdmissionTests(unittest.TestCase):
    def run_gate(self, home: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "xdg")}
        return subprocess.run(
            ["bash", str(SCRIPT), *args], cwd=ROOT, env=env, text=True,
            capture_output=True, timeout=20, check=False,
        )

    def test_usage_is_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            result = self.run_gate(home, ["--help"])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("READ-ONLY admission", result.stdout)
            self.assertFalse((home / "xdg").exists())

    def test_unknown_or_missing_id_denied(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            for flags in ([], ["--expected-old-id", "123"], ["--yes"]):
                result = self.run_gate(home, flags)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("PASS_READ_ONLY", result.stdout)
            self.assertFalse((home / "xdg").exists())

    def test_reviewed_a_requires_full_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            invalid = self.run_gate(home, [
                "--expected-old-id", EXAMPLE_ID, "--reviewed-trial-a-id", "short"
            ])
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn("reviewed historical A ID", invalid.stderr)
            self.assertFalse((home / "xdg").exists())

    def test_repeated_and_unknown_flags_denied(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            for flags in (
                ["--expected-old-id", EXAMPLE_ID, "--expected-old-id", EXAMPLE_ID],
                ["--reviewed-trial-a-id", EXAMPLE_ID, "--reviewed-trial-a-id", EXAMPLE_ID],
                ["--expected-old-id", EXAMPLE_ID, "--cleanup"],
            ):
                result = self.run_gate(home, flags)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("PASS_READ_ONLY", result.stdout)
            self.assertFalse((home / "xdg").exists())

    def test_stopped_historical_a_is_reviewed_not_removed(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("historical A must be reviewed through Wizard", source)
        self.assertIn("qwen38-mazinb-kv-b", source)
        self.assertIn("PRESERVED_REVIEWED", source)
        self.assertIn("a_running", source)
        self.assertNotIn('docker rm "', source)
        self.assertNotIn('rm -rf "', source)

    def test_missing_state_fails_before_docker(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            result = self.run_gate(home, ["--expected-old-id", EXAMPLE_ID])
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("PASS_READ_ONLY", result.stdout)
            self.assertFalse((home / "xdg").exists())

    def test_symlink_state_directory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / "real").mkdir()
            (home / "xdg").mkdir()
            (home / "xdg" / "qwen38-spark").symlink_to(home / "real")
            result = self.run_gate(home, ["--expected-old-id", EXAMPLE_ID])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("BLOCKED", result.stderr)

    def test_source_has_no_host_mutation_calls(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for disallowed in ("docker stop ", "docker rm ", "docker run ", "docker start ",
                           "systemctl restart ", "systemctl stop ", "rm -rf ", "sudo "):
            self.assertNotIn(disallowed, source)
        self.assertIn("MAZINB_ADMISSION=PASS_READ_ONLY", source)
        self.assertIn("MAZINB_BENCHMARK=NOT_MEASURED", source)


if __name__ == "__main__":
    unittest.main()
