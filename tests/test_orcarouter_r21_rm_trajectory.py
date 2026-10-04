from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "benchmark" / "analyze-orcarouter-r21-rm-trajectory.py"


def text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_trajectory_uses_existing_r21_evidence_only() -> None:
    data = text()
    assert 'parser.add_argument("--r21", required=True' in data
    assert 'state / "fast-state.txt"' in data
    assert 'state / "slow-state.txt"' in data
    assert 'parse_event_meta(state / "events")' in data
    assert "systemctl" not in data
    assert "docker" not in data
    assert "sudo" not in data


def test_trajectory_tracks_pre_event_offsets() -> None:
    data = text()
    assert "TARGET_OFFSETS_S = (-60, -30, -10, -5, -1, 0)" in data
    assert "sample_offset_s=" in data
    assert "r21_fast" in data
    assert "r21_slow" in data


def test_trajectory_tracks_relevant_allocator_metrics() -> None:
    data = text()
    for token in (
        '"memavailable"',
        '"memfree"',
        '"cached"',
        '"inactive_file"',
        '"swapfree"',
        '"normal_o4"',
        '"normal_o5plus"',
        '"normal_o4plus"',
        '"unmovable_o4plus"',
        '"movable_o4plus"',
    ):
        assert token in data


def test_trajectory_requires_exactly_one_rm_event() -> None:
    data = text()
    assert 'glob("rm-oom-*")' in data
    assert "expected exactly one RM event directory" in data
