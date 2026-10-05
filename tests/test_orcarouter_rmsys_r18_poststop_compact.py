from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNNER = ROOT / "scripts" / "benchmark" / "run-orcarouter-managed-rmsys-r18-poststop-compact.sh"


def text() -> str:
    return RUNNER.read_text(encoding="utf-8")


def test_requires_aged_predecessor_before_mutating_host() -> None:
    data = text()
    assert 'MIN_PREDECESSOR_AGE_S="${ORCA_R18_MIN_PREDECESSOR_AGE_S:-2700}"' in data
    assert "predecessor-age-s.txt" in data
    assert "predecessor runtime is younger than required R18 minimum" in data
    assert data.index("PREDECESSOR_AGE_S=") < data.index('sudo -n systemctl stop "${UNIT}"')


def test_compaction_occurs_only_after_full_service_stop() -> None:
    data = text()
    stop = data.index('sudo -n systemctl stop "${UNIT}"')
    stopped_check = data.index('predecessor container is still running after service stop')
    compact = data.index("/proc/sys/vm/compact_memory")
    start = data.index('sudo -n /bin/bash "${MANAGE_SERVICE}" create')
    assert stop < stopped_check < compact < start
    assert "poststop-before-compact" in data
    assert "poststop-after-compact" in data


def test_compact_memory_is_written_exactly_once_without_persistent_vm_tuning() -> None:
    data = text()
    assert data.count("/proc/sys/vm/compact_memory") == 1
    for knob in (
        "compaction_proactiveness",
        "watermark_scale_factor",
        "watermark_boost_factor",
        "min_free_kbytes",
        "extfrag_threshold",
    ):
        assert f"/proc/sys/vm/{knob}" not in data


def test_r18_collects_allocator_state_and_strict_rm_signature() -> None:
    data = text()
    assert "collect-linux-allocator-state.py" in data
    assert "NV_ERR_NO_MEMORY|_memdescAllocInternal" in data
    assert "event_snapshot_count" in data
    assert "restart-observed.txt" in data
    assert "api-ready.txt" in data


def test_r18_has_explicit_validity_outcomes() -> None:
    data = text()
    assert "ORCA_R18_RESULT=INVALID" in data
    assert "ORCA_R18_RESULT=VALID_CLEAN" in data
    assert "ORCA_R18_RESULT=VALID_RM_OOM" in data
    assert '"${MANAGED_RC}" != 0' in data
    assert '"${COLLECTOR_RC}" != 0' in data
    assert '"${RESTART_OBSERVED}" != 1' in data
    assert '"${API_READY}" != 1' in data
