#!/usr/bin/env bash
# Controlled mazinb KV-cache host-stability A/B experiment.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
SERVE="${ROOT}/scripts/serve.sh"
STATE_PARSER="${ROOT}/scripts/lib/state_file.py"
MODEL_PROFILES="${ROOT}/scripts/model-profiles.sh"
UPDATE_TRANSITION="${ROOT}/scripts/update-transition.sh"
RUNTIME_TRANSITION="${ROOT}/scripts/runtime-transition.sh"
PROFILE_SWITCH_TRANSITION="${ROOT}/scripts/profile-switch-transition.sh"
SERVICE="qwen38-flash-next.service"
CANONICAL_CONTAINER="qwen38-flash-next"
CANONICAL_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
INSTALL_STATE="${QWEN38_STATE_FILE:-${CANONICAL_STATE_HOME}/install.env}"
ACTION="${1:-plan}"
CASE_ID="${2:-}"
WAIT_SECONDS="${MAZINB_KV_WAIT_SECONDS:-1800}"
SOAK_SECONDS="${MAZINB_KV_SOAK_SECONDS:-180}"
POLL_SECONDS="${MAZINB_KV_POLL_SECONDS:-10}"
PORT="${MAZINB_KV_PORT:-8888}"

usage() {
    cat <<'USAGE'
Usage:
  bash scripts/runtime/mazinb-kv-ab.sh plan
  bash scripts/runtime/mazinb-kv-ab.sh preflight
  bash scripts/runtime/mazinb-kv-ab.sh run A|B
  bash scripts/runtime/mazinb-kv-ab.sh status
  bash scripts/runtime/mazinb-kv-ab.sh evidence A|B
  bash scripts/runtime/mazinb-kv-ab.sh cleanup [A|B]

Matrix:
  A  KV_MEM=25769803776  (24 GiB, current mazinb default/control)
  B  KV_MEM=17179869184  (16 GiB, reduced-KV candidate)

Fixed runtime controls:
  MODEL_PROFILE=mazinb
  NSPEC=2
  MAXLEN=262144
  MAXSEQS=3
  PREFIX_CACHE=0
  INDEX_SHARE=0
  AUTOTUNE=0
  GPU_UTIL=0.80
  QSA_EXACT_TOPK=1
  RESTART_POLICY=no
  MONITOR_ENABLED=1
  MONITOR_PROTECT=1
  MONITOR_MIN_AVAILABLE_GIB=6
  MONITOR_MIN_FREE_GIB=2
  MONITOR_FREE_GATE_GIB=10
  MONITOR_MIN_SWAP_FREE_GIB=8
  MONITOR_CONSECUTIVE=5
  loopback-only API

Run B first. If B reaches READY, passes served-model validation, completes the
180 s soak, has no protected stop, and has no kernel NV_ERR_NO_MEMORY in the
case window, run A under the same helper to establish the controlled contrast.
If B reproduces the failure, A does not need to be rerun.
USAGE
}

fail() {
    printf 'MAZINB_KV_AB_ERROR: %s\n' "$*" >&2
    exit 2
}

case_values() {
    case "$1" in
        A|a)
            CASE_ID=A
            KV_MEM_VALUE=25769803776
            ;;
        B|b)
            CASE_ID=B
            KV_MEM_VALUE=17179869184
            ;;
        *)
            printf 'ERROR: case must be A or B\n' >&2
            return 2
            ;;
    esac
    CASE_LOWER="${CASE_ID,,}"
    CONTAINER_NAME="qwen38-mazinb-kv-${CASE_LOWER}"
    EXPERIMENT_XDG_STATE_HOME="${HOME}/.local/state/qwen38-mazinb-kv-${CASE_LOWER}"
    EXPERIMENT_STATE_DIR="${EXPERIMENT_XDG_STATE_HOME}/qwen38-spark"
    EXPERIMENT_ENV="${EXPERIMENT_STATE_DIR}/experiment.env"
    MONITOR_LOG="${EXPERIMENT_STATE_DIR}/monitor.log"
    RUNTIME_STOP_ENV="${EXPERIMENT_STATE_DIR}/runtime-stop.env"
}

