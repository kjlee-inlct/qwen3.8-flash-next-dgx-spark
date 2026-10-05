from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "benchmark" / "run-orcarouter-managed-rmsys-r17-baseline-repeat.sh"


def test_r17_contract() -> None:
    text = SCRIPT.read_text()

    assert 'run-orcarouter-managed-rmsys-r11.sh' in text
    assert 'EXPECTED_WATERMARK=10' in text
    assert 'EXPECTED_COMPACTION=20' in text

    # R17 must not write any VM policy. It isolates restart ordinal only.
    assert 'tee "${WATERMARK_TUNABLE}"' not in text
    assert 'tee /proc/sys/vm/' not in text
    assert 'run-orcarouter-managed-rmsys-r14-watermark100.sh' not in text

    assert 'LEG_A_OUT="${OUT}/leg-a-baseline10"' in text
    assert 'LEG_B_OUT="${OUT}/leg-b-baseline10"' in text
    assert 'ORCA_R11_OUT="${LEG_A_OUT}" bash "${R11}"' in text
    assert 'ORCA_R11_OUT="${LEG_B_OUT}" bash "${R11}"' in text

    assert 'leg_a_run_valid=%s' in text
    assert 'leg_b_run_valid=%s' in text
    assert 'leg_a_rm_oom_count=%s' in text
    assert 'leg_b_rm_oom_count=%s' in text
    assert 'ORCA_R17_RESULT=VALID_A_RM_B_CLEAN' in text
    assert 'ORCA_R17_RESULT=VALID_BOTH_CLEAN' in text
    assert 'ORCA_R17_RESULT=VALID_A_CLEAN_B_RM' in text
    assert 'ORCA_R17_RESULT=VALID_BOTH_RM' in text
