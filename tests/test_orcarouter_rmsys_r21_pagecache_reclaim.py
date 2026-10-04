from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNNER = ROOT / "scripts" / "benchmark" / "run-orcarouter-managed-rmsys-r21-pagecache-reclaim-compact.sh"


def text() -> str:
    return RUNNER.read_text(encoding="utf-8")


def test_requires_aged_predecessor_before_mutation() -> None:
    data = text()
    assert 'MIN_PREDECESSOR_AGE_S="${ORCA_R21_MIN_PREDECESSOR_AGE_S:-2700}"' in data
    assert "predecessor-age-s.txt" in data
    assert "predecessor runtime is younger than required R21 minimum" in data
    assert data.index("PREDECESSOR_AGE_S=") < data.index('sudo -n systemctl stop "${UNIT}"')


def test_pagecache_reclaim_and_compaction_ordering() -> None:
    data = text()
    stop = data.index('sudo -n systemctl stop "${UNIT}"')
    stopped_check = data.index('predecessor container is still running after service stop')
    sync = data.index("sudo -n sync")
    drop = data.index("/proc/sys/vm/drop_caches")
    compact = data.index("/proc/sys/vm/compact_memory")
    start = data.index('sudo -n /bin/bash "${MANAGE_SERVICE}" create')
    assert stop < stopped_check < sync < drop < compact < start
    assert "poststop-before-reclaim" in data
    assert "poststop-after-sync" in data
    assert "poststop-after-drop-caches" in data
    assert "poststop-after-compact" in data


def test_one_shot_mutations_are_exact_and_no_persistent_tuning() -> None:
    data = text()
    assert data.count("/proc/sys/vm/drop_caches") == 1
    assert data.count("/proc/sys/vm/compact_memory") == 1
    assert "printf 1 > /proc/sys/vm/drop_caches" in data
    assert "printf 1 > /proc/sys/vm/compact_memory" in data
    for knob in (
        "compaction_proactiveness",
        "watermark_scale_factor",
        "watermark_boost_factor",
        "min_free_kbytes",
        "extfrag_threshold",
    ):
        assert f"/proc/sys/vm/{knob}" not in data


def test_sudo_timestamp_is_kept_alive_through_long_startup() -> None:
    data = text()
    assert 'SUDO_KEEPALIVE_PID=""' in data
    assert "sudo -n -v" in data
    assert "while sleep 60" in data
    assert 'kill "${SUDO_KEEPALIVE_PID}"' in data
    assert data.index("sudo -n -v") < data.index('sudo -n /bin/bash "${MANAGE_SERVICE}" create')
    assert data.index('sudo -n /bin/bash "${MANAGE_SERVICE}" create') < data.index("journalctl -k")


def test_r21_collects_allocator_and_strict_rm_evidence() -> None:
    data = text()
    assert "collect-linux-allocator-state.py" in data
    assert "NV_ERR_NO_MEMORY|_memdescAllocInternal" in data
    assert "event_snapshot_count" in data
    assert "restart-observed.txt" in data
    assert "api-ready.txt" in data
    assert "r21-summary.txt" in data


def test_r21_has_explicit_validity_outcomes() -> None:
    data = text()
    assert "ORCA_R21_RESULT=INVALID" in data
    assert "ORCA_R21_RESULT=VALID_CLEAN" in data
    assert "ORCA_R21_RESULT=VALID_RM_OOM" in data
    assert '"${MANAGED_RC}" != 0' in data
    assert '"${COLLECTOR_RC}" != 0' in data
    assert '"${RESTART_OBSERVED}" != 1' in data
    assert '"${API_READY}" != 1' in data
