"""Regression coverage for restart-conditioning chain analysis."""

from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/benchmark/compare-orcarouter-restart-conditioning-chain.py"


def load_module():
    spec = importlib.util.spec_from_file_location("conditioning_chain", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_weighted_high_order_capacity():
    mod = load_module()
    values = [0, 0, 0, 0, 2, 1]
    assert mod.weighted_ge4_mib(values) == 0.25


def test_parse_leg_requires_label_and_path():
    mod = load_module()
    label, path = mod.parse_leg("R17A=/tmp/evidence")
    assert label == "R17A"
    assert path == pathlib.Path("/tmp/evidence")


def test_pagetype_parser_reads_normal_migrate_types():
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


def test_analyzer_is_read_only_and_exposes_boundaries():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "ORCA_RESTART_CONDITIONING_BOUNDARIES=BEGIN" in text
    assert "unmovable_delta_mib" in text
    assert "movable_delta_mib" in text
    assert "unmovable_pageblock_delta" in text
    assert "/proc/sys/vm/" not in text
    assert "write_text(" not in text
