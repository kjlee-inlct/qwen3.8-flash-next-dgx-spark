from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
FINALIZER = ROOT / "scripts" / "benchmark" / "finalize-orcarouter-r21-incomplete.sh"


def text() -> str:
    return FINALIZER.read_text(encoding="utf-8")


def test_requires_existing_partial_evidence_and_sudo_timestamp() -> None:
    data = text()
    assert 'sudo -n true' in data
    for name in (
        "start-epoch.txt",
        "end-epoch.txt",
        "container-id-before.txt",
        "managed-command.rc",
        "collector.rc",
    ):
        assert name in data


def test_rebuilds_kernel_and_strict_rm_evidence() -> None:
    data = text()
    assert "journalctl -k" in data
    assert "NV_ERR_NO_MEMORY|_memdescAllocInternal" in data
    assert "kernel-window.txt" in data
    assert "kernel-errors.txt" in data
    assert "event_snapshot_count" in data


def test_rejects_unrelated_later_container() -> None:
    data = text()
    assert "candidate-started-in-run-window.txt" in data
    assert "CANDIDATE_IN_WINDOW" in data
    assert '"${POST_CONTAINER_ID}" != "${PRE_CONTAINER_ID}"' in data
    assert 'begin <= started <= end' in data


def test_emits_explicit_final_result() -> None:
    data = text()
    assert "r21-summary.txt" in data
    assert "ORCA_R21_FINAL_RESULT=INVALID" in data
    assert "ORCA_R21_FINAL_RESULT=VALID_CLEAN" in data
    assert "ORCA_R21_FINAL_RESULT=VALID_RM_OOM" in data
