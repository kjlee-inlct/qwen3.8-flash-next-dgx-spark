#!/usr/bin/env bash
# Validate the R25b marker-only diagnostic image without loading a model.
set -Eeuo pipefail

IMAGE="${ORCA_R25B_IMAGE:-vllm-orcarouter-v029-r25-init-marker:v1}"
EXPECTED_STABILITY="v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla"
EXPECTED_R25="init-model-boundary-v1"
BASE_LOADER="/usr/local/lib/python3.12/dist-packages/vllm/model_executor/model_loader/base_loader.py"

fail() {
    printf 'R25B_IMAGE_PREFLIGHT=FAIL reason=%s\n' "$*" >&2
    exit 2
}

command -v docker >/dev/null 2>&1 || fail "docker_missing"
docker image inspect "${IMAGE}" >/dev/null 2>&1 || fail "image_missing:${IMAGE}"

stability="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.stability-candidate" }}')"
r25="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.r25" }}')"
[[ "${stability}" == "${EXPECTED_STABILITY}" ]] || fail "stability_label_mismatch:${stability}"
[[ "${r25}" == "${EXPECTED_R25}" ]] || fail "r25_label_mismatch:${r25}"

docker run --rm -i --entrypoint python3 "${IMAGE}" - "${BASE_LOADER}" <<'PY'
import ast
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
ast.parse(text)

begin = 'logger.info("QWEN38_R25_INIT_MODEL_BEGIN")'
init = "model = initialize_model("
end = 'logger.info("QWEN38_R25_INIT_MODEL_END")'
weights = "self.load_weights(model, model_config)"

for needle in (begin, init, end, weights):
    if text.count(needle) != 1:
        raise SystemExit(f"marker/source contract mismatch: {needle!r}")

if not (text.index(begin) < text.index(init) < text.index(end) < text.index(weights)):
    raise SystemExit("R25 initialize_model marker ordering mismatch")

print("r25_marker_contract=PASS")
PY

printf 'R25B_IMAGE_PREFLIGHT=PASS\n'
printf 'image=%s\n' "${IMAGE}"
printf 'stability_label=%s\n' "${stability}"
printf 'r25_label=%s\n' "${r25}"
printf 'model_restart=NO\n'
printf 'managed_service_mutation=NO\n'
printf 'persistent_vm_tuning=NO\n'
