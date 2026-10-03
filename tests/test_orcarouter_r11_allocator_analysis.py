from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).parents[1]
ANALYZER = ROOT / "scripts" / "benchmark" / "analyze-orcarouter-r11-allocator-state.py"

spec = importlib.util.spec_from_file_location("r11_allocator_analysis", ANALYZER)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class OrcaRouterR11AllocatorAnalysisTests(unittest.TestCase):
    def test_parse_buddy_and_metrics(self) -> None:
        parsed = module.parse_buddy("Node 0, zone Normal  1 2 3 4 5 6 7\n")
        values = parsed[(0, "Normal")]
        order4, ge4_mib, higher = module.buddy_metrics(values)
        self.assertEqual(order4, 5)
        self.assertEqual(higher, 13)
        self.assertGreater(ge4_mib, 0)

    def test_parse_pagetype_and_pageblocks(self) -> None:
        text = """\
Free pages count per migrate type at order 0 1 2 3 4 5
Node    0, zone   Normal, type    Unmovable      1      2      3      4      5      6
Node    0, zone   Normal, type      Movable      7      8      9     10     11     12
Number of blocks type     Unmovable      Movable  Reclaimable   HighAtomic      Isolate
Node 0, zone   Normal          10           20            3            1            0
"""
        counts, blocks = module.parse_pagetype(text)
        self.assertEqual(counts[(0, "Normal", "Unmovable")][4], 5)
        self.assertEqual(counts[(0, "Normal", "Movable")][4], 11)
        self.assertEqual(blocks[(0, "Normal")]["Unmovable"], 10)
        self.assertEqual(blocks[(0, "Normal")]["Movable"], 20)

    def test_parse_zoneinfo_watermarks(self) -> None:
        text = """\
Node 0, zone   Normal
  pages free     1200
        boost    0
        min      100
        low      200
        high     300
        managed  4000
        cma      0
"""
        zones = module.parse_zoneinfo(text)
        self.assertEqual(zones[(0, "Normal")]["free"], 1200)
        self.assertEqual(zones[(0, "Normal")]["low"], 200)
        self.assertEqual(zones[(0, "Normal")]["managed"], 4000)

    def test_parse_samples_and_nearest(self) -> None:
        text = """\
===== sample seq=1 wall=2026-10-03T00:00:00+00:00 monotonic_ns=1000000000 =====
--- /proc/buddyinfo ---
Node 0, zone Normal 1 2 3 4 5

===== sample seq=2 wall=2026-10-03T00:00:01+00:00 monotonic_ns=2000000000 =====
--- /proc/buddyinfo ---
Node 0, zone Normal 1 2 3 4 6

"""
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "fast-state.txt"
            path.write_text(text, encoding="utf-8")
            samples = module.parse_samples(path)
        self.assertEqual(len(samples), 2)
        before, after = module.nearest(samples, 1500000000)
        self.assertIsNotNone(before)
        self.assertIsNotNone(after)
        assert before is not None and after is not None
        self.assertEqual(before.seq, 1)
        self.assertEqual(after.seq, 2)

    def test_analyzer_contract_mentions_allocator_dimensions(self) -> None:
        text = ANALYZER.read_text(encoding="utf-8")
        for token in (
            "/proc/buddyinfo",
            "/proc/pagetypeinfo",
            "/proc/zoneinfo",
            "/proc/vmstat",
            "/proc/pressure/memory",
            "order4_blocks",
            "event_snapshot_delay_ms",
            'emit_pagetype_text("slow_before"',
            'emit_zone_text("slow_before_zone"',
            "free_minus_low_pages",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
