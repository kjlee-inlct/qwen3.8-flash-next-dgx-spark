#!/usr/bin/env bash
# Inspect the already-installed H38 loader source, never model/checkpoint data.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"
IMAGE_ID="sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc"
TARGET="${H38_LOADER_SOURCE_TARGET_SHA:-}"
INSPECTOR="${ROOT}/scripts/benchmark/inspect-h38-installed-loader-source.py"

fail() {
  printf 'H38_LOADER_SOURCE_PREFLIGHT=INVALID reason=%s\n' "$*" >&2
  exit 2
}

[[ "$#" == 0 ]] || fail 'unexpected_arguments'
[[ "${TARGET}" =~ ^[0-9a-f]{40}$ ]] || fail 'exact_checkout_sha_required'
[[ -r "${INSPECTOR}" ]] || fail 'inspector_missing'
command -v git >/dev/null 2>&1 || fail 'git_missing'
command -v docker >/dev/null 2>&1 || fail 'docker_missing'
[[ "$(git -C "${ROOT}" rev-parse HEAD)" == "${TARGET}" ]] ||
  fail 'checkout_sha_mismatch'
[[ -z "$(git -C "${ROOT}" status --porcelain=v1 --untracked-files=all)" ]] ||
  fail 'dirty_checkout'

docker image inspect "${IMAGE}" >/dev/null 2>&1 || fail 'image_missing'
before="$(docker image inspect --format '{{.Id}}' "${IMAGE}")"
[[ "${before}" == "${IMAGE_ID}" ]] || fail 'installed_image_id_mismatch'

image_label() {
  docker image inspect --format "{{ index .Config.Labels \"$2\" }}" "$1" 2>/dev/null
}
[[ "$(image_label "${IMAGE}" qwen38.h11)" == 'compressed-tensors-packed-modelweight-v1' ]] ||
  fail 'H11_lineage_mismatch'
[[ "$(image_label "${IMAGE}" qwen38.h12)" == 'compressed-tensors-postload-preserve-modelweight-v1' ]] ||
  fail 'H12_lineage_mismatch'
[[ "$(image_label "${IMAGE}" qwen38.h38scope)" == 'decoder-v1' ]] ||
  fail 'H38_lineage_mismatch'

printf 'H38_LOADER_SOURCE_PREFLIGHT=BEGIN\n'
printf 'repository_sha=%s\nimage=%s\nimage_id=%s\n' "${TARGET}" "${IMAGE}" "${before}"
printf 'execution=cpu_only_no_checkpoint_mount_no_gpu_no_network\n'
printf 'private_tmpfs=/tmp:32m:rw:noexec:nosuid:nodev\n'

docker run \
  --rm --pull never --runtime runc --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 512m --memory-swap 512m --cpus 1 \
  --user 65534:65534 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=32m,mode=1777 \
  --env TMPDIR=/tmp \
  --mount "type=bind,src=${INSPECTOR},dst=/opt/h38-installed-loader-source.py,readonly" \
  --entrypoint python3 "${IMAGE}" \
  -B /opt/h38-installed-loader-source.py ||
  fail 'installed_loader_source_contract_invalid'

after="$(docker image inspect --format '{{.Id}}' "${IMAGE}")"
[[ "${before}" == "${after}" ]] || fail 'installed_image_id_changed'
printf 'image_identity_unchanged=YES\n'
printf 'model_checkpoint_payload_read=NO\n'
printf 'gpu_or_model_load=NO\n'
printf 'managed_service_mutation=NO\n'
printf 'host_protection_changed=NO\n'
printf 'H38_LOADER_SOURCE_PREFLIGHT=PASS\n'
