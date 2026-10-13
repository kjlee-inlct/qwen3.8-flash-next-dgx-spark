#!/usr/bin/env bash
# H38 CT expert/shard destination source branch audit only; no torch/GPU/model.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TARGET="${H38_CT_EXPERT_DESTINATION_TARGET_SHA:-}"
IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"
IMAGE_ID="sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc"
INSPECTOR="${ROOT}/scripts/benchmark/inspect-h38-ct-expert-destination-source.py"

fail() {
  printf 'H38_CT_EXPERT_DESTINATION_PREFLIGHT=INVALID reason=%s\n' "$*" >&2
  exit 2
}

[[ "$#" == 0 ]] || fail 'unexpected_arguments'
[[ "${TARGET}" =~ ^[0-9a-f]{40}$ ]] || fail 'exact_checkout_sha_required'
command -v git >/dev/null 2>&1 || fail 'git_missing'
command -v docker >/dev/null 2>&1 || fail 'docker_missing'
[[ -r "${INSPECTOR}" ]] || fail 'inspector_missing'
[[ "$(git -C "${ROOT}" rev-parse HEAD)" == "${TARGET}" ]] || fail 'checkout_sha_mismatch'
[[ -z "$(git -C "${ROOT}" status --porcelain=v1 --untracked-files=all)" ]] || fail 'dirty_checkout'
docker image inspect "${IMAGE}" >/dev/null 2>&1 || fail 'image_missing'
before="$(docker image inspect --format '{{.Id}}' "${IMAGE}")"
[[ "${before}" == "${IMAGE_ID}" ]] || fail 'image_id_mismatch'

image_label() {
  docker image inspect --format "{{ index .Config.Labels \"$2\" }}" "$1" 2>/dev/null
}
[[ "$(image_label "${IMAGE}" qwen38.h11)" == "compressed-tensors-packed-modelweight-v1" ]] ||
  fail 'H11_label_mismatch'
[[ "$(image_label "${IMAGE}" qwen38.h12)" == "compressed-tensors-postload-preserve-modelweight-v1" ]] ||
  fail 'H12_label_mismatch'
[[ "$(image_label "${IMAGE}" qwen38.h38scope)" == "decoder-v1" ]] ||
  fail 'H38_label_mismatch'

printf 'H38_CT_EXPERT_DESTINATION_PREFLIGHT=BEGIN\n'
printf 'checkout_sha=%s\nimage_id=%s\n' "${TARGET}" "${before}"
printf 'scope=exact_installed_source_only_no_checkpoint_no_gpu_no_model_no_network\n'

if docker run \
    --rm --pull never --runtime runc --network none --read-only \
    --cap-drop ALL --security-opt no-new-privileges \
    --pids-limit 64 --memory 512m --memory-swap 512m --cpus 1 \
    --user 65534:65534 \
    --tmpfs /tmp:rw,noexec,nosuid,nodev,size=32m \
    --mount "type=bind,src=${INSPECTOR},dst=/opt/h38-ct-expert-destination.py,readonly" \
    --entrypoint python3 "${IMAGE}" -B /opt/h38-ct-expert-destination.py; then
  :
else
  fail 'installed_expert_destination_source_contract_invalid'
fi

after="$(docker image inspect --format '{{.Id}}' "${IMAGE}")"
[[ "${before}" == "${after}" ]] || fail 'image_identity_changed'
printf 'image_identity_unchanged=YES\n'
printf 'gpu_or_model_load=NO\ncheckpoint_payload_read=NO\n'
printf 'managed_service_mutation=NO\nhost_protection_changed=NO\n'
printf 'ct_meta_patch_implemented=NO\n'
printf 'H38_CT_EXPERT_DESTINATION_PREFLIGHT=PASS_SOURCE_BRANCHES_ONLY\n'
