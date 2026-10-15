from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / "scripts/model/hybrid-container-evidence.py"

class HybridEvidenceTests(unittest.TestCase):
    def test_preflight_scoped_and_read_only(self):
        source = SRC.read_text(encoding="utf-8")
        self.assertIn('if state != "exited"', source)
        self.assertIn('PASS_READ_ONLY_NOT_ARCHIVED_NOT_DELETE_AUTHORIZATION', source)
        for forbidden in ('docker("rm"', 'docker("stop"', 'docker("start"', 'shutil.rmtree', 'subprocess.Popen'):
            self.assertNotIn(forbidden, source)

if __name__ == "__main__":
    unittest.main()
