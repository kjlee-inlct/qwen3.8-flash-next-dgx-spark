from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "benchmark" / "compare-orcarouter-r18-r20-poststop-state.py"


class OrcaRouterR18R20PoststopCompareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("r18r20_compare", SCRIPT)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_buddy_weighting_and_meminfo(self) -> None:
        buddy = self.module.parse_counts(
            "Node 0, zone Normal 0 0 0 0 2 1 0\n",
            self.module.BUDDY_RE,
        )
        values = buddy[(0, "Normal")]
        self.assertEqual(self.module.order_mib(values, 4), 0.125)
        self.assertEqual(self.module.mib_for_orders(values, 5), 0.125)
        self.assertEqual(self.module.mib_for_orders(values, 4), 0.25)

        mem = self.module.parse_meminfo(
            "MemAvailable:    16384 kB\nMemFree: 8192 kB\nSwapFree: 32768 kB\nCached: 4096 kB\n"
        )
        self.assertEqual(mem["MemAvailable"], 16384)
        self.assertEqual(mem["SwapFree"], 32768)
        self.assertEqual(self.module.mem_mib(mem, "Cached"), 4.0)

    def test_pagetype_parser(self) -> None:
        parsed = self.module.parse_counts(
            "Node 0, zone Normal, type Unmovable 1 2 3 4 5 6\n",
            self.module.PAGETYPE_RE,
        )
        self.assertEqual(parsed[(0, "Normal", "Unmovable")][4], 5)

    def test_zoneinfo_parser(self) -> None:
        parsed = self.module.parse_zoneinfo(
            "Node 0, zone Normal\n  pages free     100\n        min      20\n        low      30\n        high     40\n"
        )
        self.assertEqual(parsed[(0, "Normal")]["free"], 100)
        self.assertEqual(parsed[(0, "Normal")]["low"], 30)

    def test_analyzer_is_read_only_and_emits_discriminators(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("/proc/sys/vm/", text)
        self.assertNotIn("compact_memory", text)
        self.assertIn("poststop-before-compact", text)
        self.assertIn("poststop-after-compact", text)
        self.assertIn("ORCA_R18_R20_POSTSTOP_COMPARISON", text)
        self.assertIn("compaction_pagetype=", text)
        self.assertIn("postcompact_pagetype=", text)
        self.assertIn("postcompact_mem=", text)
        self.assertIn('"KReclaimable"', text)
        self.assertIn('"SReclaimable"', text)

    def test_load_snapshot_requires_full_proc_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "proc-buddyinfo.txt").write_text(
                "Node 0, zone Normal 0 0 0 0 1 1\n", encoding="utf-8"
            )
            (path / "proc-pagetypeinfo.txt").write_text(
                "Node 0, zone Normal, type Unmovable 0 0 0 0 1 1\n",
                encoding="utf-8",
            )
            (path / "proc-zoneinfo.txt").write_text(
                "Node 0, zone Normal\n pages free 100\n low 20\n high 30\n",
                encoding="utf-8",
            )
            (path / "proc-meminfo.txt").write_text(
                "MemAvailable: 1000 kB\nMemFree: 500 kB\nSwapFree: 2000 kB\nCached: 250 kB\n",
                encoding="utf-8",
            )
            (path / "proc-vmstat.txt").write_text(
                "compact_stall 10\ncompact_fail 3\ncompact_success 7\n",
                encoding="utf-8",
            )
            snap = self.module.load_snapshot(path)
            self.assertEqual(snap["mem"]["MemAvailable"], 1000)
            self.assertEqual(snap["mem"]["Cached"], 250)
            self.assertEqual(snap["vm"]["compact_success"], 7)


if __name__ == "__main__":
    unittest.main()
