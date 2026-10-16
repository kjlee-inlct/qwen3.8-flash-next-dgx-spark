"""Hybrid retirement wizard is modular, navigable, and read-only."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MENU = ROOT / "scripts/wizard/model-menu.sh"
SUBMENU = ROOT / "scripts/wizard/hybrid-retirement-menu.sh"
ROUTER = ROOT / "scripts/wizard/menus.sh"


class HybridRetirementWizardMenuTests(unittest.TestCase):
    def test_navigation_and_guards(self):
        model = MENU.read_text()
        guide = SUBMENU.read_text()
        router = ROUTER.read_text()
        self.assertNotIn("wizard_hybrid_retirement_guide() {", model)
        self.assertIn("wizard_menu_option 10", model)
        self.assertIn("10) wizard_hybrid_retirement_guide ;;", model)
        self.assertIn("hybrid-retirement-menu.sh", router)
        self.assertIn("wizard_hybrid_retirement_guide() {", guide)
        for phrase in ("hybrid-archive-git-summary.py",
                       "hybrid-docker-inventory.py",
                       "Old exact-17/H3-H6 scripts", "((missing+=1))"):
            self.assertIn(phrase, guide)
        for forbidden in ("--execute", "docker rm", "rmtree",
                          "remove-hybrid-models-exact-h3-h6.py"):
            self.assertNotIn(forbidden, guide)


if __name__ == "__main__":
    unittest.main()
