from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
EVENT = ROOT / "scripts" / "benchmark" / "analyze-orcarouter-r22-rm-event.py"
COLLAPSE = ROOT / "scripts" / "benchmark" / "analyze-orcarouter-r22-rm-collapse.py"


def event_text() -> str:
    return EVENT.read_text(encoding="utf-8")


def collapse_text() -> str:
    return COLLAPSE.read_text(encoding="utf-8")


def test_r22_event_analyzer_is_read_only_and_uses_single_event() -> None:
    data = event_text()
    assert 'root / "poststop-after-compact"' in data
    assert 'root / "allocator-state" / "events"' in data
    assert 'glob("rm-oom-*")' in data
    assert "expected exactly one R22 RM event snapshot" in data
    assert "ORCA_R22_RM_EVENT_ANALYSIS=BEGIN" in data
    assert "ORCA_R22_RM_EVENT_ANALYSIS=END" in data
    assert "systemctl" not in data
    assert "docker" not in data
    assert "sudo" not in data


def test_r22_event_analyzer_reports_allocator_dimensions() -> None:
    data = event_text()
    for token in (
        '"memavailable"',
        '"memfree"',
        '"cached"',
        '"inactive_file"',
        '"swapfree"',
        '"normal_o4plus"',
        '"unmovable_o4plus"',
        '"movable_o4plus"',
    ):
        assert token in data
    assert "POST_COMPACT_TO_RM_EVENT" in data


def test_r22_collapse_analyzer_uses_existing_evidence_only() -> None:
    data = collapse_text()
    assert 'root / "compact-complete-iso.txt"' in data
    assert 'state / "fast-state.txt"' in data
    assert 'state / "slow-state.txt"' in data
    assert 'root / "allocator-state/events"' in data
    assert "compact_done <= wall <= event_wall" in data
    assert "systemctl" not in data
    assert "docker" not in data
    assert "sudo" not in data


def test_r22_collapse_analyzer_reports_thresholds_and_largest_drops() -> None:
    data = collapse_text()
    assert '"UNMOVABLE_O4PLUS"' in data
    assert '"NORMAL_O4PLUS"' in data
    assert 'largest_drop("UNMOVABLE_O4PLUS"' in data
    assert 'largest_drop("MOVABLE_O4PLUS"' in data
    assert 'largest_drop("NORMAL_O4PLUS"' in data
    assert "initial_u * 0.5" in data
    assert "initial_u * 0.1" in data
    assert "initial_u * 0.01" in data
    assert "ORCA_R22_RM_COLLAPSE=BEGIN" in data
    assert "ORCA_R22_RM_COLLAPSE=END" in data
