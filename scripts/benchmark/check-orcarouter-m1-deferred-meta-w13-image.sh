#!/usr/bin/env bash
# Validate the M1 deferred-meta-w13 image without loading a model.
set -Eeuo pipefail

IMAGE="${ORCA_M1_IMAGE:-vllm-orcarouter-v029-m1-deferred-meta-w13:v1}"
EXPECTED_STABILITY="v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla"
EXPECTED_R25="init-model-boundary-v1"
EXPECTED_R26="construction-boundary-v1"
EXPECTED_R27="w4a16-linear-boundary-v1"
EXPECTED_R28="unquant-linear-boundary-v1"
EXPECTED_M1="deferred-meta-w13-v1"
SP="/usr/local/lib/python3.12/dist-packages"
MODELOPT="${SP}/vllm/model_executor/layers/quantization/modelopt.py"
BASE_LOADER="${SP}/vllm/model_executor/model_loader/base_loader.py"
LAYERWISE="${SP}/vllm/model_executor/model_loader/reload/layerwise.py"
LINEAR="${SP}/vllm/model_executor/layers/linear.py"
LOADER_UTILS="${SP}/vllm/model_executor/model_loader/utils.py"
QWEN4="${SP}/vllm/models/qwen4_exp/nvidia/model.py"

fail() {
    printf 'M1_IMAGE_PREFLIGHT=FAIL reason=%s\n' "$*" >&2
    exit 2
}

command -v docker >/dev/null 2>&1 || fail "docker_missing"
docker image inspect "${IMAGE}" >/dev/null 2>&1 || fail "image_missing:${IMAGE}"

stability="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.stability-candidate" }}')"
r25="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r25" }}')"
r26="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r26" }}')"
r27="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r27" }}')"
r28="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r28" }}')"
m1="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.m1" }}')"

[[ "${stability}" == "${EXPECTED_STABILITY}" ]] || fail "stability_label_mismatch:${stability}"
[[ "${r25}" == "${EXPECTED_R25}" ]] || fail "r25_label_mismatch:${r25}"
[[ "${r26}" == "${EXPECTED_R26}" ]] || fail "r26_label_mismatch:${r26}"
[[ "${r27}" == "${EXPECTED_R27}" ]] || fail "r27_label_mismatch:${r27}"
[[ "${r28}" == "${EXPECTED_R28}" ]] || fail "r28_label_mismatch:${r28}"
[[ "${m1}" == "${EXPECTED_M1}" ]] || fail "m1_label_mismatch:${m1}"

docker run --rm -i --entrypoint python3 "${IMAGE}" - \
    "${MODELOPT}" "${BASE_LOADER}" "${LAYERWISE}" \
    "${LINEAR}" "${LOADER_UTILS}" "${QWEN4}" <<'PY'
import ast
import pathlib
import sys

modelopt_path, base_loader_path, layerwise_path, linear_path, loader_path, qwen4_path = (
    map(pathlib.Path, sys.argv[1:])
)
modelopt = modelopt_path.read_text(encoding="utf-8")
base_loader = base_loader_path.read_text(encoding="utf-8")
layerwise = layerwise_path.read_text(encoding="utf-8")
linear = linear_path.read_text(encoding="utf-8")
loader = loader_path.read_text(encoding="utf-8")
qwen4 = qwen4_path.read_text(encoding="utf-8")

for text in (modelopt, base_loader, layerwise, linear, loader, qwen4):
    ast.parse(text)

# Inherited diagnostic markers must remain exact.
for marker in ("QWEN38_R26_MODEL_CTOR_BEGIN", "QWEN38_R26_MODEL_CTOR_END"):
    if loader.count(marker) != 1:
        raise SystemExit(f"R26 constructor inheritance mismatch: {marker}")
for marker in (
    "QWEN38_R26_MODELOPT_MOE_BEGIN",
    "QWEN38_R26_MODELOPT_MOE_END",
    "QWEN38_R26_MODELOPT_W13_BEGIN",
    "QWEN38_R26_MODELOPT_W13_END",
):
    if modelopt.count(marker) != 1:
        raise SystemExit(f"R26 ModelOpt inheritance mismatch: {marker}")
