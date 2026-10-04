from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
ANALYZER = ROOT / "scripts" / "benchmark" / "analyze-orcarouter-r21-rm-collapse.py"


def text() -> str:
    return ANALYZER.read_text(encoding="utf-8")


def test_collapse_analyzer_uses_existing_r21_evidence_only() -> None:
    data = text()
    assert 'root / "compact-complete-iso.txt"' in data
    assert 'state / "fast-state.txt"' in data
    assert 'state / "slow-state.txt"' in data
    assert 'root / "allocator-state/events"' in data
    assert "systemctl" not in data
    assert "docker" not in data
    assert "sudo" not in data


def test_collapse_analyzer_reports_threshold_crossings_and_largest_drops() -> None:
    data = text()
    assert '"UNMOVABLE_O4PLUS"' in data
    assert '"NORMAL_O4PLUS"' in data
    assert 'largest_drop("UNMOVABLE_O4PLUS"' in data
    assert 'largest_drop("MOVABLE_O4PLUS"' in data
    assert 'largest_drop("NORMAL_O4PLUS"' in data
    assert "initial_u * 0.5" in data
    assert "initial_u * 0.1" in data
    assert "initial_u * 0.01" in data
    assert "1024.0" in data
    assert "100.0" in data
    assert "10.0" in data


def test_collapse_analyzer_limits_samples_to_postcompact_pre_event_window() -> None:
    data = text()
    assert "compact_done <= wall <= event_wall" in data
    assert "ORCA_R21_RM_COLLAPSE=BEGIN" in data
    assert "ORCA_R21_RM_COLLAPSE=END" in data