require_file() {
    [[ -f "$1" && ! -L "$1" ]] || fail "missing or unsafe file: $1"
}

require_idle_line() {
    local label="$1" expected="$2" output="$3"
    grep -Fxq "$expected" <<<"$output" ||
        fail "$label is not idle (expected: $expected; got: $output)"
}

service_active() {
    command -v systemctl >/dev/null 2>&1 &&
        systemctl is-active --quiet "${SERVICE}" 2>/dev/null
}

container_running() {
    local name="$1"
    [[ "$(docker inspect --format '{{.State.Running}}' "$name" 2>/dev/null || true)" == true ]]
}

load_managed_mazinb() {
    require_file "$STATE_PARSER"
    require_file "$MODEL_PROFILES"
    require_file "$INSTALL_STATE"

    local parsed current_phase current_model_dir
    parsed="$(mktemp)"
    if ! python3 "$STATE_PARSER" install-maintenance "$INSTALL_STATE" >"$parsed"; then
        rm -f -- "$parsed"
        fail 'installation manifest failed strict maintenance parsing'
    fi

    current_phase=""
    current_model_dir=""
    while IFS= read -r -d '' key && IFS= read -r -d '' value; do
        case "$key" in
            PHASE) current_phase="$value" ;;
            MODEL_DIR) current_model_dir="$value" ;;
        esac
    done <"$parsed"

    [[ "$current_phase" == complete ]] || {
        rm -f -- "$parsed"
        fail "live install phase is $current_phase; expected complete"
    }
    [[ -n "$current_model_dir" && -d "$current_model_dir" ]] || {
        rm -f -- "$parsed"
        fail "live model directory is missing: $current_model_dir"
    }
    rm -f -- "$parsed"

    MANAGED_MODEL_ROOT="$(dirname -- "$(realpath -m -- "$current_model_dir")")"
    export QWEN38_MODEL_ROOT="$MANAGED_MODEL_ROOT"
    # shellcheck source=scripts/model-profiles.sh
    source "$MODEL_PROFILES"
    load_model_profile mazinb || fail 'failed to load mazinb profile definition'

    MAZINB_MODEL_DIR="$PROFILE_MODEL_DIR"
    MAZINB_IMAGE="$PROFILE_IMAGE"
    MAZINB_SERVED_NAME="$PROFILE_SERVED_NAME"
}

check_lifecycle_idle() {
    require_file "$UPDATE_TRANSITION"
    require_file "$RUNTIME_TRANSITION"
    require_file "$PROFILE_SWITCH_TRANSITION"
    require_idle_line update 'UPDATE_STATE=idle' "$(bash "$UPDATE_TRANSITION" status)"
    require_idle_line runtime 'TRANSACTION_STATE=idle' "$(bash "$RUNTIME_TRANSITION" status)"
    require_idle_line profile-switch 'PROFILE_SWITCH_STATE=idle' "$(bash "$PROFILE_SWITCH_TRANSITION" status)"
}

port_in_use() {
    python3 - "$PORT" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.2)
    raise SystemExit(0 if sock.connect_ex(("127.0.0.1", port)) == 0 else 1)
PY
}

