from __future__ import annotations

import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "benchmark" / "analyze-orcarouter-r21-rm-event.py"


def write_snapshot(path: pathlib.Path, *, normal: str, unmovable: str, movable: str, memfree_kib: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "proc-buddyinfo.txt").write_text(
        f"Node 0, zone   Normal {normal}\n", encoding="utf-8"
    )
    (path / "proc-pagetypeinfo.txt").write_text(
        "\n".join(
            (
                f"Node 0, zone   Normal, type    Unmovable {unmovable}",
                f"Node 0, zone   Normal, type      Movable {movable}",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    (path / "proc-meminfo.txt").write_text(
        "\n".join(
            (
                "MemAvailable: 200000 kB",
                f"MemFree: {memfree_kib} kB",
                "Cached: 1000 kB",
                "Inactive(file): 500 kB",
                "SwapFree: 300000 kB",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def test_compares_postcompact_with_exactly_one_rm_event(tmp_path: pathlib.Path) -> None:
    write_snapshot(
        tmp_path / "poststop-after-compact",
        normal="0 0 0 0 16 8",
        unmovable="0 0 0 0 8 4",
        movable="0 0 0 0 8 4",
        memfree_kib=100000,
    )
    event = tmp_path / "allocator-state" / "events" / "rm-oom-01-123"
    write_snapshot(
        event,
        normal="0 0 0 0 4 2",
        unmovable="0 0 0 0 2 1",
        movable="0 0 0 0 2 1",
        memfree_kib=50000,
    )
    (event / "meta.txt").write_text("wall=2026-10-04T00:00:00+00:00\nmonotonic_ns=123\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--r21", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "ORCA_R21_RM_EVENT_ANALYSIS=BEGIN" in result.stdout
    assert "r21_rm_event_dir=rm-oom-01-123" in result.stdout
    assert "r21_rm_state=POST_COMPACT" in result.stdout
    assert "r21_rm_state=RM_EVENT" in result.stdout
    assert "r21_rm_delta=POST_COMPACT_TO_RM_EVENT" in result.stdout


def test_rejects_missing_rm_event(tmp_path: pathlib.Path) -> None:
    write_snapshot(
        tmp_path / "poststop-after-compact",
        normal="0 0 0 0 1",
        unmovable="0 0 0 0 1",
        movable="0 0 0 0 0",
        memfree_kib=1000,
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--r21", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "expected exactly one R21 RM event snapshot" in result.stderr
