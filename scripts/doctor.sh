#!/usr/bin/env bash
# Read-only installation and runtime diagnostics for the OrcaRouter profile.
# shellcheck disable=SC1090,SC2154
set -u

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
EXPECTED_REPO="orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
EXPECTED_REVISION="c1209bda15a6bbc4c68b585e93d40c0d85f50306"
SERVICE_UNIT="qwen38-flash-next.service"
STRICT=0
ERRORS=0
WARNINGS=0

usage() {
  printf 'Usage: ./scripts/doctor.sh [--strict]\n'
  printf 'Read-only checks; --strict also fails when warnings are found.\n'
}
pass() { printf '[PASS] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*"; WARNINGS=$((WARNINGS + 1)); }
fail() { printf '[FAIL] %s\n' "$*"; ERRORS=$((ERRORS + 1)); }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict) STRICT=1 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'ERROR: unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

printf 'Qwen3.8 Flash Next doctor (read-only)\n\n'

if [[ -r "${STATE_FILE}" ]]; then
  # The installer writes shell-escaped values with mode 600.
  # shellcheck disable=SC1090
  source "${STATE_FILE}"
  pass "installation manifest is readable (${PHASE:-unknown})"
else
  fail "installation manifest is missing: ${STATE_FILE}"
fi

if [[ "${MODEL_REPO:-}" == "${EXPECTED_REPO}" ]]; then pass "model repository is pinned"; else fail "unexpected model repository: ${MODEL_REPO:-missing}"; fi
if [[ "${MODEL_REVISION:-}" == "${EXPECTED_REVISION}" ]]; then pass "model revision is pinned"; else fail "unexpected model revision: ${MODEL_REVISION:-missing}"; fi
if [[ "${PHASE:-}" == complete ]]; then pass "installation phase is complete"; else warn "installation phase is ${PHASE:-unknown}"; fi

if [[ -d "${MODEL_DIR:-}" && -f "${MODEL_DIR:-}/model.safetensors.index.json" ]]; then
  pass "model index is present"
else
  fail "model index is missing under ${MODEL_DIR:-unset}"
fi
if [[ -r "${MODEL_DIR:-}/.qwen38-model-manifest.json" ]]; then
  if python3 - "${MODEL_DIR}/.qwen38-model-manifest.json" "${EXPECTED_REPO}" "${EXPECTED_REVISION}" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
assert data.get("repository") == sys.argv[2]
assert data.get("revision") == sys.argv[3]
assert data.get("status") == "complete"
assert data.get("files")
PY
  then pass "checkpoint manifest is complete"; else fail "checkpoint manifest is incomplete or mismatched"; fi
else
  fail "checkpoint manifest is missing"
fi

CONFIG_CANDIDATE="${CONFIG_OVERRIDE:-}"
if [[ ! -r "${CONFIG_CANDIDATE}" && -r "${STATE_DIR}/config.vllm.json" ]]; then
  CONFIG_CANDIDATE="${STATE_DIR}/config.vllm.json"
fi
if [[ ! -r "${CONFIG_CANDIDATE}" ]] && command -v docker >/dev/null 2>&1 && \
   docker inspect "${CONTAINER_NAME:-qwen38-flash-next}" >/dev/null 2>&1; then
  CONFIG_CANDIDATE="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/model/config.json"}}{{.Source}}{{end}}{{end}}' \
    "${CONTAINER_NAME:-qwen38-flash-next}" 2>/dev/null || true)"
fi
if [[ -r "${CONFIG_CANDIDATE}" ]]; then
  if python3 - "${CONFIG_CANDIDATE}" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
values = []
def walk(item):
    if isinstance(item, dict):
        for value in item.values(): walk(value)
    elif isinstance(item, list):
        for value in item: walk(value)
    elif isinstance(item, str): values.append(item)
walk(data)
assert "qwen_sparse_attention" not in values
PY
  then pass "vLLM config is compatible (${CONFIG_CANDIDATE})"; else fail "vLLM config still contains incompatible layer values"; fi
else
  fail "vLLM config override is missing (manifest, generated config, and container mount checked)"
fi

if command -v swapon >/dev/null 2>&1 && swapon --show=NAME --noheadings | awk '{$1=$1};1' | grep -Fxq "${SWAP_FILE:-}"; then
  pass "dedicated PLE swap is active (${SWAP_FILE})"
else
  fail "dedicated PLE swap is not active (${SWAP_FILE:-unset})"
fi

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  pass "Docker daemon is available"
  if docker image inspect "${VLLM_IMAGE:-}" >/dev/null 2>&1; then pass "vLLM image is present"; else fail "vLLM image is missing"; fi
  if docker inspect "${CONTAINER_NAME:-qwen38-flash-next}" >/dev/null 2>&1; then
    state="$(docker inspect --format '{{.State.Status}}' "${CONTAINER_NAME:-qwen38-flash-next}" 2>/dev/null)"
    [[ "${state}" == running ]] && pass "container is running" || fail "container state is ${state}"
    ports="$(docker port "${CONTAINER_NAME:-qwen38-flash-next}" 2>/dev/null || true)"
    if grep -Eq '(^|[[:space:]])127\.0\.0\.1:8888$' <<<"${ports}" && ! grep -Eq '0\.0\.0\.0:8888|\[::\]:8888' <<<"${ports}"; then
      pass "API is published on loopback only"
    else
      fail "API port is not loopback-only: ${ports:-no published port}"
    fi
  else
    fail "container is missing: ${CONTAINER_NAME:-qwen38-flash-next}"
  fi
else
  fail "Docker daemon is unavailable"
fi

if command -v systemctl >/dev/null 2>&1 && systemctl cat "${SERVICE_UNIT}" >/dev/null 2>&1; then
  systemctl is-enabled --quiet "${SERVICE_UNIT}" && pass "systemd service is enabled" || warn "systemd service exists but is disabled"
  systemctl is-active --quiet "${SERVICE_UNIT}" && pass "systemd service is active" || warn "systemd service exists but is inactive"
else
  warn "systemd runtime service is not installed; boot persistence relies on Docker restart policy"
fi

if [[ "${MONITOR_PROTECT:-0}" == 1 ]]; then
  if [[ -r "${STATE_DIR}/monitor.pid" ]]; then
    monitor_pid="$(<"${STATE_DIR}/monitor.pid")"
    if [[ "${monitor_pid}" =~ ^[0-9]+$ && -r "/proc/${monitor_pid}/cmdline" ]] && tr '\0' ' ' <"/proc/${monitor_pid}/cmdline" | grep -Fq monitor-runtime.sh; then
      pass "memory protection monitor is running"
    else
      fail "memory protection monitor PID is stale"
    fi
  else
    fail "memory protection monitor PID file is missing"
  fi
else
  warn "automatic low-memory protection is disabled"
fi

if [[ "${PROXY_ENABLED:-0}" == 1 ]]; then
  if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet qwen38-openwebui-proxy.socket; then
    pass "OpenWebUI proxy socket is active"
  else
    fail "OpenWebUI proxy was selected but is not active"
  fi
fi

if command -v curl >/dev/null 2>&1 && curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null 2>&1; then
  pass "health endpoint responds"
else
  fail "health endpoint does not respond"
fi

printf '\nSummary: %d failure(s), %d warning(s)\n' "${ERRORS}" "${WARNINGS}"
if (( ERRORS > 0 || (STRICT == 1 && WARNINGS > 0) )); then exit 1; fi
