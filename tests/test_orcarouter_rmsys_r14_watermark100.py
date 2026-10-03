from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "benchmark" / "run-orcarouter-managed-rmsys-r14-watermark100.sh"


def test_r14_contract() -> None:
    text = SCRIPT.read_text()

    assert 'TUNABLE="/proc/sys/vm/watermark_scale_factor"' in text
    assert 'COMPACTION_TUNABLE="/proc/sys/vm/compaction_proactiveness"' in text
    assert "EXPECTED_ORIGINAL=10" in text
    assert "EXPECTED_COMPACTION=20" in text
    assert "TARGET=100" in text

    # Exactly the watermark knob is written by the experiment helper.
    assert 'tee "${TUNABLE}"' in text
    assert 'tee /proc/sys/vm/compact_memory' not in text
    assert 'tee /proc/sys/vm/compaction_proactiveness' not in text
    assert 'tee /proc/sys/vm/watermark_boost_factor' not in text
    assert 'tee /proc/sys/vm/min_free_kbytes' not in text

    # Refuse an unexpected baseline so the A/B cannot silently inherit a prior tuning.
    assert 'expected watermark_scale_factor=${EXPECTED_ORIGINAL}' in text
    assert 'expected compaction_proactiveness=${EXPECTED_COMPACTION}' in text

    # Restore the original watermark on normal/error/signal paths.
    assert "trap cleanup EXIT INT TERM" in text
    assert "restore_tunable" in text
    assert 'watermark_scale_factor_restored=%s' in text

    # Preserve the proven managed restart/trace contract and classify zero RM events strictly.
    assert 'run-orcarouter-managed-rmsys-r11.sh' in text
    assert 'ORCA_R11_OUT="${R11_OUT}" bash "${R11}"' in text
    assert 'rm_oom_count=%s' in text
    assert 'ORCA_R14_RESULT=VALID_CLEAN' in text
    assert 'ORCA_R14_RESULT=VALID_RM_OOM' in text
