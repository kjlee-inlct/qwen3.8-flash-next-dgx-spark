#!/usr/bin/env bash
# Read-only installation and runtime diagnostics for a supported model profile.
# shellcheck disable=SC2154
set -u

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
TRANSITION_STATE_FILE="${STATE_DIR}/runtime-transition.env"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STATE_PARSER="${SCRIPT_DIR}/lib/state_file.py"
# shellcheck source=model-profiles.sh
source "${SCRIPT_DIR}/model-profiles.sh"
SERVICE_UNIT="qwen38-flash-next.service"
STRICT=0
ERRORS=0
WARNINGS=0

usage() { printf 'Usage: ./scripts/doctor.sh [--strict]\nRead-only checks; --strict also fails when warnings are found.\n'; }
pass() { printf '[PASS] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; WARNINGS=$((WARNINGS + 1)); }
fail() { printf '[FAIL] %s\n' "$*"; ERRORS=$((ERRORS + 1)); }

parse_install_manifest() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-doctor "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in --strict) STRICT=1 ;; -h|--help) usage; exit 0 ;; *) printf 'ERROR: unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;; esac
  shift
done

printf 'Qwen3.8 Flash Next doctor (read-only)\n\n'

if [[ -r "${STATE_FILE}" ]]; then
  if [[ ! -r "${STATE_PARSER}" ]]; then
    fail "strict state parser is unavailable: ${STATE_PARSER}"
  elif parse_install_manifest; then
    pass "installation manifest is readable (${PHASE:-unknown})"
  else
    fail "installation manifest failed strict parsing: ${STATE_FILE}"
  fi
else
  fail "installation manifest is missing: ${STATE_FILE}"
fi

if load_model_profile "${MODEL_PROFILE:-}" 2>/dev/null; then
  EXPECTED_REPO="${PROFILE_REPO}"; EXPECTED_REVISION="${PROFILE_REVISION}"
  pass "model profile is supported (${MODEL_PROFILE})"
else
  EXPECTED_REPO=""; EXPECTED_REVISION=""; fail "unsupported model profile: ${MODEL_PROFILE:-missing}"
fi
if [[ "${MODEL_REPO:-}" == "${EXPECTED_REPO}" ]]; then pass "model repository is pinned"; else fail "unexpected model repository: ${MODEL_REPO:-missing}"; fi
if [[ "${MODEL_REVISION:-}" == "${EXPECTED_REVISION}" ]]; then pass "model revision is pinned"; else fail "unexpected model revision: ${MODEL_REVISION:-missing}"; fi
if [[ "${PHASE:-}" == complete ]]; then pass "installation phase is complete"; else warn "installation phase is ${PHASE:-unknown}"; fi
if (( ${SCHEMA_VERSION:-0} >= 3 )); then pass "installation manifest schema supports runtime safety settings"; else warn "installation manifest schema is ${SCHEMA_VERSION:-missing}; run ./install.sh --migrate-manifest to migrate it"; fi

MONITOR_ENABLED="${MONITOR_ENABLED:-${MONITOR_PROTECT:-0}}"
MONITOR_MIN_AVAILABLE_GIB="${MONITOR_MIN_AVAILABLE_GIB:-6}"
MONITOR_MIN_FREE_GIB="${MONITOR_MIN_FREE_GIB:-2}"
MONITOR_FREE_GATE_GIB="${MONITOR_FREE_GATE_GIB:-10}"
MONITOR_MIN_SWAP_FREE_GIB="${MONITOR_MIN_SWAP_FREE_GIB:-8}"
MONITOR_CONSECUTIVE="${MONITOR_CONSECUTIVE:-5}"
MONITOR_HEARTBEAT="${MONITOR_HEARTBEAT:-60}"
RUNTIME_CONTAINER="${CONTAINER_NAME:-qwen38-flash-next}"
ROLLBACK_CONTAINER="${RUNTIME_CONTAINER}.rollback"
# shellcheck source=doctor-observability.sh
source "${SCRIPT_DIR}/doctor-observability.sh"

if [[ -d "${MODEL_DIR:-}" && -f "${MODEL_DIR:-}/model.safetensors.index.json" ]]; then pass "model index is present"; else fail "model index is missing under ${MODEL_DIR:-unset}"; fi
if [[ -r "${MODEL_DIR:-}/.qwen38-model-manifest.json" ]]; then
  if python3 - "${MODEL_DIR}/.qwen38-model-manifest.json" "${EXPECTED_REPO}" "${EXPECTED_REVISION}" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle: data = json.load(handle)
assert data.get("repository") == sys.argv[2]
assert data.get("revision") == sys.argv[3]
assert data.get("status") == "complete"
assert data.get("files")
PY
  then pass "checkpoint manifest is complete"; else fail "checkpoint manifest is incomplete or mismatched"; fi
else fail "checkpoint manifest is missing"; fi

CONFIG_CANDIDATE="${CONFIG_OVERRIDE:-}"
if [[ ! -r "${CONFIG_CANDIDATE}" && -r "${STATE_DIR}/config.vllm.json" ]]; then CONFIG_CANDIDATE="${STATE_DIR}/config.vllm.json"; fi
if [[ ! -r "${CONFIG_CANDIDATE}" ]] && command -v docker >/dev/null 2>&1 && docker inspect "${RUNTIME_CONTAINER}" >/dev/null 2>&1; then
  CONFIG_CANDIDATE="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/model/config.json"}}{{.Source}}{{end}}{{end}}' "${RUNTIME_CONTAINER}" 2>/dev/null || true)"
