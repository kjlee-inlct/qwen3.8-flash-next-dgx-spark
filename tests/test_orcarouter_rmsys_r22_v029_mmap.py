from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNNER = ROOT / "scripts" / "benchmark" / "run-orcarouter-managed-rmsys-r22-v029-mmap.sh"


def text() -> str:
    return RUNNER.read_text(encoding="utf-8")


def test_r22_requires_aged_managed_orca_predecessor_before_mutation() -> None:
    data = text()
    assert 'MIN_PREDECESSOR_AGE_S="${ORCA_R22_MIN_PREDECESSOR_AGE_S:-2700}"' in data
    assert '[[ "${MODEL_PROFILE}" == orcarouter ]]' in data
    assert "predecessor-age-s.txt" in data
    assert data.index("PREDECESSOR_AGE_S=") < data.index('sudo -n systemctl stop "${UNIT}"')


def test_r22_matches_r21_preconditioning_order() -> None:
    data = text()
    stop = data.index('sudo -n systemctl stop "${UNIT}"')
    sync = data.index("sudo -n sync")
    drop = data.index("/proc/sys/vm/drop_caches")
    compact = data.index("/proc/sys/vm/compact_memory")
    candidate = data.index("docker run -d")
    assert stop < sync < drop < compact < candidate
    assert data.count("/proc/sys/vm/drop_caches") == 1
    assert data.count("/proc/sys/vm/compact_memory") == 1


def test_r22_is_pinned_to_mmap_and_managed_16gib_kv() -> None:
    data = text()
    assert 'KV_BYTES="${ORCA_R22_KV_BYTES:-17179869184}"' in data
    assert '[[ "${KV_BYTES}" == 17179869184 ]]' in data
    assert "-e VLLM_PLE_MMAP=1" in data
    assert "-e VLLM_PLE_MMAP_PREWARM=0" in data
    assert "-e VLLM_PLE_MMAP_MADVISE=random" in data
    assert "--kv-cache-memory-bytes \"${KV_BYTES}\"" in data
    assert "VLLM_PLE_CPU_OFFLOAD=1" in data
    assert "unexpectedly enables legacy PLE CPU offload" in data


def test_r22_preserves_context_and_sequence_controls() -> None:
    data = text()
    assert "--max-model-len 262144" in data
    assert "--max-num-seqs 3" in data
    assert "--max-num-batched-tokens 8192" in data
    assert "--speculative-config '{\"method\":\"mtp\",\"num_speculative_tokens\":2}'" in data


def test_r22_uses_same_allocator_and_host_protection_evidence() -> None:
    data = text()
    assert "collect-linux-allocator-state.py" in data
    assert "--fast-interval 1" in data
    assert "--slow-interval 5" in data
    assert "--min-available-gib 6" in data
    assert "--min-free-gib 2" in data
    assert "--free-gate-gib 10" in data
    assert "--min-swap-free-gib 8" in data
    assert "--consecutive 5" in data
    assert "--protect" in data
    assert "NV_ERR_NO_MEMORY|_memdescAllocInternal" in data


def test_r22_restores_managed_service_after_preserving_candidate() -> None:
    data = text()
    assert 'docker stop --timeout 30 "${EXPERIMENT_CONTAINER}"' in data
    assert 'sudo -n systemctl start "${UNIT}"' in data
    assert "managed-restore-started-iso.txt" in data


def test_r22_has_explicit_strict_outcomes() -> None:
    data = text()
    assert "ORCA_R22_RESULT=INVALID" in data
    assert "ORCA_R22_RESULT=VALID_CLEAN" in data
    assert "ORCA_R22_RESULT=VALID_RM_OOM" in data
    assert "protected_stop" in data
    assert "event_snapshot_count" in data
    assert "r22-summary.txt" in data
