"""Storage menu must expose state retention without mutation."""
from pathlib import Path
import unittest

MENU = Path(__file__).resolve().parents[1] / "scripts/wizard/storage-menu.sh"


class StorageStateRetentionMenuTests(unittest.TestCase):
    def test_single_read_only_menu_entry(self):
        content = MENU.read_text()
        self.assertIn("wizard_menu_option 5 'State retention audit", content)
        self.assertIn("5) python3 -B", content)
        self.assertIn('scripts/storage/state-retention-audit.py', content)
        self.assertEqual(content.count("state-retention-audit.py"), 1)
        self.assertNotIn("rm -rf", content)
        self.assertNotIn("--delete", content)


if __name__ == "__main__":
    unittest.main()
