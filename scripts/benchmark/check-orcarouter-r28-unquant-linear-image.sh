#!/usr/bin/env bash
# Validate the R28 marker-only diagnostic image without loading a model.
set -Eeuo pipefail

IMAGE="${ORCA_R28_IMAGE:-vllm-orcarouter-v029-r28-unquant-linear-marker:v1}"
EXPECTED_STABILITY="v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla"
EXPECTED_R25="init-model-boundary-v1"
EXPECTED_R26="construction-boundary-v1"
EXPECTED_R27="w4a16-linear-boundary-v1"
EXPECTED_R28="unquant-linear-boundary-v1"
SP="/usr/local/lib/python3.12/dist-packages"
LINEAR="${SP}/vllm/model_executor/layers/linear.py"
LOADER="${SP}/vllm/model_executor/model_loader/utils.py"
MODELOPT="${SP}/vllm/model_executor/layers/quantization/modelopt.py"
QWEN4="${SP}/vllm/models/qwen4_exp/nvidia/model.py"

fail() {
    printf 'R28_IMAGE_PREFLIGHT=FAIL reason=%s\n' "$*" >&2
    exit 2
}

command -v docker >/dev/null 2>&1 || fail "docker_missing"
docker image inspect "${IMAGE}" >/dev/null 2>&1 || fail "image_missing:${IMAGE}"

stability="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.stability-candidate" }}')"
r25="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r25" }}')"
r26="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r26" }}')"
r27="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r27" }}')"
r28="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r28" }}')"
[[ "${stability}" == "${EXPECTED_STABILITY}" ]] || fail "stability_label_mismatch:${stability}"
[[ "${r25}" == "${EXPECTED_R25}" ]] || fail "r25_label_mismatch:${r25}"
[[ "${r26}" == "${EXPECTED_R26}" ]] || fail "r26_label_mismatch:${r26}"
[[ "${r27}" == "${EXPECTED_R27}" ]] || fail "r27_label_mismatch:${r27}"
[[ "${r28}" == "${EXPECTED_R28}" ]] || fail "r28_label_mismatch:${r28}"

docker run --rm -i --entrypoint python3 "${IMAGE}" - \
    "${LINEAR}" "${LOADER}" "${MODELOPT}" "${QWEN4}" <<'PY'
import ast
import pathlib
import sys

linear = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
loader = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
modelopt = pathlib.Path(sys.argv[3]).read_text(encoding="utf-8")
qwen4 = pathlib.Path(sys.argv[4]).read_text(encoding="utf-8")
for text in (linear, loader, modelopt, qwen4):
    ast.parse(text)

for marker in ("QWEN38_R26_MODEL_CTOR_BEGIN", "QWEN38_R26_MODEL_CTOR_END"):
    if loader.count(marker) != 1:
        raise SystemExit(f"R26 constructor inheritance mismatch: {marker}")
for marker in ("QWEN38_R26_MODELOPT_MOE_BEGIN", "QWEN38_R26_MODELOPT_MOE_END"):
    if modelopt.count(marker) != 1:
        raise SystemExit(f"R26 ModelOpt inheritance mismatch: {marker}")
for marker in ("QWEN38_R27_QWEN4_LAYER_BEGIN", "QWEN38_R27_QWEN4_LAYER_END"):
    if qwen4.count(marker) != 1:
        raise SystemExit(f"R27 layer inheritance mismatch: {marker}")
for marker in ("QWEN38_R28_UNQUANT_LINEAR_BEGIN", "QWEN38_R28_UNQUANT_LINEAR_END"):
    if linear.count(marker) != 1:
        raise SystemExit(f"R28 marker contract mismatch: {marker}")
if linear.count("_QWEN38_R28_UNQUANT_LINEAR_SEQ = 0") != 1:
    raise SystemExit("R28 sequence-counter contract mismatch")
for needle in (
    "class UnquantizedLinearMethod",
    "data=torch.empty(",
    "self.quant_method = UnquantizedLinearMethod()",
):
    if needle not in linear:
        raise SystemExit(f"R28 unquantized Linear source contract missing: {needle}")

print("r26_inherited_constructor_contract=PASS")
print("r26_inherited_modelopt_moe_contract=PASS")
print("r27_inherited_qwen4_layer_contract=PASS")
print("r28_unquant_linear_contract=PASS")
PY

printf 'R28_IMAGE_PREFLIGHT=PASS\n'
printf 'image=%s\n' "${IMAGE}"
printf 'stability_label=%s\n' "${stability}"
printf 'r25_label=%s\n' "${r25}"
printf 'r26_label=%s\n' "${r26}"
printf 'r27_label=%s\n' "${r27}"
printf 'r28_label=%s\n' "${r28}"
printf 'model_restart=NO\n'
printf 'managed_service_mutation=NO\n'
printf 'persistent_vm_tuning=NO\n'
