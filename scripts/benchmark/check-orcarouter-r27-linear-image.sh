#!/usr/bin/env bash
# Validate the R27 marker-only diagnostic image without loading a model.
set -Eeuo pipefail

IMAGE="${ORCA_R27_IMAGE:-vllm-orcarouter-v029-r27-linear-marker:v1}"
EXPECTED_STABILITY="v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla"
EXPECTED_R25="init-model-boundary-v1"
EXPECTED_R26="construction-boundary-v1"
EXPECTED_R27="w4a16-linear-boundary-v1"
SP="/usr/local/lib/python3.12/dist-packages"
LOADER_UTILS="${SP}/vllm/model_executor/model_loader/utils.py"
MODELOPT="${SP}/vllm/model_executor/layers/quantization/modelopt.py"
QWEN4="${SP}/vllm/models/qwen4_exp/nvidia/model.py"
PLE_LAYER="${SP}/vllm/models/qwen4_exp/nvidia/ple_layer.py"
PLE_MMAP="${SP}/vllm_ple_mmap.py"

fail() {
    printf 'R27_IMAGE_PREFLIGHT=FAIL reason=%s\n' "$*" >&2
    exit 2
}

command -v docker >/dev/null 2>&1 || fail "docker_missing"
docker image inspect "${IMAGE}" >/dev/null 2>&1 || fail "image_missing:${IMAGE}"

stability="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.stability-candidate" }}')"
r25="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r25" }}')"
r26="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r26" }}')"
r27="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r27" }}')"
[[ "${stability}" == "${EXPECTED_STABILITY}" ]] || fail "stability_label_mismatch:${stability}"
[[ "${r25}" == "${EXPECTED_R25}" ]] || fail "r25_label_mismatch:${r25}"
[[ "${r26}" == "${EXPECTED_R26}" ]] || fail "r26_label_mismatch:${r26}"
[[ "${r27}" == "${EXPECTED_R27}" ]] || fail "r27_label_mismatch:${r27}"

docker run --rm -i --entrypoint python3 "${IMAGE}" - \
    "${LOADER_UTILS}" "${MODELOPT}" "${QWEN4}" "${PLE_LAYER}" "${PLE_MMAP}" <<'PY'
import ast
import pathlib
import sys

loader = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
modelopt = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
qwen4 = pathlib.Path(sys.argv[3]).read_text(encoding="utf-8")
ple_layer = pathlib.Path(sys.argv[4]).read_text(encoding="utf-8")
ple_mmap = pathlib.Path(sys.argv[5]).read_text(encoding="utf-8")
for text in (loader, modelopt, qwen4, ple_layer, ple_mmap):
    ast.parse(text)

for marker in (
    "QWEN38_R26_MODEL_CTOR_BEGIN",
    "QWEN38_R26_MODEL_CTOR_END",
):
    if loader.count(marker) != 1:
        raise SystemExit(f"R26 constructor inheritance mismatch: {marker}")

for marker in (
    "QWEN38_R26_MODELOPT_MOE_BEGIN",
    "QWEN38_R26_MODELOPT_MOE_END",
    "QWEN38_R26_MODELOPT_W13_BEGIN",
    "QWEN38_R26_MODELOPT_W13_END",
    "QWEN38_R26_MODELOPT_W2_BEGIN",
    "QWEN38_R26_MODELOPT_W2_END",
):
    if modelopt.count(marker) != 1:
        raise SystemExit(f"R26 ModelOpt inheritance mismatch: {marker}")

for marker in (
    "QWEN38_R27_W4A16_LINEAR_BEGIN",
    "QWEN38_R27_W4A16_LINEAR_END",
    "QWEN38_R27_W4A16_WEIGHT_BEGIN",
    "QWEN38_R27_W4A16_WEIGHT_END",
):
    if modelopt.count(marker) != 1:
        raise SystemExit(f"R27 W4A16 marker contract mismatch: {marker}")
if modelopt.count("_QWEN38_R27_W4A16_LINEAR_SEQ = 0") != 1:
    raise SystemExit("R27 W4A16 sequence-counter contract mismatch")
if "class ModelOptNvFp4W4A16LinearMethod" not in modelopt:
    raise SystemExit("R27 W4A16 class missing")

for marker in (
    "QWEN38_R27_QWEN4_LAYER_BEGIN",
    "QWEN38_R27_QWEN4_LAYER_END",
):
    if qwen4.count(marker) != 1:
        raise SystemExit(f"R27 Qwen4Exp layer marker contract mismatch: {marker}")
if qwen4.count("_QWEN38_R27_QWEN4_LAYER_SEQ = 0") != 1:
    raise SystemExit("R27 Qwen4Exp sequence-counter contract mismatch")
for needle in ("class Qwen4ExpDecoderLayer", "class Qwen4ExpForCausalLM"):
    if needle not in qwen4:
        raise SystemExit(f"R27 exact Qwen4Exp source contract missing: {needle}")

# PLE mmap constructor exclusion contract: v0.29 patch replaces the giant
# PLEVocabParallelEmbedding with a tiny placeholder and passes quant_config=None.
if "_ple_mmap_apply(Qwen4ExpNGramEmbedding)" not in ple_layer:
    raise SystemExit("R27 PLE mmap hook missing")
for needle in (
    "def _apply_v029(cls: type)",
    'embed_attr = "PLEVocabParallelEmbedding"',
    "_MmapNgramEmbedding(n, d)",
    "quant_config=None",
):
    if needle not in ple_mmap:
        raise SystemExit(f"R27 PLE mmap placeholder contract missing: {needle}")

print("r26_inherited_constructor_contract=PASS")
print("r26_inherited_modelopt_moe_contract=PASS")
print("r27_w4a16_linear_contract=PASS")
print("r27_qwen4_layer_contract=PASS")
print("r27_ple_mmap_placeholder_contract=PASS")
PY

printf 'R27_IMAGE_PREFLIGHT=PASS\n'
printf 'image=%s\n' "${IMAGE}"
printf 'stability_label=%s\n' "${stability}"
printf 'r25_label=%s\n' "${r25}"
printf 'r26_label=%s\n' "${r26}"
printf 'r27_label=%s\n' "${r27}"
printf 'model_restart=NO\n'
printf 'managed_service_mutation=NO\n'
printf 'persistent_vm_tuning=NO\n'
