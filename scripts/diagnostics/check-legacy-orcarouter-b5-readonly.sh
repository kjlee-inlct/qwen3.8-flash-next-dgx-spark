#!/usr/bin/env bash
# Exact-identity READ-ONLY legacy OrcaRouter B5 prestart check on one DGX.
# No installation, runtime start, service mutation or rollback is allowed.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TARGET="${QWEN38_B5_TARGET_SHA:-}"
RELEASE="${QWEN38_B5_RELEASE_SHA:-}"
PREVIOUS="${QWEN38_B5_PREVIOUS_CONTAINER_ID:-}"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
CURRENT="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark/current"
MANIFEST="$STATE/install.env"
OWNERSHIP="$STATE/asset-ownership.json"
fail() { printf 'B5_READONLY=INVALID reason=%s\n' "$*" >&2; exit 2; }
[[ "$#" == 0 ]] || fail unexpected_args
[[ "$TARGET" =~ ^[0-9a-f]{40}$ ]] || fail exact_sha_required
[[ "$RELEASE" =~ ^[0-9a-f]{40}$ ]] || fail release_sha_required
[[ "$PREVIOUS" =~ ^[0-9a-f]{64}$ ]] || fail previous_container_id_required
for bin in git docker systemctl readlink sha256sum awk swapon df grep; do
  command -v "$bin" >/dev/null 2>&1 || fail "missing_command:$bin"
done
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$TARGET" ]] || fail checkout_sha_mismatch
[[ -z "$(git -C "$ROOT" status --porcelain=v1 --untracked-files=all)" ]] ||
  fail dirty_checkout
[[ -f "$MANIFEST" && ! -L "$MANIFEST" ]] || fail manifest_not_regular
[[ ! -L "$OWNERSHIP" ]] || fail ownership_is_symlink
[[ -L "$CURRENT" ]] || fail current_release_not_symlink

fingerprint() {
  if [[ -f "$1" ]]; then sha256sum -- "$1" | awk '{print $1}'
  elif [[ -e "$1" ]]; then printf NOT_REGULAR
  else printf ABSENT
  fi
}
manifest_before="$(fingerprint "$MANIFEST")"
ownership_before="$(fingerprint "$OWNERSHIP")"
release_before="$(readlink -f -- "$CURRENT")"

printf 'B5_READONLY=BEGIN\n'
printf 'SOURCE_SHA=%s\nEXPECTED_RELEASE=%s\nEXPECTED_CONTAINER=%s\n' \
  "$TARGET" "$RELEASE" "$PREVIOUS"
printf 'HOST_MUTATION=NO\nMODEL_START=NO\n'
bad=0
require_equals() {
  if [[ "$2" == "$3" ]]; then
    printf 'B5_CHECK=%s PASS\n' "$1"
  else
    printf 'B5_CHECK=%s FAIL expected=%s actual=%s\n' "$1" "$2" "$3"
    bad=1
  fi
}

require_equals installed_release \
  "${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark/releases/$RELEASE" "$release_before"
id="$(docker inspect -f '{{.Id}}' qwen38-flash-next)" || fail docker_inspect_failed
state="$(docker inspect -f '{{.State.Status}}' qwen38-flash-next)" ||
  fail docker_state_failed
image="$(docker inspect -f '{{.Config.Image}}' qwen38-flash-next)" ||
  fail docker_image_failed
oom="$(docker inspect -f '{{.State.OOMKilled}}' qwen38-flash-next)" ||
  fail docker_oom_failed
require_equals prior_docker_id "$PREVIOUS" "$id"
require_equals prior_docker_stopped exited "$state"
require_equals prior_docker_image vllm-skinny-tp1:v1 "$image"
require_equals prior_docker_not_oom false "$oom"
if docker inspect qwen38-flash-next.rollback >/dev/null 2>&1; then
  require_equals rollback_object_absent absent present
else
  require_equals rollback_object_absent absent absent
fi
active="$(systemctl show qwen38-flash-next.service -p ActiveState --value --no-pager)" ||
  fail systemctl_query_failed
require_equals managed_unit_stopped inactive "$active"
printf 'SYSTEMD_METADATA_BEGIN\n'
systemctl show qwen38-flash-next.service --no-pager \
  -p LoadState,ActiveState,SubState,Result,ExecStart,ExecStop,Restart ||
  fail systemd_unit_metadata_failed
printf 'SYSTEMD_METADATA_END\n'
if grep -Fxq 'PHASE=complete' "$MANIFEST"; then
  printf 'B5_CHECK=complete_manifest PASS\n'
else
  printf 'B5_CHECK=complete_manifest FAIL\n'
  bad=1
fi
for setting in MONITOR_PROTECT=1 MONITOR_ENABLED=1; do
  if grep -Fxq "$setting" "$MANIFEST"; then
    printf 'B5_CHECK=%s PASS\n' "$setting"
  else
    printf 'B5_CHECK=%s FAIL\n' "$setting"
    bad=1
  fi
done
if swapon --show=NAME --noheadings | awk '{$1=$1;print}' |
    grep -Fxq /swap-ple.img; then
  printf 'B5_CHECK=dedicated_swap_active PASS\n'
else
  printf 'B5_CHECK=dedicated_swap_active FAIL\n'
  bad=1
fi
printf 'MEMORY_POINT_IN_TIME_BEGIN\n'
awk '/^(MemAvailable|MemFree|SwapFree|CmaFree):/ {print}' /proc/meminfo
printf 'MEMORY_POINT_IN_TIME_END\n'
swapon --show
df -h -- "$HOME"

require_equals manifest_unmodified "$manifest_before" "$(fingerprint "$MANIFEST")"
require_equals ownership_unmodified "$ownership_before" "$(fingerprint "$OWNERSHIP")"
require_equals release_unmodified "$release_before" "$(readlink -f -- "$CURRENT")"
require_equals source_unmodified "$TARGET" "$(git -C "$ROOT" rev-parse HEAD)"
[[ -z "$(git -C "$ROOT" status --porcelain=v1 --untracked-files=all)" ]] ||
  fail checkout_dirty_after
if [[ "$bad" != 0 ]]; then
  printf 'B5_READONLY=PARTIAL_CHECK_FAILURE\nM1_LIVE=NOT_AUTHORIZED\n'
  exit 3
fi
printf 'B5_READONLY=COLLECTED_READ_ONLY\n'
printf 'M1_LIVE=BLOCKED_PENDING_CONTAINER_ID_DECISION_AND_ROLLBACK_PLAN\n'
printf 'OLD_DOCKER_ID_SURVIVAL=NOT_GUARANTEED_BY_INSTALLED_SERVICE_RUNNER\n'
printf 'H38_LIVE=BLOCKED\n'
