"""Source safety contract for opt-in H3-H6 model-only retirement."""
import ast
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/model/remove-hybrid-models-exact-h3-h6.py"


class RemoveHybridModelsTests(unittest.TestCase):
    def test_exact_scope_gate_and_no_docker(self):
        source = SCRIPT.read_text()
        ast.parse(source)
        for item in ('gate.inspect()', '"PASS_READ_ONLY"', '"--confirm-exact-h3-h6"',
                     'shutil.rmtree.avoids_symlink_attacks', 'reversed(paths)',
                     '"mode": "DRY_RUN"', 'protected_orcarouter_exists'):
            self.assertIn(item, source)
        for item in ('"docker", "rm"', '"prune"', '"--volumes"', 'os.system(', 'shell=True'):
            self.assertNotIn(item, source)


if __name__ == "__main__":
    unittest.main()