preflight() {
    local failures=0
    printf 'mazinb KV A/B preflight\n'

    for cmd in docker python3 curl sudo; do
        if command -v "$cmd" >/dev/null 2>&1; then
            printf '  %-16s: ready\n' "$cmd"
        else
            printf '  %-16s: missing\n' "$cmd"
            failures=1
        fi
    done
    ((failures == 0)) || return 1

    check_lifecycle_idle
    load_managed_mazinb

    printf '  managed root    : %s\n' "$MANAGED_MODEL_ROOT"
    printf '  mazinb model    : %s\n' "$MAZINB_MODEL_DIR"
    printf '  runtime image   : %s\n' "$MAZINB_IMAGE"
    printf '  served name     : %s\n' "$MAZINB_SERVED_NAME"

    [[ -d "$MAZINB_MODEL_DIR" ]] || {
        printf '  checkpoint      : missing\n'
        failures=1
    }
    [[ -f "$MAZINB_MODEL_DIR/config.json" ]] || {
        printf '  config.json     : missing\n'
        failures=1
    }
    if docker image inspect "$MAZINB_IMAGE" >/dev/null 2>&1; then
        printf '  image           : ready\n'
    else
        printf '  image           : missing\n'
        failures=1
    fi

    if service_active; then
        printf '  managed service : ACTIVE (must remain stopped during A/B)\n'
        failures=1
    else
        printf '  managed service : inactive\n'
    fi
    if container_running "$CANONICAL_CONTAINER"; then
        printf '  canonical       : RUNNING (must remain stopped during A/B)\n'
        failures=1
    else
        printf '  canonical       : not running\n'
    fi
    if port_in_use; then
        printf '  port %s       : IN USE\n' "$PORT"
        failures=1
    else
        printf '  port %s       : free\n' "$PORT"
    fi

    if sudo -n true >/dev/null 2>&1; then
        printf '  kernel evidence : sudo credential ready\n'
    else
        printf '  kernel evidence : sudo credential unavailable; run sudo -v first\n'
        failures=1
    fi

    ((failures == 0)) || return 1
    printf 'MAZINB_KV_AB_PREFLIGHT=PASS\n'
}

read_started_at() {
    [[ -f "$EXPERIMENT_ENV" ]] || return 1
    sed -n 's/^STARTED_AT=//p' "$EXPERIMENT_ENV" | tail -n 1
}

kernel_signals() {
    local since="$1"
    sudo -n journalctl -k --since "$since" --no-pager 2>/dev/null |
        grep -E 'NVRM|NV_ERR|Out of memory|oom-killer|Killed process' || true
}

kernel_nv_err_present() {
    local since="$1"
    kernel_signals "$since" | grep -q 'NV_ERR_NO_MEMORY'
}

protected_stop_present() {
    [[ -f "$MONITOR_LOG" ]] && grep -q 'PROTECT stopping' "$MONITOR_LOG"
}

health_ready() {
    curl -fsS --max-time 3 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1
}

validate_served_model() {
    curl -fsS --max-time 5 "http://127.0.0.1:${PORT}/v1/models" |
        python3 -c 'import json, sys; expected=sys.argv[1]; payload=json.load(sys.stdin); ids=[item.get("id") for item in payload.get("data", [])]; sys.exit(0 if ids == [expected] else 1)' "$MAZINB_SERVED_NAME"
}

prepare_case_state() {
    mkdir -p "$EXPERIMENT_STATE_DIR"
    if [[ -f "${EXPERIMENT_STATE_DIR}/monitor.pid" ]]; then
        local old_pid
        old_pid="$(cat "${EXPERIMENT_STATE_DIR}/monitor.pid" 2>/dev/null || true)"
        if [[ "$old_pid" =~ ^[0-9]+$ ]] && kill -0 "$old_pid" 2>/dev/null; then
            fail "case ${CASE_ID} still has a live memory monitor pid=$old_pid"
        fi
    fi
    rm -f -- \
        "${EXPERIMENT_STATE_DIR}/monitor.pid" \
        "$MONITOR_LOG" \
        "$RUNTIME_STOP_ENV" \
        "$EXPERIMENT_ENV"
}

