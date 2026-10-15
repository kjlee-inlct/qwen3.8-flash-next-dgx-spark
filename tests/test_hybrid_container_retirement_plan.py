"""Host-free tests for immutable Hybrid container retirement planning."""
import importlib.util
import json
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/model/hybrid-container-retirement-plan.py"
spec = importlib.util.spec_from_file_location("hybrid_retirement_plan", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture():
    ids = list(mod.EXPECTED.values()) + ["f" * 64]
    items = []
    for name, cid in mod.EXPECTED.items():
        items.append({"Id": cid, "Name": "/" + name,
                      "State": {"Status": "exited", "Running": False},
                      "HostConfig": {"AutoRemove": False, "RestartPolicy": {"Name": "no"}},
                      "Mounts": [{"Source": "/model/models/" + mod.STAGES[0]}]})
    items.append({"Id": "f" * 64, "Name": "/other", "Mounts": []})
    return "\n".join(ids), items


class HybridContainerRetirementPlanTests(unittest.TestCase):
    def test_full_id_regex_accepts_exact_hex_and_rejects_short(self):
        self.assertTrue(mod.FULL_ID.fullmatch(next(iter(mod.EXPECTED.values()))))
        self.assertFalse(mod.FULL_ID.fullmatch("e526189f1093"))
        self.assertFalse(mod.FULL_ID.fullmatch("g" * 64))

    def test_exact_six_only(self):
        ids, items = fixture()
        ok, lines = mod.plan(ids, json.dumps(items))
        self.assertTrue(ok)
        self.assertIn("TARGET_COUNT=6", lines)

    def test_missing_or_replaced_id_blocks(self):
        ids, items = fixture()
        self.assertFalse(mod.plan(ids.replace(next(iter(mod.EXPECTED.values())), "a" * 64),
                                  json.dumps(items))[0])

    def test_running_and_auto_remove_block(self):
        ids, items = fixture()
        items[0]["State"]["Running"] = True
        self.assertFalse(mod.plan(ids, json.dumps(items))[0])
        items[0]["State"]["Running"] = False
        items[0]["HostConfig"]["AutoRemove"] = True
        self.assertFalse(mod.plan(ids, json.dumps(items))[0])

    def test_other_container_hybrid_mount_blocks(self):
        ids, items = fixture()
        items[-1]["Mounts"] = [{"Source": "/model/models/" + mod.STAGES[1]}]
        self.assertFalse(mod.plan(ids, json.dumps(items))[0])

    def test_no_destructive_calls(self):
        source = SOURCE.read_text()
        for token in ('docker("rm"', 'docker("stop"', 'docker("start"',
                      'unlink(', 'rmtree('):
            self.assertNotIn(token, source)
        self.assertIn("HYBRID_CONTAINER_DELETE=NOT_AUTHORIZED", source)


if __name__ == "__main__":
    unittest.main()
