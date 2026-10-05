from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "benchmark" / "compare-orcarouter-r21-r22-rm-memory.py"


def text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_comparison_is_read_only_and_uses_existing_evidence() -> None:
    data = text()
    assert 'root / "poststop-after-compact" / "proc-meminfo.txt"' in data
    assert 'root / "allocator-state" / "events"' in data
    assert 'glob("rm-oom-*")' in data
    assert "systemctl" not in data
    assert "docker" not in data
    assert "sudo" not in data


def test_comparison_covers_memory_composition_dimensions() -> None:
    data = text()
    for key in (
        "AnonPages",
        "Active(anon)",
        "Inactive(anon)",
        "Active(file)",
        "Inactive(file)",
        "Shmem",
        "Slab",
        "SReclaimable",
        "SUnreclaim",
        "KernelStack",
        "PageTables",
        "Unevictable",
        "Mlocked",
        "SwapFree",
    ):
        assert f'"{key}"' in data


def test_comparison_emits_per_run_delta_and_cross_run_event_delta() -> None:
    data = text()
    assert "ORCA_R21_R22_RM_MEMORY=BEGIN" in data
    assert "rm_memory_delta={run}_POST_TO_EVENT" in data
    assert "rm_memory_cross=R22_EVENT_MINUS_R21_EVENT" in data
    assert "ORCA_R21_R22_RM_MEMORY=END" in data