fi
if [[ -r "${CONFIG_CANDIDATE}" ]]; then
  if python3 - "${CONFIG_CANDIDATE}" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8")); values = []
def walk(item):
    if isinstance(item, dict):
        for value in item.values(): walk(value)
    elif isinstance(item, list):
        for value in item: walk(value)
    elif isinstance(item, str): values.append(item)
walk(data); assert "qwen_sparse_attention" not in values
PY
  then pass "vLLM config is compatible (${CONFIG_CANDIDATE})"; else fail "vLLM config still contains incompatible layer values"; fi
else fail "vLLM config override is missing (manifest, generated config, and container mount checked)"; fi

if command -v swapon >/dev/null 2>&1 && swapon --show=NAME --noheadings | awk '{$1=$1};1' | grep -Fxq "${SWAP_FILE:-}"; then pass "dedicated PLE swap is active (${SWAP_FILE})"; else fail "dedicated PLE swap is not active (${SWAP_FILE:-unset})"; fi

if [[ -r /proc/meminfo ]]; then
  mem_available_kib="$(awk '$1=="MemAvailable:" {print $2}' /proc/meminfo)"; swap_free_kib="$(awk '$1=="SwapFree:" {print $2}' /proc/meminfo)"
  if (( mem_available_kib >= MONITOR_MIN_AVAILABLE_GIB * 1048576 )); then pass "memory reserve is healthy ($((mem_available_kib / 1048576)) GiB available)"; else warn "memory reserve is below ${MONITOR_MIN_AVAILABLE_GIB} GiB ($((mem_available_kib / 1024)) MiB available)"; fi
  if (( swap_free_kib >= MONITOR_MIN_SWAP_FREE_GIB * 1048576 )); then pass "swap reserve is healthy ($((swap_free_kib / 1048576)) GiB free)"; elif (( swap_free_kib >= 2 * 1048576 )); then warn "swap reserve is below ${MONITOR_MIN_SWAP_FREE_GIB} GiB ($((swap_free_kib / 1024)) MiB free)"; else fail "swap reserve is critically low ($((swap_free_kib / 1024)) MiB free)"; fi
fi
if [[ -d "${MODEL_DIR:-}" ]]; then
  disk_available_kib="$(df -Pk "${MODEL_DIR}" | awk 'NR==2 {print $4}')"
  if (( disk_available_kib >= 20 * 1048576 )); then pass "model filesystem has at least 20 GiB free ($((disk_available_kib / 1048576)) GiB)"; elif (( disk_available_kib >= 5 * 1048576 )); then warn "model filesystem has less than 20 GiB free ($((disk_available_kib / 1048576)) GiB)"; else fail "model filesystem has less than 5 GiB free ($((disk_available_kib / 1024)) MiB)"; fi
fi

