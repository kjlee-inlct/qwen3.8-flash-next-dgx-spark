#!/usr/bin/env bash
# Validate the R26 marker-only diagnostic image without loading a model.
set -Eeuo pipefail

IMAGE="${ORCA_R26_IMAGE:-vllm-orcarouter-v029-r26-construction-marker:v1}"
EXPECTED_STABILITY="v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla"
EXPECTED_R25="init-model-boundary-v1"
EXPECTED_R26="construction-boundary-v1"
SP="/usr/local/lib/python3.12/dist-packages"
LOADER_UTILS="${SP}/vllm/model_executor/model_loader/utils.py"
MODELOPT="${SP}/vllm/model_executor/layers/quantization/modelopt.py"
BASE_LOADER="${SP}/vllm/model_executor/model_loader/base_loader.py"

fail() {
    printf 'R26_IMAGE_PREFLIGHT=FAIL reason=%s\n' "$*" >&2
    exit 2
}

command -v docker >/dev/null 2>&1 || fail "docker_missing"
docker image inspect "${IMAGE}" >/dev/null 2>&1 || fail "image_missing:${IMAGE}"

stability="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.stability-candidate" }}')"
r25="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r25" }}')"
r26="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r26" }}')"
[[ "${stability}" == "${EXPECTED_STABILITY}" ]] || fail "stability_label_mismatch:${stability}"
[[ "${r25}" == "${EXPECTED_R25}" ]] || fail "r25_label_mismatch:${r25}"
[[ "${r26}" == "${EXPECTED_R26}" ]] || fail "r26_label_mismatch:${r26}"

docker run --rm -i --entrypoint python3 "${IMAGE}" - \
    "${BASE_LOADER}" "${LOADER_UTILS}" "${MODELOPT}" <<'PY'
import ast
import pathlib
import sys

base_loader = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
loader = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
modelopt = pathlib.Path(sys.argv[3]).read_text(encoding="utf-8")
for text in (base_loader, loader, modelopt):
    ast.parse(text)

r25_begin = 'logger.info("QWEN38_R25_INIT_MODEL_BEGIN")'
r25_init = "model = initialize_model("
r25_end = 'logger.info("QWEN38_R25_INIT_MODEL_END")'
for needle in (r25_begin, r25_init, r25_end):
    if base_loader.count(needle) != 1:
        raise SystemExit(f"R25 inherited contract mismatch: {needle!r}")
if not (base_loader.index(r25_begin) < base_loader.index(r25_init) < base_loader.index(r25_end)):
    raise SystemExit("R25 inherited marker ordering mismatch")

ctor_begin = "QWEN38_R26_MODEL_CTOR_BEGIN"
ctor_call = "model = model_class(vllm_config=vllm_config, prefix=prefix)"
ctor_end = "QWEN38_R26_MODEL_CTOR_END"
for needle in (ctor_begin, ctor_call, ctor_end):
    if loader.count(needle) != 1:
        raise SystemExit(f"R26 model-constructor contract mismatch: {needle!r}")
if not (loader.index(ctor_begin) < loader.index(ctor_call) < loader.index(ctor_end)):
    raise SystemExit("R26 model-constructor marker ordering mismatch")

markers = (
    "QWEN38_R26_MODELOPT_MOE_BEGIN",
    "QWEN38_R26_MODELOPT_MOE_END",
    "QWEN38_R26_MODELOPT_W13_BEGIN",
    "QWEN38_R26_MODELOPT_W13_END",
    "QWEN38_R26_MODELOPT_W2_BEGIN",
    "QWEN38_R26_MODELOPT_W2_END",
)
for marker in markers:
    if modelopt.count(marker) != 1:
        raise SystemExit(f"R26 ModelOpt marker contract mismatch: {marker}")
if modelopt.count("_QWEN38_R26_MODELOPT_MOE_SEQ = 0") != 1:
    raise SystemExit("R26 ModelOpt sequence-counter contract mismatch")
if '"W4A16_NVFP4"' not in modelopt:
    raise SystemExit("R26 expected W4A16_NVFP4 support missing")

print("r25_inherited_marker_contract=PASS")
print("r26_model_constructor_contract=PASS")
print("r26_modelopt_moe_contract=PASS")
PY

printf 'R26_IMAGE_PREFLIGHT=PASS\n'
printf 'image=%s\n' "${IMAGE}"
printf 'stability_label=%s\n' "${stability}"
printf 'r25_label=%s\n' "${r25}"
printf 'r26_label=%s\n' "${r26}"
printf 'model_restart=NO\n'
printf 'managed_service_mutation=NO\n'
printf 'persistent_vm_tuning=NO\n'
