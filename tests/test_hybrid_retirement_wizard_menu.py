"""Hybrid retirement wizard is navigable, read-only, and historical IDs are not reused."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MENU = ROOT / "scripts/wizard/model-menu.sh"
SUBMENU = ROOT / "scripts/wizard/hybrid-retirement-menu.sh"
ROUTER = ROOT / "scripts/wizard/menus.sh"


class HybridRetirementWizardMenuTests(unittest.TestCase):
    def test_navigation_and_guards(self):
        text = MENU.read_text()
        guide = SUBMENU.read_text()
        router = ROUTER.read_text()
        self.assertNotIn("wizard_hybrid_retirement_guide() {", text)
        self.assertIn("hybrid-retirement-menu.sh", router)
        for phrase in ("wizard_hybrid_retirement_guide()"
                       "wizard_menu_option 10", "10) wizard_hybrid_retirement_guide ;;",
                       "hybrid-archive-git-summary.py", "hybrid-docker-inventory.py",
                       "Old exact-17/H3-H6 scripts", "((missing+=1))"):
            self.assertIn(phrase, guide if phrase not in ("wizard_menu_option 10", "10) wizard_hybrid_retirement_guide ;;") else text)
        for forbidden in ('--execute', 'docker rm', 'rmtree', 'remove-hybrid-models-exact-h3-h6.py'):
            self.assertNotIn(forbidden, guide)


if __name__ == "__main__":
    unittest.main()
