"""Regression coverage for predecessor-runtime age correlation."""

from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/benchmark/compare-orcarouter-predecessor-runtime-age.py"


def load_module():
    spec = importlib.util.spec_from_file_location("predecessor_age", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_iso_handles_docker_z_and_offset():
    mod = load_module()
    a = mod.parse_iso("2026-10-03T12:00:00.123456789Z")
    b = mod.parse_iso("2026-10-03T21:00:00+09:00")
    assert abs((a - b).total_seconds()) < 1


def test_rm_oom_count_prefers_r11_summary(tmp_path):
    mod = load_module()
    (tmp_path / "r11-summary.txt").write_text("run_valid=1\nrm_oom_count=4\n", encoding="utf-8")
    assert mod.rm_oom_count(tmp_path) == 4


def test_rm_oom_count_falls_back_to_kernel_errors(tmp_path):
    mod = load_module()
    r10b = tmp_path / "r10b"
    r10b.mkdir()
    (r10b / "kernel-errors.txt").write_text(
        "NV_ERR_NO_MEMORY\n_memdescAllocInternal NV_ERR_NO_MEMORY\nother\n",
        encoding="utf-8",
    )
    assert mod.rm_oom_count(tmp_path) == 2


def test_script_is_read_only_and_reports_age():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "predecessor_age_s=" in text
    assert "predecessor_age_min=" in text
    assert "rm_oom_count=" in text
    assert "/proc/sys/vm/" not in text
    assert "write_text(" not in text
