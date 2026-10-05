from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
ANALYZER = ROOT / "scripts" / "benchmark" / "compare-orcarouter-r21-r22-rm-meminfo-all.py"


def text() -> str:
    return ANALYZER.read_text(encoding="utf-8")


def test_full_meminfo_analyzer_is_read_only() -> None:
    data = text()
    assert 'root / "poststop-after-compact" / "proc-meminfo.txt"' in data
    assert 'root / "allocator-state" / "events"' in data
    assert "systemctl" not in data
    assert "docker" not in data
    assert "sudo" not in data


def test_full_meminfo_analyzer_reports_all_deltas_and_cross_run_state() -> None:
    data = text()
    assert "meminfo_delta=" in data
    assert "meminfo_cross=R22_EVENT_MINUS_R21_EVENT" in data
    assert "ORCA_R21_R22_RM_MEMINFO_ALL=BEGIN" in data
    assert "ORCA_R21_R22_RM_MEMINFO_ALL=END" in data


def test_full_meminfo_analyzer_focuses_driver_accounting_candidates() -> None:
    data = text()
    for key in (
        "CmaFree",
        "VmallocUsed",
        "Percpu",
        "KernelStack",
        "PageTables",
        "HugePages_Total",
        "Hugetlb",
    ):
        assert f'"{key}"' in data
