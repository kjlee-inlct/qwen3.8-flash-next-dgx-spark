from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "benchmark" / "analyze-orcarouter-r21-pagecache-reclaim.py"


class R21PagecacheReclaimAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("r21_analysis", SCRIPT)
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_weighted_high_order_metrics(self) -> None:
        values = [0, 0, 0, 0, 2, 1]
        self.assertEqual(self.module.order_mib(values, 4), 0.125)
        self.assertEqual(self.module.ge_mib(values, 5), 0.125)
        self.assertEqual(self.module.ge_mib(values, 4), 0.25)

    def test_metric_extracts_file_cache_and_migratetypes(self) -> None:
        snapshot = {
            "buddy": {(0, "Normal"): [0, 0, 0, 0, 2, 1]},
            "pagetype": {
                (0, "Normal", "Unmovable"): [0, 0, 0, 0, 1, 1],
                (0, "Normal", "Movable"): [0, 0, 0, 0, 1, 0],
            },
            "mem": {
                "MemAvailable": 8192,
                "MemFree": 4096,
                "Cached": 2048,
                "Active(file)": 512,
                "Inactive(file)": 1536,
                "SwapFree": 16384,
            },
        }
        values = self.module.metric(snapshot)
        self.assertEqual(values["memavailable"], 8.0)
        self.assertEqual(values["memfree"], 4.0)
        self.assertEqual(values["cached"], 2.0)
        self.assertEqual(values["inactive_file"], 1.5)
        self.assertEqual(values["unmovable_o4plus"], 0.1875)
        self.assertEqual(values["movable_o4plus"], 0.0625)

    def test_load_snapshot_requires_proc_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "proc-buddyinfo.txt").write_text(
                "Node 0, zone Normal 0 0 0 0 1 1\n", encoding="utf-8"
            )
            (path / "proc-pagetypeinfo.txt").write_text(
                "Node 0, zone Normal, type Unmovable 0 0 0 0 1 1\n",
                encoding="utf-8",
            )
            (path / "proc-meminfo.txt").write_text(
                "MemAvailable: 8192 kB\nMemFree: 4096 kB\nCached: 2048 kB\n"
                "Active(file): 512 kB\nInactive(file): 1536 kB\nSwapFree: 16384 kB\n",
                encoding="utf-8",
            )
            snap = self.module.load_snapshot(path)
            values = self.module.metric(snap)
            self.assertEqual(values["cached"], 2.0)

    def test_analyzer_is_read_only_and_uses_all_r21_stages(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("/proc/sys/vm/", text)
        self.assertNotIn("drop_caches", text)
        self.assertNotIn("compact_memory", text)
        self.assertIn("poststop-before-reclaim", text)
        self.assertIn("poststop-after-sync", text)
        self.assertIn("poststop-after-drop-caches", text)
        self.assertIn("poststop-after-compact", text)
        self.assertIn("ORCA_R21_PAGECACHE_RECLAIM_ANALYSIS", text)


if __name__ == "__main__":
    unittest.main()
