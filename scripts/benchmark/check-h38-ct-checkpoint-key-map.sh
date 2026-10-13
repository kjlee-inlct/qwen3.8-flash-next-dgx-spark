#!/usr/bin/env bash
# CPU-only, read-only H38 CT checkpoint INDEX KEY inventory (not tensor headers).
# Reuses qualified shard/index guard, does not read tensor headers or payloads.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"
IMAGE_ID="sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc"
TARGET_SHA="${H38_CKPT_CT_KEY_MAP_TARGET_SHA:-}"
MODEL_DIR="${H38_CKPT_CT_KEY_MAP_MODEL_DIR:-}"
INSPECTOR="${ROOT}/scripts/benchmark/inspect-h38-ct-checkpoint-key-map.py"
ORDER_INSPECTOR="${ROOT}/scripts/benchmark/inspect-h38-checkpoint-metadata-order.py"

fail() {
  printf 'H38_CKPT_CT_KEY_MAP_PREFLIGHT=INVALID reason=%s\n' "$*" >&2
  exit 2
}

[[ "$#" == 0 ]] || fail 'unexpected_arguments'
[[ "${TARGET_SHA}" =~ ^[0-9a-f]{40}$ ]] || fail 'exact_checkout_sha_required'
[[ -n "${MODEL_DIR}" && "${MODEL_DIR}" == /* ]] ||
  fail 'absolute_checkpoint_directory_required'
[[ -r "${INSPECTOR}" && -r "${ORDER_INSPECTOR}" ]] || fail 'source_inspectors_missing'
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
[[ "${before}" == "${IMAGE_ID}" ]] || fail 'image_id_mismatch'

printf 'H38_CKPT_CT_KEY_MAP_PREFLIGHT=BEGIN\n'
printf 'checkout_sha=%s\nimage_id=%s\n' "${TARGET_SHA}" "${before}"
printf 'scope=index_only_no_header_reread_no_tensor_data_no_gpu_no_model\n'
printf 'ephemeral_tmpfs=/tmp:64m:noexec:nosuid:nodev:mode1777\n'
# The original source-only attempt had no writable tempfile location because
# --read-only + UID 65534 rendered image /tmp unusable. Supply only a capped,
# container-private /tmp tmpfs; keep checkpoint bind and rootfs read-only.
# Access denied to an unprivileged inspector is INVALID; do not retry as root.
if docker run \
  --rm --pull never --runtime runc --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 1g --memory-swap 1g --cpus 1 \
  --user 65534:65534 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777 \
  --env TMPDIR=/tmp \
  --mount "type=bind,src=${MODEL_DIR},dst=/opt/checkpoint,readonly" \
  --mount "type=bind,src=${INSPECTOR},dst=/opt/h38-ct-key-map.py,readonly" \
  --mount "type=bind,src=${ORDER_INSPECTOR},dst=/opt/inspect-h38-checkpoint-metadata-order.py,readonly" \
  --entrypoint python3 "${IMAGE}" \
  -B /opt/h38-ct-key-map.py --model-dir /opt/checkpoint; then
  inspect_rc=0
else
  inspect_rc=$?
fi

after="$(docker image inspect --format '{{.Id}}' "${IMAGE}")"
[[ "${before}" == "${after}" ]] || fail 'image_identity_changed'
printf 'image_identity_unchanged=YES\n'
if [[ "${inspect_rc}" -eq 3 ]]; then
  # The analyzer completed its metadata output and deliberately
  # rejected the CT index-key schema gate; NOT a preflight INVALID.
  printf 'H38_CKPT_CT_KEY_MAP_PREFLIGHT=KEY_SCHEMA_FAIL\n'
  exit 3
fi
[[ "${inspect_rc}" -eq 0 ]] ||
  fail "checkpoint_key_map_inspector_invalid_rc_${inspect_rc}"
printf 'tensor_payload_read=NO\nheaders_reread=NO\n'
printf 'model_or_gpu_load=NO\n'
printf 'managed_service_mutation=NO\n'
printf 'monitor_protection_changed=NO\n'
printf 'meta_w13_patch_implemented=NO\n'
printf 'H38_CKPT_CT_KEY_MAP_PREFLIGHT=PASS_BASE_KEY_SCHEMA_ONLY\n'
