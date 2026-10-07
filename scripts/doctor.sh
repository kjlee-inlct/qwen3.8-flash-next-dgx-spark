#!/usr/bin/env bash
# Read-only installation and runtime diagnostics for a supported model profile.
# shellcheck disable=SC2154
set -u

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
TRANSITION_STATE_FILE="${STATE_DIR}/runtime-transition.env"
PROFILE_SWITCH_STATE_FILE="${STATE_DIR}/profile-switch-transition.env"
PROFILE_SWITCH_BACKUP="${STATE_FILE}.profile-switch-backup"
PROFILE_SWITCH_CANDIDATE="${STATE_FILE}.profile-switch-candidate"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STATE_PARSER="${SCRIPT_DIR}/lib/state_file.py"
ASSET_OWNERSHIP_TOOL="${SCRIPT_DIR}/lib/asset_ownership.py"
ASSET_OWNERSHIP_FILE="${STATE_DIR}/asset-ownership.json"
CHECKPOINT_INTEGRITY="${SCRIPT_DIR}/model/checkpoint_integrity.py"
HYBRID_VALIDATOR="${SCRIPT_DIR}/model/validate-orcarouter-hybrid.py"
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

parse_lifecycle_state_value() {
  local schema="$1" path="$2" wanted="$3" parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" "${schema}" "${path}" >"${parsed}" 2>/dev/null; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    if [[ "${key}" == "${wanted}" ]]; then
      printf '%s\n' "${value}"
      rm -f -- "${parsed}"
      return 0
    fi
  done <"${parsed}"
  rm -f -- "${parsed}"
  return 1
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
  EXPECTED_REPO="${PROFILE_REPO}"; EXPECTED_REVISION="${PROFILE_REVISION}"; EXPECTED_IMAGE="${PROFILE_IMAGE}"
  pass "model profile is supported (${MODEL_PROFILE})"
else
  EXPECTED_REPO=""; EXPECTED_REVISION=""; EXPECTED_IMAGE=""; fail "unsupported model profile: ${MODEL_PROFILE:-missing}"
fi
if [[ "${MODEL_REPO:-}" == "${EXPECTED_REPO}" ]]; then pass "model repository is pinned"; else fail "unexpected model repository: ${MODEL_REPO:-missing}"; fi
if [[ "${MODEL_REVISION:-}" == "${EXPECTED_REVISION}" ]]; then pass "model revision is pinned"; else fail "unexpected model revision: ${MODEL_REVISION:-missing}"; fi
if [[ "${PHASE:-}" == complete ]]; then pass "installation phase is complete"; else warn "installation phase is ${PHASE:-unknown}"; fi
if (( ${SCHEMA_VERSION:-0} >= 3 )); then pass "installation manifest schema supports runtime safety settings"; else warn "installation manifest schema is ${SCHEMA_VERSION:-missing}; run ./install.sh --migrate-manifest to migrate it"; fi

if [[ -e "${ASSET_OWNERSHIP_FILE}" || -L "${ASSET_OWNERSHIP_FILE}" ]]; then
  if [[ ! -r "${ASSET_OWNERSHIP_TOOL}" ]]; then
    fail "asset ownership helper is unavailable: ${ASSET_OWNERSHIP_TOOL}"
  elif [[ -f "${ASSET_OWNERSHIP_FILE}" && ! -L "${ASSET_OWNERSHIP_FILE}" ]] &&
       python3 "${ASSET_OWNERSHIP_TOOL}" verify "${ASSET_OWNERSHIP_FILE}" >/dev/null 2>&1; then
    pass "multi-profile asset ownership registry is valid"
    if [[ "${MODEL_OWNED:-0}" == 1 ]] &&
       ! python3 "${ASSET_OWNERSHIP_TOOL}" owns-model "${ASSET_OWNERSHIP_FILE}" "${MODEL_DIR:-}" >/dev/null 2>&1; then
      fail "active MODEL_OWNED flag is not backed by the ownership registry"
    fi
    if [[ "${IMAGE_OWNED:-0}" == 1 ]] &&
       ! python3 "${ASSET_OWNERSHIP_TOOL}" owns-image "${ASSET_OWNERSHIP_FILE}" "${VLLM_IMAGE:-}" >/dev/null 2>&1; then
      fail "active IMAGE_OWNED flag is not backed by the ownership registry"
    fi
  else
    fail "multi-profile asset ownership registry is malformed or unsafe: ${ASSET_OWNERSHIP_FILE}"
  fi
else
  pass "asset ownership registry is not present; legacy active-asset ownership remains in install.env"
fi

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

if [[ -d "${MODEL_DIR:-}" && -f "${MODEL_DIR:-}/model.safetensors.index.json" ]]; then
  pass "model index is present"
  if [[ "${MODEL_PROFILE:-}" == orcarouter-hybrid ]]; then
    if [[ -r "${HYBRID_VALIDATOR}" ]] && hybrid_detail="$(python3 "${HYBRID_VALIDATOR}" \
      --runtime-only \
      --base-dir "${ORCAROUTER_MODEL_DIR:-$HOME/models/qwen3.8-flash-next-orcarouter}" \
      --h3-dir "${HYBRID_QUANT_LAYOUT_MODEL_DIR:-$HOME/models/qwen3.8-hybrid-quant-layout}" \
      --h4-dir "${H4_ORCA_ALL_MODEL_DIR:-$HOME/models/qwen3.8-h4-orca-all}" \
      --h5-dir "${H5_NEUTRAL_INPUT_MODEL_DIR:-$HOME/models/qwen3.8-h5-neutral-input-scale}" \
      --model-dir "${MODEL_DIR}" 2>&1)"; then
      pass "${hybrid_detail}"
    else
      fail "${hybrid_detail:-OrcaRouter hybrid validator is unavailable or failed}"
    fi
  elif [[ -r "${CHECKPOINT_INTEGRITY}" ]]; then
    if checkpoint_integrity_detail="$(python3 "${CHECKPOINT_INTEGRITY}" "${MODEL_DIR}" 2>&1)"; then
      pass "${checkpoint_integrity_detail}"
    else
      fail "${checkpoint_integrity_detail}"
    fi
  else
    fail "checkpoint integrity checker is unavailable: ${CHECKPOINT_INTEGRITY}"
  fi
else
  fail "model index is missing under ${MODEL_DIR:-unset}"
fi
if [[ "${MODEL_PROFILE:-}" == orcarouter-hybrid ]]; then
  [[ -r "${MODEL_DIR:-}/.qwen38-hybrid-manifest.json" ]] && pass "hybrid checkpoint manifest is present" || fail "hybrid checkpoint manifest is missing"
elif [[ -r "${MODEL_DIR:-}/.qwen38-model-manifest.json" ]]; then
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

if [[ "${PROFILE_CONFIG_OVERRIDE:-0}" == 1 ]]; then
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
else
  pass "model profile does not require a vLLM config override"
fi

if command -v swapon >/dev/null 2>&1 && swapon --show=NAME --noheadings | awk '{$1=$1};1' | grep -Fxq "${SWAP_FILE:-}"; then pass "dedicated PLE swap is active (${SWAP_FILE})"; else fail "dedicated PLE swap is not active (${SWAP_FILE:-unset})"; fi

if [[ -r /proc/meminfo ]]; then
  mem_available_kib="$(awk '$1=="MemAvailable:" {print $2}' /proc/meminfo)"
  mem_free_kib="$(awk '$1=="MemFree:" {print $2}' /proc/meminfo)"
  cma_free_kib="$(awk '$1=="CmaFree:" {print $2}' /proc/meminfo)"; cma_free_kib="${cma_free_kib:-0}"
  swap_free_kib="$(awk '$1=="SwapFree:" {print $2}' /proc/meminfo)"
  (( mem_available_kib >= cma_free_kib )) && noncma_available_kib=$((mem_available_kib - cma_free_kib)) || noncma_available_kib=0
  (( mem_free_kib >= cma_free_kib )) && noncma_free_kib=$((mem_free_kib - cma_free_kib)) || noncma_free_kib=0
  if (( noncma_available_kib >= MONITOR_MIN_AVAILABLE_GIB * 1048576 )); then
    pass "non-CMA memory reserve is healthy ($((noncma_available_kib / 1048576)) GiB available; CmaFree=$((cma_free_kib / 1048576)) GiB)"
  else
    warn "non-CMA memory reserve is below ${MONITOR_MIN_AVAILABLE_GIB} GiB ($((noncma_available_kib / 1024)) MiB available after excluding $((cma_free_kib / 1024)) MiB CmaFree)"
  fi
  if (( noncma_free_kib >= MONITOR_MIN_FREE_GIB * 1048576 || noncma_available_kib >= MONITOR_FREE_GATE_GIB * 1048576 )); then
    pass "non-CMA free-memory floor is healthy ($((noncma_free_kib / 1024)) MiB free)"
  else
    warn "non-CMA free memory is below ${MONITOR_MIN_FREE_GIB} GiB while non-CMA available is below ${MONITOR_FREE_GATE_GIB} GiB ($((noncma_free_kib / 1024)) MiB free)"
  fi
  if (( swap_free_kib >= MONITOR_MIN_SWAP_FREE_GIB * 1048576 )); then pass "swap reserve is healthy ($((swap_free_kib / 1048576)) GiB free)"; elif (( swap_free_kib >= 2 * 1048576 )); then warn "swap reserve is below ${MONITOR_MIN_SWAP_FREE_GIB} GiB ($((swap_free_kib / 1024)) MiB free)"; else fail "swap reserve is critically low ($((swap_free_kib / 1024)) MiB free)"; fi
fi
if [[ -d "${MODEL_DIR:-}" ]]; then
  disk_available_kib="$(df -Pk "${MODEL_DIR}" | awk 'NR==2 {print $4}')"
  if (( disk_available_kib >= 20 * 1048576 )); then pass "model filesystem has at least 20 GiB free ($((disk_available_kib / 1048576)) GiB)"; elif (( disk_available_kib >= 5 * 1048576 )); then warn "model filesystem has less than 20 GiB free ($((disk_available_kib / 1048576)) GiB)"; else fail "model filesystem has less than 5 GiB free ($((disk_available_kib / 1024)) MiB)"; fi
fi

if [[ -r "${TRANSITION_STATE_FILE}" ]]; then
  if transition_state="$(parse_lifecycle_state_value runtime-transition "${TRANSITION_STATE_FILE}" TRANSACTION_STATE)"; then
    fail "runtime transition is incomplete (${transition_state}); run runtime-transition.sh recover before maintenance"
  else
    fail "runtime transition state is malformed; inspect ${TRANSITION_STATE_FILE} before maintenance"
  fi
else
  pass "no incomplete runtime transition exists"
fi

if [[ -r "${PROFILE_SWITCH_STATE_FILE}" ]]; then
  if profile_switch_state="$(parse_lifecycle_state_value profile-switch "${PROFILE_SWITCH_STATE_FILE}" PROFILE_SWITCH_STATE)"; then
    fail "profile-switch transition is incomplete (${profile_switch_state}); run scripts/profile-switch-transition.sh recover before maintenance"
  else
    fail "profile-switch transition state is malformed; inspect ${PROFILE_SWITCH_STATE_FILE} before maintenance"
  fi
elif [[ -e "${PROFILE_SWITCH_BACKUP}" || -L "${PROFILE_SWITCH_BACKUP}" ||
        -e "${PROFILE_SWITCH_CANDIDATE}" || -L "${PROFILE_SWITCH_CANDIDATE}" ]]; then
  fail "profile-switch candidate/backup artifacts exist without transaction state; automatic cleanup is intentionally disabled"
else
  pass "no incomplete profile-switch transition exists"
fi

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  pass "Docker daemon is available"
  if docker image inspect "${VLLM_IMAGE:-}" >/dev/null 2>&1; then
    pass "vLLM image is present"
    if [[ "${MODEL_PROFILE:-}" == orcarouter ]]; then
      if [[ "${VLLM_IMAGE:-}" == "${EXPECTED_IMAGE}" ]]; then
        pass "managed OrcaRouter image matches profile default"
        h38_scope="$(docker image inspect --format '{{ index .Config.Labels "qwen38.h38scope" }}' "${VLLM_IMAGE}" 2>/dev/null || true)"
        [[ "${h38_scope}" == decoder-v1 ]] && pass "H38 decoder-scope image label is valid" || fail "H38 decoder-scope image label mismatch: ${h38_scope:-missing}"
      elif [[ "${VLLM_IMAGE:-}" == vllm-skinny-tp1:v1 ]]; then
        warn "managed OrcaRouter still uses the legacy image; run --refresh-profile-defaults after the immutable release update"
      else
        fail "managed OrcaRouter image drift: manifest=${VLLM_IMAGE:-missing}, profile=${EXPECTED_IMAGE:-missing}"
      fi
    fi
  else
    fail "vLLM image is missing"
  fi
  if docker inspect "${ROLLBACK_CONTAINER}" >/dev/null 2>&1; then if [[ -r "${TRANSITION_STATE_FILE}" ]]; then fail "rollback container exists while a runtime transition is incomplete (${ROLLBACK_CONTAINER})"; else warn "stale rollback container exists (${ROLLBACK_CONTAINER})"; fi; else pass "no stale rollback container exists"; fi
  if docker inspect "${RUNTIME_CONTAINER}" >/dev/null 2>&1; then
    state="$(docker inspect --format '{{.State.Status}}' "${RUNTIME_CONTAINER}" 2>/dev/null)"; [[ "${state}" == running ]] && pass "container is running" || fail "container state is ${state}"
    runtime_image="$(docker inspect --format '{{.Config.Image}}' "${RUNTIME_CONTAINER}" 2>/dev/null || true)"; [[ "${runtime_image}" == "${VLLM_IMAGE:-}" ]] && pass "runtime container image matches installation manifest" || warn "runtime image drift: running=${runtime_image:-unknown}, manifest=${VLLM_IMAGE:-missing}"
    runtime_model_mount="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/model"}}{{.Source}}{{end}}{{end}}' "${RUNTIME_CONTAINER}" 2>/dev/null || true)"; [[ "${runtime_model_mount}" == "${MODEL_DIR:-}" ]] && pass "runtime model mount matches installation manifest" || warn "runtime model mount drift: running=${runtime_model_mount:-missing}, manifest=${MODEL_DIR:-missing}"
    runtime_env="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "${RUNTIME_CONTAINER}" 2>/dev/null || true)"
    if [[ "${MODEL_PROFILE:-}" == orcarouter && "${VLLM_IMAGE:-}" == "${EXPECTED_IMAGE}" ]]; then
      grep -Fxq 'VLLM_PLE_MMAP=1' <<<"${runtime_env}" && pass "managed OrcaRouter runtime uses PLE mmap" || fail "managed OrcaRouter PLE mmap setting is missing"
      grep -Fxq 'VLLM_QSA_EXACT_TOPK=1' <<<"${runtime_env}" && pass "managed OrcaRouter runtime uses exact QSA" || fail "managed OrcaRouter exact-QSA setting is missing"
      grep -Fxq 'QWEN38_MARLIN_CANONICAL_ORDER=1' <<<"${runtime_env}" && pass "managed OrcaRouter H38 canonical order is enabled" || fail "managed OrcaRouter H38 canonical-order setting is missing"
      grep -Fxq 'QWEN38_MARLIN_CANONICAL_SCOPE=decoder' <<<"${runtime_env}" && pass "managed OrcaRouter H38 scope is decoder-only" || fail "managed OrcaRouter H38 decoder scope is missing"
      grep -Fxq 'VLLM_CACHE_ROOT=/root/.cache/vllm/h38-marlin-canonical-decoder-managed-v1' <<<"${runtime_env}" && pass "managed OrcaRouter H38 compile cache is isolated" || fail "managed OrcaRouter H38 compile-cache namespace is missing"
    fi
    if [[ "${MODEL_PROFILE:-}" == orcarouter-hybrid ]]; then
      declare -A expected_hybrid_mounts=(
        ["/base-model"]="${ORCAROUTER_MODEL_DIR:-$HOME/models/qwen3.8-flash-next-orcarouter}"
        ["/h3-model"]="${HYBRID_QUANT_LAYOUT_MODEL_DIR:-$HOME/models/qwen3.8-hybrid-quant-layout}"
        ["/h4-all"]="${H4_ORCA_ALL_MODEL_DIR:-$HOME/models/qwen3.8-h4-orca-all}"
        ["/h5-parent"]="${H5_NEUTRAL_INPUT_MODEL_DIR:-$HOME/models/qwen3.8-h5-neutral-input-scale}"
      )
      for destination in "/base-model" "/h3-model" "/h4-all" "/h5-parent"; do
        actual_source="$(docker inspect --format "{{range .Mounts}}{{if eq .Destination \"${destination}\"}}{{.Source}}{{end}}{{end}}" "${RUNTIME_CONTAINER}" 2>/dev/null || true)"
        expected_source="$(realpath -m -- "${expected_hybrid_mounts[${destination}]}" 2>/dev/null || printf '%s' "${expected_hybrid_mounts[${destination}]}")"
        actual_source_canonical=""
        [[ -z "${actual_source}" ]] || actual_source_canonical="$(realpath -m -- "${actual_source}" 2>/dev/null || printf '%s' "${actual_source}")"
        [[ -n "${actual_source_canonical}" && "${actual_source_canonical}" == "${expected_source}" ]] && pass "hybrid parent mount matches (${destination})" || fail "hybrid parent mount drift at ${destination}: ${actual_source:-missing}"
      done
      grep -Fxq 'VLLM_PLE_MMAP=1' <<<"${runtime_env}" && pass "hybrid runtime uses PLE mmap" || fail "hybrid runtime PLE mmap setting is missing"
      grep -Fxq 'VLLM_QSA_EXACT_TOPK=1' <<<"${runtime_env}" && pass "hybrid runtime uses exact QSA" || fail "hybrid runtime exact-QSA setting is missing"
    fi
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
if [[ "${MODEL_PROFILE:-}" == orcarouter-hybrid && "${MONITOR_PROTECT:-0}" != 1 ]]; then
  warn "OrcaRouter hybrid host protection is disabled; use ./install.sh --model orcarouter-hybrid --protect --yes"
fi

if [[ "${PROXY_ENABLED:-0}" == 1 ]]; then if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet qwen38-openwebui-proxy.socket; then pass "managed API access socket is active"; else fail "managed API access was selected but its socket is not active"; fi; fi
if command -v curl >/dev/null 2>&1 && curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null 2>&1; then pass "health endpoint responds"; else fail "health endpoint does not respond"; fi

printf '\nSummary: %d failure(s), %d warning(s)\n' "${ERRORS}" "${WARNINGS}"
if (( ERRORS > 0 || (STRICT == 1 && WARNINGS > 0) )); then exit 1; fi
