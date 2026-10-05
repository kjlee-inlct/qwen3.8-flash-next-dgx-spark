from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "benchmark" / "run-orcarouter-managed-rmsys-r15-paired-watermark.sh"


def test_r15_paired_contract() -> None:
    text = SCRIPT.read_text()

    assert 'run-orcarouter-managed-rmsys-r11.sh' in text
    assert 'run-orcarouter-managed-rmsys-r14-watermark100.sh' in text
    assert 'LEG_A_OUT="${OUT}/leg-a-baseline10"' in text
    assert 'LEG_B_OUT="${OUT}/leg-b-watermark100"' in text

    assert 'EXPECTED_WATERMARK=10' in text
    assert 'EXPECTED_COMPACTION=20' in text
    assert 'WATERMARK_TUNABLE="/proc/sys/vm/watermark_scale_factor"' in text
    assert 'COMPACTION_TUNABLE="/proc/sys/vm/compaction_proactiveness"' in text

    # Leg A is an unchanged baseline R11 run. Leg B delegates the only temporary
    # watermark write/restoration to the already-tested R14 helper.
    assert 'ORCA_R11_OUT="${LEG_A_OUT}" bash "${R11}"' in text
    assert 'ORCA_R14_OUT="${LEG_B_OUT}" bash "${R14}"' in text
    assert 'tee /proc/sys/vm/watermark_scale_factor' not in text
    assert 'tee /proc/sys/vm/compaction_proactiveness' not in text
    assert 'tee /proc/sys/vm/watermark_boost_factor' not in text
    assert 'tee /proc/sys/vm/min_free_kbytes' not in text

    # Require baseline host policy both before leg A and again before treatment.
    assert text.count('check_host_baseline') >= 3
    assert 'temporary KV override is present' in text

    # Each leg must be independently valid and the final host policy must be back
    # at the measured baseline after the treatment helper returns.
    assert 'leg_a_run_valid=%s' in text
    assert 'leg_b_run_valid=%s' in text
    assert 'leg_b_watermark_restored=%s' in text
    assert 'watermark_scale_factor_final=%s' in text
    assert 'compaction_proactiveness_final=%s' in text

    # Pair classification must preserve all four valid A/B outcome combinations.
    assert 'ORCA_R15_RESULT=VALID_A_RM_B_CLEAN' in text
    assert 'ORCA_R15_RESULT=VALID_BOTH_CLEAN' in text
    assert 'ORCA_R15_RESULT=VALID_A_CLEAN_B_RM' in text
    assert 'ORCA_R15_RESULT=VALID_BOTH_RM' in text