start_case() {
    case_values "$1"
    preflight || fail 'preflight failed'
    load_managed_mazinb

    if docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
        fail "experimental container already exists: $CONTAINER_NAME; collect evidence then cleanup first"
    fi

    prepare_case_state
    local started_at
    started_at="$(date --iso-8601=seconds)"
    printf 'STARTED_AT=%s\nCASE=%s\nKV_MEM=%s\n' \
        "$started_at" "$CASE_ID" "$KV_MEM_VALUE" >"$EXPERIMENT_ENV"

    printf 'Starting mazinb KV case %s with KV_MEM=%s\n' "$CASE_ID" "$KV_MEM_VALUE"
    MODEL_PROFILE=mazinb \
    QWEN38_MODEL_ROOT="$MANAGED_MODEL_ROOT" \
    MODEL_DIR="$MAZINB_MODEL_DIR" \
    VLLM_IMAGE="$MAZINB_IMAGE" \
    SERVED_NAME="$MAZINB_SERVED_NAME" \
    NSPEC=2 \
    MAXLEN=262144 \
    KV_MEM="$KV_MEM_VALUE" \
    MAXSEQS=3 \
    PREFIX_CACHE=0 \
    INDEX_SHARE=0 \
    AUTOTUNE=0 \
    GPU_UTIL=0.80 \
    QSA_EXACT_TOPK=1 \
    NAME="$CONTAINER_NAME" \
    PORT="$PORT" \
    PUBLISH_HOST=127.0.0.1 \
    RESTART_POLICY=no \
    MONITOR_ENABLED=1 \
    MONITOR_PROTECT=1 \
    MONITOR_MIN_AVAILABLE_GIB=6 \
    MONITOR_MIN_FREE_GIB=2 \
    MONITOR_FREE_GATE_GIB=10 \
    MONITOR_MIN_SWAP_FREE_GIB=8 \
    MONITOR_CONSECUTIVE=5 \
    MONITOR_HEARTBEAT=60 \
    XDG_STATE_HOME="$EXPERIMENT_XDG_STATE_HOME" \
        "$SERVE"
}

print_container_state() {
    if docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
        docker inspect --format \
            'name={{.Name}} state={{.State.Status}} running={{.State.Running}} exit={{.State.ExitCode}} oom_killed={{.State.OOMKilled}} error={{json .State.Error}} started={{.State.StartedAt}} finished={{.State.FinishedAt}} image={{.Config.Image}}' \
            "$CONTAINER_NAME"
    else
        printf 'container_absent=%s\n' "$CONTAINER_NAME"
    fi
}

print_evidence() {
    case_values "$1"
    local since
    since="$(read_started_at || true)"
    printf '===== mazinb KV case %s =====\n' "$CASE_ID"
    printf 'kv_mem=%s\n' "$KV_MEM_VALUE"
    printf 'started_at=%s\n' "${since:-UNKNOWN}"
    printf '\n===== container state =====\n'
    print_container_state
    printf '\n===== memory monitor signals =====\n'
    if [[ -f "$MONITOR_LOG" ]]; then
        grep -E 'monitor started|HEARTBEAT|WARNING memory margin low|memory margin recovered|PROTECT stopping' "$MONITOR_LOG" || true
    else
        printf 'monitor log absent: %s\n' "$MONITOR_LOG"
    fi
    printf '\n===== runtime-stop marker =====\n'
    if [[ -f "$RUNTIME_STOP_ENV" ]]; then
        cat "$RUNTIME_STOP_ENV"
    else
        printf 'runtime-stop marker absent\n'
    fi
    printf '\n===== recent container logs =====\n'
    docker logs --timestamps --tail 120 "$CONTAINER_NAME" 2>&1 || true
    printf '\n===== kernel RM/OOM signals =====\n'
    if [[ -n "$since" ]]; then
        kernel_signals "$since"
    else
        printf 'start timestamp unavailable\n'
    fi
}

