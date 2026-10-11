#!/usr/bin/env bash
# Read-only H38 CT meta-deferral prerequisite source check; NOT a mitigation run.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"
INSPECTOR="${ROOT}/scripts/benchmark/inspect-h38-ct-meta-prerequisites.py"
EXPECTED_SHA="${H38_CT_META_SOURCE_TARGET_SHA:-}"

fail() {
  printf 'H38_CT_META_SOURCE_PREFLIGHT=INVALID reason=%s\n' "$*" >&2
  exit 2
}

[[ "$#" == 0 ]] || fail 'unexpected_arguments'
[[ "${EXPECTED_SHA}" =~ ^[0-9a-f]{40}$ ]] || fail 'exact_sha_required'
[[ -r "${INSPECTOR}" ]] || fail 'inspector_missing'
command -v docker >/dev/null || fail 'docker_missing'
command -v git >/dev/null || fail 'git_missing'
[[ "$(git -C "${ROOT}" rev-parse HEAD)" == "${EXPECTED_SHA}" ]] ||
  fail 'checkout_sha_mismatch'
[[ -z "$(git -C "${ROOT}" status --porcelain=v1 --untracked-files=all)" ]] ||
  fail 'checkout_dirty'
docker image inspect "${IMAGE}" >/dev/null 2>&1 || fail 'image_missing'

image_label() {
  docker image inspect --format "{{ index .Config.Labels \"$2\" }}" "$1" 2>/dev/null
}
[[ "$(image_label "${IMAGE}" qwen38.h11)" == 'compressed-tensors-packed-modelweight-v1' ]] ||
  fail 'h11_label_mismatch'
[[ "$(image_label "${IMAGE}" qwen38.h12)" == 'compressed-tensors-postload-preserve-modelweight-v1' ]] ||
  fail 'h12_label_mismatch'
[[ "$(image_label "${IMAGE}" qwen38.h38scope)" == 'decoder-v1' ]] ||
  fail 'h38_label_mismatch'

before="$(docker image inspect --format '{{.Id}}' "${IMAGE}")"
printf 'H38_CT_META_SOURCE_PREFLIGHT=BEGIN\n'
printf 'repository_sha=%s\nimage=%s\nimage_id=%s\n' \
  "${EXPECTED_SHA}" "${IMAGE}" "${before}"
printf 'semantics=cpu_only_installed_source_prerequisites_not_model_or_mitigation\n'

docker run \
  --rm --pull never --runtime runc --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 512m --memory-swap 512m --cpus 1 \
  --user 65534:65534 \
  --mount "type=bind,src=${INSPECTOR},dst=/opt/h38-ct-meta-prerequisites.py,readonly" \
  --entrypoint python3 "${IMAGE}" \
  -B /opt/h38-ct-meta-prerequisites.py ||
  fail 'source_contract_invalid'

after="$(docker image inspect --format '{{.Id}}' "${IMAGE}")"
[[ "${before}" == "${after}" ]] || fail 'image_identity_changed'
printf 'image_identity_unchanged=YES\n'
printf 'managed_service_mutation=NO\n'
printf 'gpu_or_model_load=NO\n'
printf 'monitor_protection_changed=NO\n'
printf 'ct_meta_w13_patch_implemented=NO\n'
printf 'H38_CT_META_SOURCE_PREFLIGHT=PASS\n'
