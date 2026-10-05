from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "benchmark" / "compare-orcarouter-watermark-runs.py"


def load_module():
    spec = importlib.util.spec_from_file_location("watermark_compare", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WatermarkRunCompareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_parse_fast_sample_and_metrics(self):
        text = """===== sample seq=1 wall=2026-10-03T00:00:00+00:00 monotonic_ns=100 =====
--- /proc/buddyinfo ---
Node 0, zone      DMA      0 0 0 0 1 0
Node 0, zone   Normal      1 2 3 4 5 2
--- /proc/meminfo ---
MemAvailable:       2048000 kB
MemFree:            1024000 kB
SwapFree:           4096000 kB
--- /proc/vmstat ---
allocstall_normal 10
compact_stall 20
--- /proc/pressure/memory ---
some avg10=0.00 avg60=0.00 avg300=0.00 total=0
===== sample seq=2 wall=2026-10-03T00:00:01+00:00 monotonic_ns=200 =====
--- /proc/buddyinfo ---
Node 0, zone   Normal      1 2 3 4 1 1
--- /proc/meminfo ---
MemAvailable:       1024000 kB
MemFree:             512000 kB
SwapFree:           3072000 kB
--- /proc/vmstat ---
allocstall_normal 13
compact_stall 25
--- /proc/pressure/memory ---
some avg10=0.00 avg60=0.00 avg300=0.00 total=0
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "fast-state.txt"
            path.write_text(text, encoding="utf-8")
            samples = self.mod.parse_samples(path)
        self.assertEqual(len(samples), 2)
        first = self.mod.normal_buddy_ge4_mib(samples[0].sections["/proc/buddyinfo"])
        second = self.mod.normal_buddy_ge4_mib(samples[1].sections["/proc/buddyinfo"])
        self.assertAlmostEqual(first, (5 * 16 + 2 * 32) * 4096 / 1024 / 1024)
        self.assertAlmostEqual(second, (1 * 16 + 1 * 32) * 4096 / 1024 / 1024)
        vm0 = self.mod.parse_key_values(samples[0].sections["/proc/vmstat"])
        vm1 = self.mod.parse_key_values(samples[1].sections["/proc/vmstat"])
        self.assertEqual(vm1["allocstall_normal"] - vm0["allocstall_normal"], 3)

    def test_parse_normal_zone(self):
        text = """Node 0, zone      DMA
  pages free     100
        min      10
        low      20
        high     30
Node 0, zone   Normal
  pages free     1000
        boost    0
        min      100
        low      200
        high     300
Node 1, zone   Normal
  pages free     9999
        min      1
        low      2
        high     3
"""
        zone = self.mod.parse_normal_zone(text)
        self.assertEqual(zone, {"free": 1000, "min": 100, "low": 200, "high": 300})

    def test_parse_run_contract(self):
        label, path = self.mod.parse_run("R14=/tmp/example/r11")
        self.assertEqual(label, "R14")
        self.assertEqual(path, pathlib.Path("/tmp/example/r11"))
        with self.assertRaises(Exception):
            self.mod.parse_run("missing-separator")


if __name__ == "__main__":
    unittest.main()
