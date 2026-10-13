"""Synthetic command-routing checks: no Docker, GPU or real installation writes."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RootWizardRoutingTests(unittest.TestCase):
    def run_cmd(self, script: str, *args: str, home: Path, stdin: str = ""):
        return subprocess.run(
            [str(ROOT / script), *args],
            cwd=ROOT,
            env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
            input=stdin, text=True, capture_output=True, check=False,
        )

    def test_wizard_help_and_invalid_choice_never_mutate(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            help_result = self.run_cmd("wizard.sh", "--help", home=home)
            self.assertEqual(help_result.returncode, 0, help_result.stderr)
            self.assertIn("--manage", help_result.stdout)
            invalid = self.run_cmd("wizard.sh", home=home, stdin="9\n")
            self.assertEqual(invalid.returncode, 2)
            self.assertFalse((home / "state").exists())

    def test_installer_stays_available_for_new_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_cmd("install.sh", "--help", home=home)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--model", result.stdout)
            self.assertFalse((home / "state").exists())

    def test_manage_requires_complete_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_cmd("wizard.sh", "--manage", "--dry-run", home=home)
            self.assertEqual(result.returncode, 2)
            self.assertIn("WIZARD_MANAGE=BLOCKED", result.stderr)
            self.assertFalse((home / "state").exists())

    def test_closed_menu_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_cmd("wizard.sh", home=home)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Input stream closed", result.stderr)


if __name__ == "__main__":
    unittest.main()
