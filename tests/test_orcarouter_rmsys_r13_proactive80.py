from pathlib import Path


SCRIPT = Path("scripts/benchmark/run-orcarouter-managed-rmsys-r13-proactive80.sh")


def test_r13_uses_r11_contract_and_single_vm_policy() -> None:
    text = SCRIPT.read_text()

    assert 'run-orcarouter-managed-rmsys-r11.sh' in text
    assert 'ORCA_R11_OUT="${R11_OUT}" bash "${R11}"' in text
    assert 'TUNABLE="/proc/sys/vm/compaction_proactiveness"' in text
    assert 'EXPECTED_ORIGINAL=20' in text
    assert 'TARGET=80' in text
    assert '/proc/sys/vm/compact_memory' not in text

    # R13 must not directly write any other VM tuning knob.
    for name in (
        "compact_unevictable_allowed",
        "extfrag_threshold",
        "min_free_kbytes",
        "watermark_boost_factor",
        "watermark_scale_factor",
    ):
        assert f'/proc/sys/vm/{name}' not in text


def test_r13_restores_policy_on_success_and_failure_paths() -> None:
    text = SCRIPT.read_text()

    assert 'trap cleanup EXIT INT TERM' in text
    assert 'restore_tunable()' in text
    assert 'restore_tunable\nRESTORED=' in text
    assert 'failed to restore compaction_proactiveness' in text
    assert 'refusing to change an unexpected host policy' in text


def test_r13_captures_validity_and_rm_result() -> None:
    text = SCRIPT.read_text()

    assert "r13-summary.txt" in text
    assert "run_valid=%s" in text
    assert "rm_oom_count=%s" in text
    assert "compaction_proactiveness_original=%s" in text
    assert "compaction_proactiveness_target=%s" in text
    assert "compaction_proactiveness_restored=%s" in text
    assert "ORCA_R13_RESULT=VALID_CLEAN" in text
    assert "ORCA_R13_RESULT=VALID_RM_OOM" in text
    assert "ORCA_R13_RESULT=INVALID" in text