if [[ -r "${TRANSITION_STATE_FILE}" ]]; then transition_state="$(awk -F= '$1=="TRANSACTION_STATE" {print $2; exit}' "${TRANSITION_STATE_FILE}" 2>/dev/null || true)"; fail "runtime transition is incomplete (${transition_state:-unknown}); run runtime-transition.sh recover before maintenance"; else pass "no incomplete runtime transition exists"; fi

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  pass "Docker daemon is available"
  if docker image inspect "${VLLM_IMAGE:-}" >/dev/null 2>&1; then pass "vLLM image is present"; else fail "vLLM image is missing"; fi
  if docker inspect "${ROLLBACK_CONTAINER}" >/dev/null 2>&1; then if [[ -r "${TRANSITION_STATE_FILE}" ]]; then fail "rollback container exists while a runtime transition is incomplete (${ROLLBACK_CONTAINER})"; else warn "stale rollback container exists (${ROLLBACK_CONTAINER})"; fi; else pass "no stale rollback container exists"; fi
  if docker inspect "${RUNTIME_CONTAINER}" >/dev/null 2>&1; then
    state="$(docker inspect --format '{{.State.Status}}' "${RUNTIME_CONTAINER}" 2>/dev/null)"; [[ "${state}" == running ]] && pass "container is running" || fail "container state is ${state}"
    runtime_image="$(docker inspect --format '{{.Config.Image}}' "${RUNTIME_CONTAINER}" 2>/dev/null || true)"; [[ "${runtime_image}" == "${VLLM_IMAGE:-}" ]] && pass "runtime container image matches installation manifest" || warn "runtime image drift: running=${runtime_image:-unknown}, manifest=${VLLM_IMAGE:-missing}"
    runtime_model_mount="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/model"}}{{.Source}}{{end}}{{end}}' "${RUNTIME_CONTAINER}" 2>/dev/null || true)"; [[ "${runtime_model_mount}" == "${MODEL_DIR:-}" ]] && pass "runtime model mount matches installation manifest" || warn "runtime model mount drift: running=${runtime_model_mount:-missing}, manifest=${MODEL_DIR:-missing}"
    runtime_served_name="$(docker inspect --format '{{json .Config.Cmd}}' "${RUNTIME_CONTAINER}" 2>/dev/null | python3 -c 'import json,sys; cmd=json.load(sys.stdin); print(cmd[cmd.index("--served-model-name")+1] if "--served-model-name" in cmd and cmd.index("--served-model-name")+1 < len(cmd) else "")' 2>/dev/null || true)"
    if [[ -n "${runtime_served_name}" && "${runtime_served_name}" == "${SERVED_NAME:-}" ]]; then pass "runtime served model name matches installation manifest"; elif [[ -n "${runtime_served_name}" ]]; then warn "runtime served-name drift: running=${runtime_served_name}, manifest=${SERVED_NAME:-missing}"; else warn "runtime served model name could not be determined from container command"; fi
    init_enabled="$(docker inspect --format '{{.HostConfig.Init}}' "${RUNTIME_CONTAINER}" 2>/dev/null)"; [[ "${init_enabled}" == true ]] && pass "container init process is enabled" || warn "container was created without --init; apply on the next maintenance restart"
    ports="$(docker port "${RUNTIME_CONTAINER}" 2>/dev/null || true)"; if grep -Eq '(^|[[:space:]])127\.0\.0\.1:8888$' <<<"${ports}" && ! grep -Eq '0\.0\.0\.0:8888|\[::\]:8888' <<<"${ports}"; then pass "API is published on loopback only"; else fail "API port is not loopback-only: ${ports:-no published port}"; fi
  else fail "container is missing: ${RUNTIME_CONTAINER}"; fi
else fail "Docker daemon is unavailable"; fi

if command -v systemctl >/dev/null 2>&1 && systemctl cat "${SERVICE_UNIT}" >/dev/null 2>&1; then systemctl is-enabled --quiet "${SERVICE_UNIT}" && pass "systemd service is enabled" || warn "systemd service exists but is disabled"; systemctl is-active --quiet "${SERVICE_UNIT}" && pass "systemd service is active" || warn "systemd service exists but is inactive"; else warn "systemd runtime service is not installed; boot persistence relies on Docker restart policy"; fi

if [[ "${MONITOR_ENABLED}" == 1 ]]; then
  if [[ -r "${STATE_DIR}/monitor.pid" ]]; then monitor_pid="$(<"${STATE_DIR}/monitor.pid")"; if [[ "${monitor_pid}" =~ ^[0-9]+$ && -r "/proc/${monitor_pid}/cmdline" ]] && tr '\0' ' ' <"/proc/${monitor_pid}/cmdline" | grep -Fq monitor-runtime.sh; then pass "memory monitor is running (protect=${MONITOR_PROTECT:-0}, heartbeat=${MONITOR_HEARTBEAT}s)"; else fail "memory protection monitor PID is stale"; fi; else fail "memory protection monitor PID file is missing"; fi
else pass "runtime memory monitor is disabled by configuration"; fi

if [[ "${PROXY_ENABLED:-0}" == 1 ]]; then if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet qwen38-openwebui-proxy.socket; then pass "OpenWebUI proxy socket is active"; else fail "OpenWebUI proxy was selected but is not active"; fi; fi
if command -v curl >/dev/null 2>&1 && curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null 2>&1; then pass "health endpoint responds"; else fail "health endpoint does not respond"; fi

printf '\nSummary: %d failure(s), %d warning(s)\n' "${ERRORS}" "${WARNINGS}"
if (( ERRORS > 0 || (STRICT == 1 && WARNINGS > 0) )); then exit 1; fi
