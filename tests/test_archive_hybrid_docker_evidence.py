"""Non-destructive source and pinned-inventory checks for 17-container archival."""
import ast
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / "scripts/model/archive-hybrid-docker-evidence.py"


class HybridArchive17Tests(unittest.TestCase):
    def test_python_parses_and_exact_seventeen_are_pinned(self):
        tree = ast.parse(SRC.read_text())
        assignments = [n for n in tree.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == "EXPECTED_IDS" for t in n.targets)]
        self.assertEqual(len(assignments), 1)
        self.assertEqual(len(ast.literal_eval(assignments[0].value)), 17)
        for cid in ast.literal_eval(assignments[0].value):
            self.assertEqual(len(cid), 64)
            self.assertTrue(all(ch in "0123456789abcdef" for ch in cid))

    def test_nondestructive_and_private_archive(self):
        text = SRC.read_text()
        for token in ('docker("rm"', 'docker("start"', 'docker("stop"', "shutil.rmtree(", "unlink("):
            self.assertNotIn(token, text)
        for marker in ("os.fchmod", "tempfile.TemporaryDirectory", "SHA256SUMS",
                       "HYBRID_DOCKER_DELETE=NOT_PERFORMED", "latest != entries"):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
