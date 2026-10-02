#!/usr/bin/env bash
# Read-only preflight for the blocked Hybrid -> mazinb managed profile-switch leg.
#
# This helper performs no lifecycle mutation and starts/stops no container.
# It is safe to run while the strict R9 host-stability gate remains in force.

set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
INSTALL_STATE="${QWEN38_STATE_FILE:-${STATE_HOME}/install.env}"
STATE_PARSER="${ROOT}/scripts/lib/state_file.py"
MODEL_PROFILES="${ROOT}/scripts/model-profiles.sh"
UPDATE_TRANSITION="${ROOT}/scripts/update-transition.sh"
RUNTIME_TRANSITION="${ROOT}/scripts/runtime-transition.sh"
PROFILE_SWITCH="${ROOT}/scripts/profile-switch-transition.sh"
EXPECTED_FROM_PROFILE="${EXPECTED_FROM_PROFILE:-orcarouter-hybrid}"
TARGET_PROFILE="mazinb"

fail() {
    printf 'MAZINB_PREFLIGHT_ERROR: %s\n' "$*" >&2
    exit 2
}

require_file() {
    [[ -f "$1" && ! -L "$1" ]] || fail "missing or unsafe file: $1"
}

require_idle_line() {
    local label="$1" expected="$2" output="$3"
    printf '%s\n' "$output"
    grep -Fxq "$expected" <<<"$output" ||
        fail "$label is not idle (expected: $expected)"
}

for path in \
    "$STATE_PARSER" \
    "$MODEL_PROFILES" \
    "$UPDATE_TRANSITION" \
    "$RUNTIME_TRANSITION" \
    "$PROFILE_SWITCH"; do
    require_file "$path"
done
require_file "$INSTALL_STATE"

printf '=== lifecycle state ===\n'
update_status="$(bash "$UPDATE_TRANSITION" status)"
runtime_status="$(bash "$RUNTIME_TRANSITION" status)"
profile_status="$(bash "$PROFILE_SWITCH" status)"
require_idle_line update 'UPDATE_STATE=idle' "$update_status"
require_idle_line runtime 'TRANSACTION_STATE=idle' "$runtime_status"
require_idle_line profile-switch 'PROFILE_SWITCH_STATE=idle' "$profile_status"

printf '\n=== live install manifest ===\n'
parsed="$(mktemp)"
trap 'rm -f -- "$parsed"' EXIT
python3 "$STATE_PARSER" install-maintenance "$INSTALL_STATE" >"$parsed" ||
    fail 'installation manifest failed strict maintenance parsing'

CURRENT_PROFILE=""
CURRENT_PHASE=""
CURRENT_MODEL_DIR=""
CURRENT_IMAGE=""
CURRENT_SERVED_NAME=""
CURRENT_CONTAINER=""
while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "$key" in
        MODEL_PROFILE) CURRENT_PROFILE="$value" ;;
        PHASE) CURRENT_PHASE="$value" ;;
        MODEL_DIR) CURRENT_MODEL_DIR="$value" ;;
        VLLM_IMAGE) CURRENT_IMAGE="$value" ;;
        SERVED_NAME) CURRENT_SERVED_NAME="$value" ;;
        CONTAINER_NAME) CURRENT_CONTAINER="$value" ;;
    esac
done <"$parsed"

printf 'current_profile=%s\n' "$CURRENT_PROFILE"
printf 'current_phase=%s\n' "$CURRENT_PHASE"
printf 'current_model_dir=%s\n' "$CURRENT_MODEL_DIR"
printf 'current_image=%s\n' "$CURRENT_IMAGE"
printf 'current_served_name=%s\n' "$CURRENT_SERVED_NAME"
printf 'current_container=%s\n' "$CURRENT_CONTAINER"

[[ "$CURRENT_PROFILE" == "$EXPECTED_FROM_PROFILE" ]] ||
    fail "live profile is $CURRENT_PROFILE; expected $EXPECTED_FROM_PROFILE for the blocked Hybrid -> mazinb leg"
[[ "$CURRENT_PHASE" == complete ]] ||
    fail "live install phase is $CURRENT_PHASE; expected complete"
[[ -d "$CURRENT_MODEL_DIR" ]] ||
    fail "live model directory is missing: $CURRENT_MODEL_DIR"

if [[ -n "$CURRENT_CONTAINER" ]]; then
    docker inspect "$CURRENT_CONTAINER" >/dev/null 2>&1 ||
        fail "live container is not inspectable: $CURRENT_CONTAINER"
    running="$(docker inspect --format '{{.State.Running}}' "$CURRENT_CONTAINER" 2>/dev/null || true)"
    printf 'current_container_running=%s\n' "$running"
fi

printf '\n=== mazinb target profile ===\n'
# Compatibility source path; canonical registry is model/model-profiles.sh.
# shellcheck source=scripts/model-profiles.sh
source "$MODEL_PROFILES"
load_model_profile "$TARGET_PROFILE" || fail 'failed to load mazinb profile definition'

printf 'target_profile=%s\n' "$TARGET_PROFILE"
printf 'target_status=%s\n' "$PROFILE_STATUS"
printf 'target_installable=%s\n' "$PROFILE_INSTALLABLE"
printf 'target_repo=%s\n' "$PROFILE_REPO"
printf 'target_revision=%s\n' "$PROFILE_REVISION"
printf 'target_model_dir=%s\n' "$PROFILE_MODEL_DIR"
printf 'target_image=%s\n' "$PROFILE_IMAGE"
printf 'target_served_name=%s\n' "$PROFILE_SERVED_NAME"

[[ "$PROFILE_INSTALLABLE" == 1 ]] || fail 'mazinb profile is not installable'
[[ -d "$PROFILE_MODEL_DIR" ]] || fail "mazinb checkpoint missing: $PROFILE_MODEL_DIR"
[[ -f "$PROFILE_MODEL_DIR/config.json" ]] || fail 'mazinb config.json missing'

if [[ ! -f "$PROFILE_MODEL_DIR/model.safetensors.index.json" ]]; then
    shopt -s nullglob
    shards=("$PROFILE_MODEL_DIR"/*.safetensors)
    shopt -u nullglob
    ((${#shards[@]} > 0)) || fail 'mazinb checkpoint has no safetensors index or shard files'
fi

docker image inspect "$PROFILE_IMAGE" >/dev/null 2>&1 ||
    fail "mazinb runtime image missing: $PROFILE_IMAGE"

printf '\n=== stale profile-switch artifacts ===\n'
backup="${INSTALL_STATE}.profile-switch-backup"
candidate="${INSTALL_STATE}.profile-switch-candidate"
for path in "$backup" "$candidate"; do
    if [[ -e "$path" || -L "$path" ]]; then
        printf 'STALE %s\n' "$path"
        fail 'stale profile-switch artifact exists; recover before any switch'
    fi
    printf 'ABSENT %s\n' "$path"
done

printf '\n=== capacity snapshot ===\n'
df -h "$(dirname -- "$PROFILE_MODEL_DIR")" | tail -n 1
free -h | sed -n '1,3p'

printf '\nMAZINB_SWITCH_PREFLIGHT=PASS\n'
printf 'from_profile=%s\n' "$CURRENT_PROFILE"
printf 'to_profile=%s\n' "$TARGET_PROFILE"
printf 'mutation_performed=NO\n'
printf 'strict_r9_gate=STILL_BLOCKS_ACTIVATION\n'