run_case() {
    case_values "$1"
    start_case "$CASE_ID"
    load_managed_mazinb

    local since deadline ready=0 soak_completed=0 result='FUNCTIONAL_FAIL' reason='readiness not reached'
    since="$(read_started_at)"
    deadline=$((SECONDS + WAIT_SECONDS))

    while ((SECONDS < deadline)); do
        if ! container_running "$CONTAINER_NAME"; then
            reason='container stopped before readiness'
            break
        fi
        if health_ready; then
            if validate_served_model; then
                ready=1
                result='FUNCTIONAL_PASS'
                reason='ready and served-model validation passed'
            else
                reason='served-model validation failed'
            fi
            break
        fi
        sleep "$POLL_SECONDS"
    done

    if ((ready == 1)); then
        printf 'READY case=%s; starting %ss soak\n' "$CASE_ID" "$SOAK_SECONDS"
        local soak_deadline=$((SECONDS + SOAK_SECONDS))
        while ((SECONDS < soak_deadline)); do
            if ! container_running "$CONTAINER_NAME"; then
                result='FUNCTIONAL_FAIL'
                reason='container stopped during soak'
                break
            fi
            if protected_stop_present; then
                result='FUNCTIONAL_FAIL'
                reason='memory protection triggered during soak'
                break
            fi
            sleep "$POLL_SECONDS"
        done
        if [[ "$result" == 'FUNCTIONAL_PASS' ]] && container_running "$CONTAINER_NAME" && ! protected_stop_present; then
            soak_completed=1
        fi
    fi

    if container_running "$CONTAINER_NAME"; then
        printf 'Stopping experimental runtime after observation window to release memory\n'
        docker stop --time 30 "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
    sleep 2

    local host_result='HOST NOT CLASSIFIED'
    if ((soak_completed == 1)); then
        host_result='HOST-STABILITY PASS'
    fi
    if protected_stop_present; then
        host_result='HOST-STABILITY FAIL'
        reason="${reason}; protected stop observed"
    fi
    if kernel_nv_err_present "$since"; then
        host_result='HOST-STABILITY FAIL'
        reason="${reason}; kernel NV_ERR_NO_MEMORY observed"
    fi
    if [[ "$(docker inspect --format '{{.State.OOMKilled}}' "$CONTAINER_NAME" 2>/dev/null || true)" == true ]]; then
        host_result='HOST-STABILITY FAIL'
        reason="${reason}; Docker OOMKilled=true"
    fi

    printf '\nRESULT case=%s functional=%s host=%s reason=%s\n' \
        "$CASE_ID" "$result" "$host_result" "$reason"
    print_evidence "$CASE_ID"

    [[ "$result" == 'FUNCTIONAL_PASS' && "$host_result" == 'HOST-STABILITY PASS' ]]
}

status_all() {
    printf 'Managed service active: '
    if service_active; then printf 'yes\n'; else printf 'no\n'; fi
    printf 'Canonical runtime: '
    docker inspect --format '{{.Name}} running={{.State.Running}} status={{.State.Status}}' \
        "$CANONICAL_CONTAINER" 2>/dev/null || printf 'absent\n'
    local id
    for id in A B; do
        case_values "$id"
        print_container_state
        [[ -f "$EXPERIMENT_ENV" ]] && cat "$EXPERIMENT_ENV"
    done
}

cleanup_one() {
    case_values "$1"
    if container_running "$CONTAINER_NAME"; then
        fail "refusing cleanup while experimental container is running: $CONTAINER_NAME"
    fi
    if docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
        docker rm "$CONTAINER_NAME" >/dev/null
        printf 'removed experimental container: %s\n' "$CONTAINER_NAME"
    else
        printf 'experimental container absent: %s\n' "$CONTAINER_NAME"
    fi
    if [[ -d "$EXPERIMENT_XDG_STATE_HOME" ]]; then
        rm -rf -- "$EXPERIMENT_XDG_STATE_HOME"
        printf 'removed experimental state: %s\n' "$EXPERIMENT_XDG_STATE_HOME"
    fi
}

case "$ACTION" in
    plan)
        [[ $# -eq 1 ]] || { usage >&2; exit 2; }
        usage
        ;;
    preflight)
        [[ $# -eq 1 ]] || { usage >&2; exit 2; }
        preflight
        ;;
    run)
        [[ $# -eq 2 ]] || { usage >&2; exit 2; }
        case_values "$CASE_ID" || exit 2
        run_case "$CASE_ID"
        ;;
    status)
        [[ $# -eq 1 ]] || { usage >&2; exit 2; }
        status_all
        ;;
    evidence)
        [[ $# -eq 2 ]] || { usage >&2; exit 2; }
        case_values "$CASE_ID" || exit 2
        print_evidence "$CASE_ID"
        ;;
    cleanup)
        [[ $# -le 2 ]] || { usage >&2; exit 2; }
        if [[ -n "$CASE_ID" ]]; then
            case_values "$CASE_ID" || exit 2
            cleanup_one "$CASE_ID"
        else
            cleanup_one A
            cleanup_one B
        fi
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
