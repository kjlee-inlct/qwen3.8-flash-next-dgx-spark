#!/usr/bin/env bash
# CPU-only, no-network static inspection of the exact installed H38 Docker image.
# Does not start a model, access a GPU, change managed lifecycle or alter VM.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"
TARGET_SHA="${H38_EXACT_SOURCE_TARGET_SHA:-}"
INSPECTOR="${ROOT}/scripts/benchmark/inspect-h38-exact-image-source.py"
R32="${ROOT}/scripts/benchmark/inspect-orcarouter-r32-precreate-source-contract.py"

usage() {
  cat <<'EOF'
Usage: H38_EXACT_SOURCE_TARGET_SHA=<exact 40-character commit SHA> \
  bash scripts/benchmark/check-h38-exact-image-source.sh

CPU-only, network-isolated static AST inspection of the exact H38 image
using an ephemeral unprivileged runc container. No vLLM model/GPU load,
no managed service operations, no image pull/build, no VM tuning.
The read-only source check does not validate RM mitigation.
EOF
}

fail() {
  printf 'H38_EXACT_IMAGE_SOURCE_PREFLIGHT=INVALID reason=%s\n' "$*" >&2
  exit 2
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
[[ "$#" == 0 ]] || { usage >&2; exit 2; }
[[ "${TARGET_SHA}" =~ ^[0-9a-f]{40}$ ]] || fail 'exact_target_sha_missing_or_invalid'
[[ -f "${INSPECTOR}" && -f "${R32}" ]] || fail 'local_source_inspectors_missing'
command -v docker >/dev/null 2>&1 || fail 'docker_missing'
command -v git >/dev/null 2>&1 || fail 'git_missing'

actual="$(git -C "${ROOT}" rev-parse HEAD)"
[[ "${actual}" == "${TARGET_SHA}" ]] || fail "checkout_sha_mismatch expected=${TARGET_SHA} actual=${actual}"
[[ -z "$(git -C "${ROOT}" status --porcelain=v1 --untracked-files=all)" ]] ||
  fail 'checkout_dirty'
docker image inspect "${IMAGE}" >/dev/null 2>&1 || fail 'exact_h38_image_missing'

label() {
  docker image inspect --format "{{ index .Config.Labels \"$2\" }}" "$1" 2>/dev/null
}
[[ "$(label "${IMAGE}" qwen38.h11)" == 'compressed-tensors-packed-modelweight-v1' ]] ||
  fail 'h11_inherited_label_mismatch'
[[ "$(label "${IMAGE}" qwen38.h12)" == 'compressed-tensors-postload-preserve-modelweight-v1' ]] ||
  fail 'h12_inherited_label_mismatch'
[[ "$(label "${IMAGE}" qwen38.h38scope)" == 'decoder-v1' ]] ||
  fail 'h38_decoder_scope_label_mismatch'

before="$(docker image inspect --format '{{.Id}}' "${IMAGE}")"
printf 'H38_EXACT_IMAGE_SOURCE_PREFLIGHT=BEGIN\n'
printf 'repository_sha=%s\n' "${TARGET_SHA}"
printf 'image=%s\n' "${IMAGE}"
printf 'image_id=%s\n' "${before}"
printf 'exec_context=ephemeral_unprivileged_runc_cpu_only_network_none\n'

# --runtime=runc prevents the NVIDIA runtime from injecting GPU devices,
# --network none and --pull never prevent online dependencies; the files and
# image rootfs are read-only. Docker only creates a short-lived inspect
# container; it never launches the model/server.
docker run \
  --rm --pull never \
  --runtime runc --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 512m --memory-swap 512m --cpus 1 \
  --user 65534:65534 \
  --mount "type=bind,src=${INSPECTOR},dst=/opt/h38-source-inspector.py,readonly" \
  --mount "type=bind,src=${R32},dst=/opt/r32-source-inspector.py,readonly" \
  --entrypoint python3 "${IMAGE}" \
  -B /opt/h38-source-inspector.py --r32-script /opt/r32-source-inspector.py ||
  fail 'exact_image_source_contract_rejected'

after="$(docker image inspect --format '{{.Id}}' "${IMAGE}")"
[[ "${after}" == "${before}" ]] || fail 'image_identity_changed_during_static_check'
printf 'image_identity_unchanged=YES\n'
printf 'managed_runtime_mutation=NO\n'
printf 'gpu_or_model_load=NO\n'
printf 'protection_changed=NO\n'
printf 'host_stability_qualified=NO\n'
printf 'H38_EXACT_IMAGE_SOURCE_PREFLIGHT=PASS\n'
