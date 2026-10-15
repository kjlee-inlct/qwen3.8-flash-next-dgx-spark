"""Source guards for exact read-only retirement gate."""
import ast
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / "scripts/model/hybrid-retirement-final-gate.py"

class HybridFinalGateTests(unittest.TestCase):
    def test_contract(self):
        text = SRC.read_text()
        ast.parse(text)
        for required in ("archive.summarize", "PINNED_MANIFEST",
                         'entry["status"] != "exited"', '"AutoRemove"',
                         '"RestartPolicy"', '"Type") != "bind"', "path.is_symlink()",
                         "read_only_preflight"):
            self.assertIn(required, text)
        for forbidden in ("docker rm", '"rm",', "rmtree(", "unlink(", "shutil.", "os.remove("):
            self.assertNotIn(forbidden, text)
if __name__ == "__main__":
    unittest.main()
