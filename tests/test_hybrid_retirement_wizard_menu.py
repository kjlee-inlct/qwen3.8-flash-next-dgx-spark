"""Hybrid retirement wizard is navigable, read-only, and historical IDs are not reused."""
from pathlib import Path
import unittest

MENU = Path(__file__).resolve().parents[1] / "scripts/wizard/model-menu.sh"


class HybridRetirementWizardMenuTests(unittest.TestCase):
    def test_navigation_and_guards(self):
        text = MENU.read_text()
        for phrase in ("wizard_hybrid_retirement_guide()",
                       "wizard_menu_option 10", "10) wizard_hybrid_retirement_guide ;;",
                       "hybrid-archive-git-summary.py", "hybrid-docker-inventory.py",
                       "Old exact-17/H3-H6 scripts", "((missing+=1))"):
            self.assertIn(phrase, text)
        guide = text.split("wizard_hybrid_retirement_guide() {", 1)[1].split("\nwizard_model_menu()", 1)[0]
        for forbidden in ('--execute', 'docker rm', 'rmtree', 'remove-hybrid-models-exact-h3-h6.py'):
            self.assertNotIn(forbidden, guide)


if __name__ == "__main__":
    unittest.main()
