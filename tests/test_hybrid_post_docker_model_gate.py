"""Read-only post-Docker model retirement gate contract."""
import ast
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / "scripts/model/hybrid-post-docker-model-gate.py"

class HybridPostDockerGateTests(unittest.TestCase):
    def test_fail_closed_rules(self):
        body = SRC.read_text()
        ast.parse(body)
        for key in ("archive.summarize", "PINNED", "retired Hybrid containers still exist",
                    "retained Docker references Hybrid", "directory symlink",
                    "special file in Hybrid tree", "followlinks=False",
                    "13, 76, 91, 139", "model_delete_performed"):
            self.assertIn(key, body)
        for forbidden in ("rmtree(", "unlink(", '"rm"', '"prune"', "shutil.", "os.remove("):
            self.assertNotIn(forbidden, body)
if __name__ == "__main__":
    unittest.main()