for marker in ("QWEN38_R27_QWEN4_LAYER_BEGIN", "QWEN38_R27_QWEN4_LAYER_END"):
    if qwen4.count(marker) != 1:
        raise SystemExit(f"R27 layer inheritance mismatch: {marker}")
for marker in ("QWEN38_R28_UNQUANT_LINEAR_BEGIN", "QWEN38_R28_UNQUANT_LINEAR_END"):
    if linear.count(marker) != 1:
        raise SystemExit(f"R28 marker inheritance mismatch: {marker}")

class_start = modelopt.index("class ModelOptNvFp4FusedMoE(FusedMoEMethodBase):")
class_end = modelopt.index(
    "ModelOptNvFp4Config.LinearMethodCls = ModelOptNvFp4LinearMethod",
    class_start,
)
block = modelopt[class_start:class_end]

if block.count("QWEN38_M1_DEFERRED_META_W13_V1") != 1:
    raise SystemExit("M1 patch marker mismatch")
if block.count("uses_meta_device = True") != 1:
    raise SystemExit("M1 uses_meta_device contract mismatch")
if modelopt.count("initialize_online_processing") != 2:
    # one import + one invocation
    raise SystemExit("M1 initialize_online_processing reference mismatch")
if block.count("initialize_online_processing(layer)") != 1:
    raise SystemExit("M1 online-processing invocation mismatch")

w13_start = block.index("# GEMM 1")
w13_end = block.index('layer.register_parameter("w13_weight", w13_weight)', w13_start)
w13 = block[w13_start:w13_end]
w2_start = block.index("# GEMM 2", w13_end)
w2_end = block.index('layer.register_parameter("w2_weight", w2_weight)', w2_start)
w2 = block[w2_start:w2_end]

if w13.count("data=torch.empty(") != 1 or w13.count('device="meta"') != 1:
    raise SystemExit("M1 w13 meta-storage contract mismatch")
if w2.count("data=torch.empty(") != 1 or 'device="meta"' in w2:
    raise SystemExit("M1 w2 must preserve original storage construction")

last_reg = block.index('layer.register_parameter("w2_input_scale", w2_input_scale)')
online = block.index("initialize_online_processing(layer)")
process = block.index("def process_weights_after_loading", online)
if not (last_reg < online < process):
    raise SystemExit("M1 online-processing installation order mismatch")

# Reject the previously disproven direct-UVA/offload variants.
for forbidden in (
    "get_accelerator_view_from_cpu_tensor",
    "cudaHostAlloc",
    "cpu_offload_gb",
):
    if forbidden in block:
        raise SystemExit(f"M1 forbidden backing path present: {forbidden}")

# Native v0.29 lifecycle contracts used by M1.
for needle in (
    "getattr(quant_method, \"uses_meta_device\", False)",
    "finalize_layerwise_processing(model, model_config)",
):
    if needle not in base_loader:
        raise SystemExit(f"base-loader online-quant contract missing: {needle}")
for needle in (
    "def initialize_online_processing(layer: torch.nn.Module):",
    "materialize_layer(layer, info)",
    "quant_method.process_weights_after_loading(layer)",
):
    if needle not in layerwise:
        raise SystemExit(f"layerwise lifecycle contract missing: {needle}")

print("m1_inherited_r26_contract=PASS")
print("m1_inherited_r27_contract=PASS")
print("m1_inherited_r28_contract=PASS")
print("m1_w13_meta_only_contract=PASS")
print("m1_native_layerwise_lifecycle_contract=PASS")
print("m1_direct_uva_absent=PASS")
PY

printf 'M1_IMAGE_PREFLIGHT=PASS\n'
printf 'image=%s\n' "${IMAGE}"
printf 'stability_label=%s\n' "${stability}"
printf 'r25_label=%s\n' "${r25}"
printf 'r26_label=%s\n' "${r26}"
printf 'r27_label=%s\n' "${r27}"
printf 'r28_label=%s\n' "${r28}"
printf 'm1_label=%s\n' "${m1}"
printf 'model_restart=NO\n'
printf 'candidate_launch=NO\n'
printf 'gpu_model_launch=NO\n'
printf 'managed_service_mutation=NO\n'
printf 'kprobe_change=NO\n'
printf 'rm_trace=NO\n'
