"""Exact-target opt-in Docker retirement source contract."""
import ast
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / "scripts/model/remove-hybrid-docker-exact17.py"


class ExactSeventeenRetirementTests(unittest.TestCase):
    def test_guards(self):
        src = SRC.read_text()
        ast.parse(src)
        for marker in ('gate.inspect_and_validate()', '"--execute", "--confirm-exact-17"',
                       'gate.archive.summarize', '["docker", "rm", "--", cid]',
                       '"State"]["Status"] != "exited"', '"mode": "DRY_RUN"'):
            self.assertIn(marker, src)
        for forbidden in ('"prune"', '"-f"', '"-v"', '"--volumes"', '"image", "rm"',
                          "rmtree(", "unlink(", "os.remove("):
            self.assertNotIn(forbidden, src)

if __name__ == "__main__":
    unittest.main()
