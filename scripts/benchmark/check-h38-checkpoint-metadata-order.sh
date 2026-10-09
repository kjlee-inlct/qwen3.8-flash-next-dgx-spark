#!/usr/bin/env bash
# CPU-only, read-only inspection of actual H38 OrcaRouter checkpoint headers.
# Mounts checkpoint readonly; does not load or inspect tensor payloads.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"
IMAGE_ID="sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc"
TARGET_SHA="${H38_CKPT_METADATA_TARGET_SHA:-}"
MODEL_DIR="${H38_CKPT_METADATA_MODEL_DIR:-}"
INSPECTOR="${ROOT}/scripts/benchmark/inspect-h38-checkpoint-metadata-order.py"

fail() {
  printf 'H38_CKPT_METADATA_PREFLIGHT=INVALID reason=%s\n' "$*" >&2
  exit 2
}

[[ "$#" == 0 ]] || fail 'unexpected_arguments'
[[ "${TARGET_SHA}" =~ ^[0-9a-f]{40}$ ]] || fail 'missing_exact_checkout_sha'
[[ -n "${MODEL_DIR}" && "${MODEL_DIR}" == /* ]] ||
  fail 'absolute_checkpoint_directory_required'
[[ -r "${INSPECTOR}" ]] || fail 'source_inspector_missing'
command -v docker >/dev/null 2>&1 || fail 'docker_missing'
command -v git >/dev/null 2>&1 || fail 'git_missing'
[[ "$(git -C "${ROOT}" rev-parse HEAD)" == "${TARGET_SHA}" ]] ||
  fail 'checkout_sha_mismatch'
[[ -z "$(git -C "${ROOT}" status --porcelain=v1 --untracked-files=all)" ]] ||
  fail 'dirty_checkout'
MODEL_DIR="$(realpath -e -- "${MODEL_DIR}")" || fail 'checkpoint_path_missing'
[[ -d "${MODEL_DIR}" && -f "${MODEL_DIR}/model.safetensors.index.json" ]] ||
  fail 'checkpoint_index_missing'
[[ "${MODEL_DIR}" != '/' ]] || fail 'root_mount_forbidden'
docker image inspect "${IMAGE}" >/dev/null 2>&1 || fail 'image_missing'
before="$(docker image inspect --format '{{.Id}}' "${IMAGE}")"
[[ "${before}" == "${IMAGE_ID}" ]] || fail 'H38_image_id_mismatch'

printf 'H38_CKPT_METADATA_PREFLIGHT=BEGIN\n'
printf 'checkout_sha=%s\nimage_id=%s\n' "${TARGET_SHA}" "${before}"
printf 'scope=read_only_header_and_safe_open_keys_no_tensor_data_no_gpu\n'
printf 'ephemeral_tmpfs=/tmp:64m:noexec:nosuid:nodev:mode1777\n'
# The original source-only attempt had no writable tempfile location because
# --read-only + UID 65534 rendered image /tmp unusable. Supply only a capped,
# container-private /tmp tmpfs; keep checkpoint bind and rootfs read-only.
# Access denied to an unprivileged inspector is INVALID; do not retry as root.
docker run \
  --rm --pull never --runtime runc --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 1g --memory-swap 1g --cpus 1 \
  --user 65534:65534 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777 \
  --env TMPDIR=/tmp \
  --mount "type=bind,src=${MODEL_DIR},dst=/opt/checkpoint,readonly" \
  --mount "type=bind,src=${INSPECTOR},dst=/opt/h38-checkpoint-order.py,readonly" \
  --entrypoint python3 "${IMAGE}" \
  -B /opt/h38-checkpoint-order.py --model-dir /opt/checkpoint ||
  fail 'checkpoint_metadata_order_invalid'

after="$(docker image inspect --format '{{.Id}}' "${IMAGE}")"
[[ "${before}" == "${after}" ]] || fail 'image_identity_changed'
printf 'image_identity_unchanged=YES\n'
printf 'tensor_payload_read=NO\n'
printf 'model_or_gpu_load=NO\n'
printf 'managed_service_mutation=NO\n'
printf 'monitor_protection_changed=NO\n'
printf 'meta_w13_patch_implemented=NO\n'
printf 'H38_CKPT_METADATA_PREFLIGHT=PASS\n'
