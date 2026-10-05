from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "benchmark" / "run-orcarouter-managed-rmsys-r16-reverse-watermark.sh"


def test_r16_reverse_pair_contract() -> None:
    text = SCRIPT.read_text()

    assert 'R11="${SCRIPT_ROOT}/scripts/benchmark/run-orcarouter-managed-rmsys-r11.sh"' in text
    assert 'R14="${SCRIPT_ROOT}/scripts/benchmark/run-orcarouter-managed-rmsys-r14-watermark100.sh"' in text

    # Reverse R15 ordering: treatment first, restored baseline second.
    treatment = 'ORCA_R14_OUT="${LEG_A_OUT}" bash "${R14}"'
    baseline = 'ORCA_R11_OUT="${LEG_B_OUT}" bash "${R11}"'
    assert treatment in text
    assert baseline in text
    assert text.index(treatment) < text.index(baseline)

    assert 'LEG_A_OUT="${OUT}/leg-a-watermark100"' in text
    assert 'LEG_B_OUT="${OUT}/leg-b-baseline10"' in text

    # The treatment helper must report restoration before baseline leg B starts.
    assert 'LEG_A_RESTORED="$(read_summary_value "${LEG_A_OUT}/r14-summary.txt" watermark_scale_factor_restored)"' in text
    assert 'R14 did not report watermark restoration' in text
    assert text.count("check_host_baseline") >= 3

    # Host policy remains baseline after the complete reverse pair.
    assert "EXPECTED_WATERMARK=10" in text
    assert "EXPECTED_COMPACTION=20" in text
    assert 'watermark_scale_factor_final=%s' in text
    assert 'compaction_proactiveness_final=%s' in text

    # Most discriminating reverse-order result is treatment clean then baseline RM.
    assert 'ORCA_R16_RESULT=VALID_A_CLEAN_B_RM' in text
    assert 'ORCA_R16_RESULT=VALID_BOTH_CLEAN' in text
    assert 'ORCA_R16_RESULT=VALID_A_RM_B_CLEAN' in text
    assert 'ORCA_R16_RESULT=VALID_BOTH_RM' in text

    # No additional VM knob is changed by R16 itself.
    assert 'tee /proc/sys/vm/' not in text
