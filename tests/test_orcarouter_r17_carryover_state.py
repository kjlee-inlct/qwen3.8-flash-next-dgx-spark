"""Regression coverage for the R17 allocator carry-over comparison."""

from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/benchmark/compare-orcarouter-r17-carryover-state.py"


def load_module():
    spec = importlib.util.spec_from_file_location("r17_carryover", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ge4_metrics_are_weighted_by_order():
    mod = load_module()
    order4, blocks, mib = mod.ge4_metrics([0, 0, 0, 0, 2, 1])
    assert order4 == 2
    assert blocks == 3
    assert mib == 0.25


def test_pagetype_parser_reads_order_counts_and_pageblocks():
    mod = load_module()
    text = """
Free pages count per migrate type at order    0    1    2    3    4    5
Node    0, zone   Normal, type    Unmovable      1      2      3      4      5      6
Node    0, zone   Normal, type      Movable      7      8      9     10     11     12
Number of blocks type     Unmovable      Movable  Reclaimable   HighAtomic          CMA      Isolate
Node 0, zone   Normal        100        200         30          4          5          6
"""
    counts, blocks = mod.parse_pagetype(text)
    assert counts[(0, "Normal", "Unmovable")][4] == 5
    assert counts[(0, "Normal", "Movable")][5] == 12
    assert blocks[(0, "Normal")]["Unmovable"] == 100
    assert blocks[(0, "Normal")]["Movable"] == 200


def test_zone_parser_reads_free_and_watermarks():
    mod = load_module()
    text = """
Node 0, zone   Normal
  pages free     12345
        min      100
        low      200
        high     300
        managed  40000
        cma      0
"""
    zones = mod.parse_zoneinfo(text)
    assert zones[(0, "Normal")]["free"] == 12345
    assert zones[(0, "Normal")]["low"] == 200
    assert zones[(0, "Normal")]["high"] == 300


def test_script_is_read_only_and_reports_cross_leg_boundary():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "R17_CARRYOVER_BOUNDARY=A_FINAL_TO_B_BASELINE" in text
    assert "carryover_pagetype" in text
    assert "carryover_pageblock" in text
    assert "carryover_buddy" in text
    assert "/proc/sys/vm/" not in text
    assert "write_text(" not in text
