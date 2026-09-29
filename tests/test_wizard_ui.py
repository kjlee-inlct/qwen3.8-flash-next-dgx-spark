from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
WIZARD = ROOT / "scripts" / "lib" / "wizard-ui.sh"


class WizardUiTests(unittest.TestCase):
    def run_bash(self, script: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", "-lc", script],
            cwd=ROOT,
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_input_returns_typed_value_to_caller(self) -> None:
        result = self.run_bash(
            f'source "{WIZARD}"; wizard_input value "Value" "default"; printf "<%s>\n" "$value"',
            "typed\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("<typed>", result.stdout)

    def test_input_uses_default_on_empty_line(self) -> None:
        result = self.run_bash(
            f'source "{WIZARD}"; wizard_input value "Value" "default"; printf "<%s>\n" "$value"',
            "\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("<default>", result.stdout)

    def test_yes_no_defaults_are_stable(self) -> None:
        yes = self.run_bash(
            f'source "{WIZARD}"; if wizard_yes_no "Continue" yes; then echo yes; else echo no; fi',
            "\n",
        )
        no = self.run_bash(
            f'source "{WIZARD}"; if wizard_yes_no "Continue" no; then echo yes; else echo no; fi',
            "\n",
        )
        self.assertEqual(yes.returncode, 0, yes.stderr)
        self.assertEqual(no.returncode, 0, no.stderr)
        self.assertIn("yes", yes.stdout)
        self.assertIn("no", no.stdout)

    def test_non_tty_output_has_no_ansi_color_codes(self) -> None:
        result = self.run_bash(
            f'source "{WIZARD}"; wizard_header "Header"; wizard_step 1 2 "Step"; wizard_success "OK"'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("\x1b[", result.stdout)
        self.assertIn("[1/2] Step", result.stdout)


if __name__ == "__main__":
    unittest.main()
