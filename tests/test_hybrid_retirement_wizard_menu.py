"""Completed Hybrid research is absent from active Wizard; archives stay intact."""
from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
MENU = ROOT / "scripts/wizard/model-menu.sh"
SUBMENU = ROOT / "scripts/wizard/hybrid-retirement-menu.sh"
ROUTER = ROOT / "scripts/wizard/menus.sh"


class RetiredHybridWizardTests(unittest.TestCase):
    def test_historical_guide_preserved_but_not_operator_routed(self):
        model = MENU.read_text(encoding="utf-8")
        router = ROUTER.read_text(encoding="utf-8")
        guide = SUBMENU.read_text(encoding="utf-8")
        self.assertNotIn("wizard_hybrid_", model)
        self.assertNotIn("Hybrid H6 Phase-0", model)
        self.assertNotIn("Hybrid H3-H6 dependency", model)
        self.assertNotIn("Hybrid H6 launch admission", model)
        self.assertNotIn("Hybrid retirement guide & post-cleanup checks", model)
        self.assertNotIn("hybrid-retirement-menu.sh", router)
        self.assertIn("wizard_menu_option 7 'Candidate Hub metadata", model)
        self.assertIn("7) wizard_candidate_metadata_menu ;;", model)
        self.assertIn("wizard_hybrid_retirement_guide() {", guide)
        for phrase in ("hybrid-archive-git-summary.py",
                       "hybrid-docker-inventory.py",
                       "Old exact-17/H3-H6 scripts"):
            self.assertIn(phrase, guide)
        for forbidden in ("docker rm", "rm -rf", "--execute"):
            self.assertNotIn(forbidden, guide)

    def test_retired_numbers_cannot_trigger_retired_operations(self):
        # The Wizard uses no network, GPU, deletion or model-specific actions.
        script = (
            "set -Eeuo pipefail; "
            f'ROOT_DIR="{ROOT}"; UI_LANG=en; '
            'source "$ROOT_DIR/scripts/lib/wizard-ui.sh"; '
            'source "$ROOT_DIR/scripts/wizard/model-menu.sh"; '
            "wizard_model_menu"
        )
        result = subprocess.run(
            ["bash", "-c", script], cwd=ROOT, input="8\n9\n10\n0\n",
            text=True, capture_output=True, check=False, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("Invalid selection"), 3)
        self.assertNotIn("Phase-0 read-only inventory", result.stdout)
        self.assertNotIn("protected launch admission", result.stdout)


if __name__ == "__main__":
    unittest.main()
