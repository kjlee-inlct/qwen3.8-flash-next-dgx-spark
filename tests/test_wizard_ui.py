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

    def test_eof_never_approves_default_yes_confirmation(self) -> None:
        result = self.run_bash(
            f'source "{WIZARD}"; '
            'if wizard_yes_no "Apply changes?" yes; then echo UNEXPECTED_APPROVAL; '
            'else echo UNEXPECTED_FALLBACK; fi; echo UNEXPECTED_CONTINUATION',
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Input stream closed (EOF)", result.stderr)
        self.assertNotIn("UNEXPECTED_", result.stdout)

    def test_eof_cannot_disable_monitor_via_and_or_fallback(self) -> None:
        result = self.run_bash(
            f'source "{WIZARD}"; '
            'wizard_yes_no "Protect memory?" yes && echo PROTECTION_ON '
            '|| echo PROTECTION_OFF; echo UNEXPECTED_CONTINUATION',
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("PROTECTION_ON", result.stdout)
        self.assertNotIn("PROTECTION_OFF", result.stdout)
        self.assertNotIn("UNEXPECTED_CONTINUATION", result.stdout)

    def test_eof_does_not_use_input_default_or_accept_secret(self) -> None:
        for entrypoint in (
            'wizard_input value "Target model" "orcarouter"; echo UNEXPECTED_DEFAULT',
            'wizard_secret token "Token"; echo UNEXPECTED_SECRET',
        ):
            with self.subTest(entrypoint=entrypoint):
                result = self.run_bash(f'source "{WIZARD}"; {entrypoint}')
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("wizard cancelled", result.stderr)
                self.assertNotIn("UNEXPECTED_", result.stdout)

    def test_truncated_unterminated_answer_is_not_consent(self) -> None:
        result = self.run_bash(
            f'source "{WIZARD}"; '
            'if wizard_yes_no "Delete?" yes; then echo UNEXPECTED_DELETE; fi',
            "yes",
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("UNEXPECTED_DELETE", result.stdout)

    def test_newline_terminated_explicit_yes_still_works(self) -> None:
        result = self.run_bash(
            f'source "{WIZARD}"; '
            'if wizard_yes_no "Continue?" no; then echo APPROVED; '
            'else echo DENIED; fi',
            "yes\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("APPROVED", result.stdout)
        self.assertNotIn("DENIED", result.stdout)



if __name__ == "__main__":
    unittest.main()
