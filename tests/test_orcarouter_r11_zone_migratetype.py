from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).parents[1]
ANALYZER = ROOT / "scripts" / "benchmark" / "analyze-orcarouter-r11-zone-migratetype.py"

spec = importlib.util.spec_from_file_location("r11_zone_migratetype", ANALYZER)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class OrcaRouterR11ZoneMigratetypeTests(unittest.TestCase):
    def test_parse_failed_interval(self) -> None:
        text = """\
=== FAILED_NV_ALLOC_PAGES_1_NESTED_SYS_1 ===
task=VLLM::Worker pid=123
start=100.500000 delta_from_rm=+0.1s
end=101.250000 delta_from_rm=+0.8s
ret=0x51(81)

=== FAILED_NV_ALLOC_PAGES_1_NEXT_SAME_THREAD ===
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "analysis.txt"
            path.write_text(text, encoding="utf-8")
            interval = module.parse_failed_interval(path)
        self.assertEqual(interval.task, "VLLM::Worker")
        self.assertEqual(interval.pid, 123)
        self.assertEqual(interval.start, 100.5)
        self.assertEqual(interval.end, 101.25)

    def test_parse_zone_ranges_and_mapping(self) -> None:
        text = """\
Node 0, zone      DMA
  pages free 1
  start_pfn:           1
        spanned  4095
Node 0, zone   Normal
  pages free 1
  start_pfn:        4096
        spanned  100000
"""
        ranges = module.parse_zone_ranges(text)
        self.assertEqual(len(ranges), 2)
        self.assertEqual(module.zone_for_pfn(ranges, 100), "node0:DMA")
        self.assertEqual(module.zone_for_pfn(ranges, 5000), "node0:Normal")
        self.assertEqual(module.zone_for_pfn(ranges, 999999), "UNMAPPED")

    def test_parse_trace_fields_for_zone_and_migratetype_contract(self) -> None:
        fields = module.parse_fields(
            "page=0xffff pfn=5000 order=4 migratetype=0 gfp_flags=0x0"
        )
        self.assertEqual(fields["pfn"], 5000)
        self.assertEqual(fields["order"], 4)
        self.assertEqual(fields["migratetype"], 0)
        self.assertEqual(module.migrate_name(0), "0:Unmovable")
        self.assertEqual(module.migrate_name(1), "1:Movable")

    def test_analyzer_contract_mentions_exact_dimensions(self) -> None:
        text = ANALYZER.read_text(encoding="utf-8")
        for token in (
            "mm_page_alloc_extfrag",
            "alloc_migratetype",
            "fallback_migratetype",
            "change_ownership",
            "rollback_zone",
            "zone_mapping_coverage",
            "start_pfn",
            "spanned",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
