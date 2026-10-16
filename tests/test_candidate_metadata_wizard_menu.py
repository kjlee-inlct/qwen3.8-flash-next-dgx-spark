"""Candidate metadata Wizard routing and real input handling; no network/GPU."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODEL_MENU = ROOT / "scripts/wizard/model-menu.sh"
ROUTER = ROOT / "scripts/wizard/menus.sh"
CANDIDATE_MENU = ROOT / "scripts/wizard/candidate-metadata-menu.sh"


class CandidateMetadataWizardTests(unittest.TestCase):
    def run_menu(self, answers: str, *, fail: bool = False) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            bindir = home / "bin"
            bindir.mkdir()
            mock_python = bindir / "python3"
            mock_python.write_text(
                "#!/bin/sh\n"
                'printf "%s\\n" "$*" >> "$WIZARD_TEST_CALL_LOG"\n'
                'printf "SYNTHETIC_METADATA=PASS\\n"\n'
                'if [ "$WIZARD_TEST_PROBE_FAIL" = 1 ]; then exit 2; fi\n',
                encoding="utf-8",
            )
            mock_python.chmod(0o755)
            calls = home / "probe-calls.txt"
            command = (
                'set -Eeuo pipefail; '
                f'ROOT_DIR="{ROOT}"; UI_LANG=en; '
                'source "$ROOT_DIR/scripts/lib/wizard-ui.sh"; '
                'wizard_init; '
                'source "$ROOT_DIR/scripts/wizard/candidate-metadata-menu.sh"; '
                'wizard_candidate_metadata_menu'
            )
            env = {**os.environ, "HOME": tmp, "XDG_STATE_HOME": str(home / "state"),
                   "PATH": str(bindir) + os.pathsep + os.environ.get("PATH", ""),
                   "WIZARD_TEST_CALL_LOG": str(calls),
                   "WIZARD_TEST_PROBE_FAIL": "1" if fail else "0"}
            result = subprocess.run(
                ["bash", "-c", command], input=answers, text=True, capture_output=True,
                env=env, cwd=ROOT, timeout=15, check=False,
            )
            return result, calls.read_text(encoding="utf-8") if calls.exists() else ""

    def test_source_navigation_is_separate_from_model_install(self):
        model = MODEL_MENU.read_text(encoding="utf-8")
        route = ROUTER.read_text(encoding="utf-8")
        menu = CANDIDATE_MENU.read_text(encoding="utf-8")
        self.assertIn("wizard_menu_option 7 'Candidate Hub metadata", model)
        self.assertIn("7) wizard_candidate_metadata_menu ;;", model)
        self.assertIn("candidate-metadata-menu.sh", route)
        self.assertIn("wizard_candidate_metadata_menu() {", menu)
        self.assertNotIn("wizard_candidate_metadata_menu() {", model)
        for forbidden in ("docker run", "docker rm", "rm -rf", "--install", "--yes", "curl -O", "hf download"):
            self.assertNotIn(forbidden, menu)

    def test_summary_only_invokes_pinned_metadata_probe(self):
        result, calls = self.run_menu("1\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SYNTHETIC_METADATA=PASS", result.stdout)
        self.assertIn("GPU", result.stdout)
        self.assertIn("-B", calls)
        self.assertIn("/scripts/model/inspect_catplusplus_metadata.py", calls)
        self.assertNotIn("--json", calls)

    def test_full_inventory_is_explicit(self):
        result, calls = self.run_menu("2\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--json", calls)

    def test_invalid_then_back_does_not_fetch(self):
        result, calls = self.run_menu("99\n0\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Invalid selection", result.stdout)
        self.assertEqual(calls, "")

    def test_failure_warns_without_claiming_compatibility(self):
        result, calls = self.run_menu("1\n0\n", fail=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("failed or incomplete", result.stdout)
        self.assertNotIn("Metadata inventory complete", result.stdout)
        self.assertEqual(len(calls.strip().splitlines()), 1)

    def test_eof_does_not_reprompt_forever_or_authorize(self):
        result, calls = self.run_menu("")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("EOF", result.stderr)
        self.assertEqual(calls, "")


if __name__ == "__main__":
    unittest.main()
