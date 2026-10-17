"""Pure inventory tests; no Docker daemon required."""
import importlib.util
import json
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/model/hybrid-docker-inventory.py"
spec = importlib.util.spec_from_file_location("hybrid_docker_inventory", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class HybridDockerInventoryTests(unittest.TestCase):
    def test_legacy_and_canonical_aliases(self):
        self.assertIn(m.STAGES[0], m.references("/home/inlc/models/" + m.STAGES[0]))
        self.assertIn(m.STAGES[0], m.references(str(m.ROOT / "models" / m.STAGES[0])))
        self.assertEqual(m.references("/other/models/" + m.STAGES[0]), [])

    def test_reports_historical_exited_object(self):
        ids = "a" * 64 + "\n" + "b" * 64
        objects = [
            {"Id": "a" * 64, "Name": "/qwen38-h6-kv16-rmsys-r9",
             "State": {"Status": "exited"},
             "Mounts": [{"Source": "/home/inlc/models/" + m.STAGES[0]}]},
            {"Id": "b" * 64, "Name": "/qwen38-flash-next",
             "State": {"Status": "exited"}, "Mounts": []},
        ]
        result = m.inventory(ids, json.dumps(objects))
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["review_required"])

    def test_incomplete_inspection_blocks(self):
        with self.assertRaises(ValueError):
            m.inventory("a" * 64, "[]")

    def test_no_mutation(self):
        src = SOURCE.read_text()
        for forbidden in ('docker("rm"', 'docker("stop"', 'docker("start"', "unlink(", "rmtree("):
            self.assertNotIn(forbidden, src)

if __name__ == "__main__":
    unittest.main()
