#!/usr/bin/env bash
# Install, inspect, or remove the managed systemd runtime service.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
UNIT="qwen38-flash-next.service"
UNIT_FILE="/etc/systemd/system/${UNIT}"
MARKER="Managed qwen38-spark runtime service"
ACTION="${1:-status}"
[[ $# -eq 0 ]] || shift
START=1
ENABLE=1
YES=0
ADOPT_EXISTING=0
RUNTIME_ROOT_OVERRIDE=""
OPERATION_LOCK_LIB="${SCRIPT_ROOT}/scripts/lib/operation-lock.sh"

usage() {
  printf 'Usage: sudo ./scripts/manage-service.sh create [--start|--no-start] [--enable|--no-enable] [--runtime-root PATH] [--adopt-existing] [--yes]\n'
  printf '       sudo ./scripts/manage-service.sh remove [--yes]\n'
  printf '       ./scripts/manage-service.sh status\n'
}
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
managed_file() { [[ -f "$1" && ! -L "$1" ]] && grep -Fq "${MARKER}" "$1"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --start) START=1 ;;
    --no-start) START=0 ;;
    --enable) ENABLE=1 ;;
    --no-enable) ENABLE=0 ;;
    --runtime-root)
      [[ $# -ge 2 ]] || die "--runtime-root requires a path"
      RUNTIME_ROOT_OVERRIDE="$2"
      shift
      ;;
    --adopt-existing) ADOPT_EXISTING=1 ;;
    --yes) YES=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done

if [[ "${ACTION}" == status ]]; then
  installed=no; enabled=no; active=no
  managed_file "${UNIT_FILE}" && installed=yes
  if [[ "${installed}" == yes ]] && command -v systemctl >/dev/null 2>&1; then
    systemctl is-enabled --quiet "${UNIT}" 2>/dev/null && enabled=yes
    systemctl is-active --quiet "${UNIT}" 2>/dev/null && active=yes
  fi
  printf 'Qwen runtime service status\n  installed : %s\n  enabled   : %s\n  active    : %s\n' "${installed}" "${enabled}" "${active}"
  [[ "${installed}" == yes ]]
  exit
fi

[[ ${EUID:-$(id -u)} -eq 0 ]] || die "create/remove requires sudo"
for command in systemctl journalctl install grep getent cut stat mktemp realpath docker curl python3 seq flock awk tail; do command -v "${command}" >/dev/null 2>&1 || die "${command} is required"; done

SERVICE_USER="${SUDO_USER:-${QWEN38_SERVICE_USER:-$(id -un)}}"
[[ "${SERVICE_USER}" != root ]] || die "run through sudo from the user who owns the installation, or set QWEN38_SERVICE_USER"
USER_ENTRY="$(getent passwd "${SERVICE_USER}")"
[[ -n "${USER_ENTRY}" ]] || die "cannot resolve service user: ${SERVICE_USER}"
SERVICE_UID="$(cut -d: -f3 <<<"${USER_ENTRY}")"
SERVICE_GID="$(cut -d: -f4 <<<"${USER_ENTRY}")"
SERVICE_HOME="$(cut -d: -f6 <<<"${USER_ENTRY}")"
SERVICE_GROUP="$(getent group "${SERVICE_GID}" | cut -d: -f1)"
[[ -n "${SERVICE_GROUP}" && -d "${SERVICE_HOME}" ]] || die "cannot resolve service home/group"

CALLER_STATE_HOME="${QWEN38_STATE_HOME:-${SERVICE_HOME}/.local/state}"
STATE_DIR="${CALLER_STATE_HOME}/qwen38-spark"
if [[ "${ADOPT_EXISTING}" == 1 ]]; then
  export QWEN38_RUNTIME_ADOPT_CONTEXT=1
fi
[[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
# shellcheck source=scripts/lib/operation-lock.sh
source "${OPERATION_LOCK_LIB}"
acquire_operation_lock "${STATE_DIR}" "managed service ${ACTION}" "${SERVICE_UID}" "${SERVICE_GID}" || exit $?

if [[ "${ACTION}" == remove ]]; then
  if [[ ! -e "${UNIT_FILE}" ]]; then printf 'Managed runtime service is not installed.\n'; exit 0; fi
  managed_file "${UNIT_FILE}" || die "refusing to remove unmanaged unit: ${UNIT_FILE}"
  [[ "${YES}" == 1 ]] || { read -r -p 'Remove the managed Qwen runtime service? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] || exit 0; }
  systemctl disable --now "${UNIT}" 2>/dev/null || true
  rm -f -- "${UNIT_FILE}"
  systemctl daemon-reload
  systemctl reset-failed "${UNIT}" 2>/dev/null || true
  printf 'Managed Qwen runtime service removed.\n'
  exit 0
fi
[[ "${ACTION}" == create ]] || { usage >&2; exit 2; }
[[ "${ADOPT_EXISTING}" != 1 || "${START}" == 1 ]] || die "--adopt-existing requires --start"

STATE_FILE="${STATE_DIR}/install.env"
RUNTIME_COMMIT_FILE="${STATE_DIR}/runtime-commit.env"
RUNTIME_ADOPT_FILE="${STATE_DIR}/runtime-adopt.env"
INSTALL_STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
[[ -f "${STATE_FILE}" && ! -L "${STATE_FILE}" ]] || die "installation manifest is missing or unsafe: ${STATE_FILE}"
[[ "$(stat -c %u "${STATE_FILE}")" == "${SERVICE_UID}" ]] || die "installation manifest is not owned by ${SERVICE_USER}"
[[ -r "${INSTALL_STATE_PARSER}" ]] || die "install state parser is unavailable: ${INSTALL_STATE_PARSER}"

parse_install_service() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${INSTALL_STATE_PARSER}" install-service "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  INSTALL_ROOT=""; SERVED_NAME=""; CONTAINER_NAME=""
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      SCHEMA_VERSION) [[ "${value}" == 3 || "${value}" == 4 ]] || { rm -f -- "${parsed}"; return 1; } ;;
      PHASE) [[ "${value}" == service_ready || "${value}" == complete ]] || { rm -f -- "${parsed}"; return 1; } ;;
      INSTALL_ROOT) INSTALL_ROOT="${value}" ;;
      SERVED_NAME) SERVED_NAME="${value}" ;;
      CONTAINER_NAME) CONTAINER_NAME="${value}" ;;
      *) rm -f -- "${parsed}"; return 1 ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
  [[ -n "${INSTALL_ROOT}" && -n "${SERVED_NAME}" && "${CONTAINER_NAME}" == qwen38-flash-next ]]
}
parse_install_service || die "installation manifest failed strict service parsing: ${STATE_FILE}"

parse_install_runtime_identity() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${INSTALL_STATE_PARSER}" install-service-runtime "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  RUNTIME_IMAGE=""; RUNTIME_MODEL_DIR=""
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      VLLM_IMAGE) RUNTIME_IMAGE="${value}" ;;
      MODEL_DIR) RUNTIME_MODEL_DIR="${value}" ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
  [[ -n "${RUNTIME_IMAGE}" && -n "${RUNTIME_MODEL_DIR}" ]]
}
parse_install_runtime_identity || die "installation manifest failed strict runtime identity parsing: ${STATE_FILE}"

RUNTIME_ROOT="${RUNTIME_ROOT_OVERRIDE:-${INSTALL_ROOT}}"
[[ "${RUNTIME_ROOT}" == /* ]] || die "runtime root must be an absolute path"
[[ -x "${RUNTIME_ROOT}/scripts/service-runner.sh" ]] || die "runtime root has no service runner: ${RUNTIME_ROOT}"
[[ -x "${RUNTIME_ROOT}/scripts/serve.sh" ]] || die "runtime root has no serve helper: ${RUNTIME_ROOT}"
[[ -r "${RUNTIME_ROOT}/scripts/runtime-transition.sh" ]] || die "runtime root has no transition helper: ${RUNTIME_ROOT}"
[[ "${RUNTIME_ROOT}" != *[[:space:]]* && "${STATE_FILE}" != *[[:space:]]* ]] || die "service paths cannot contain whitespace"
EXPECTED_RUNTIME_ROOT="$(realpath -e -- "${RUNTIME_ROOT}")"
RUNTIME_STATE_PARSER="${INSTALL_STATE_PARSER}"
ADOPT_RUNNER="${SCRIPT_ROOT}/scripts/runtime/service-adopt-runner.sh"
SERVICE_STOP_HELPER="${SCRIPT_ROOT}/scripts/runtime/service-stop.sh"
[[ -r "${ADOPT_RUNNER}" ]] || die "runtime adoption supervisor is unavailable: ${ADOPT_RUNNER}"
[[ -r "${SERVICE_STOP_HELPER}" ]] || die "identity-aware service stop helper is unavailable: ${SERVICE_STOP_HELPER}"

prepare_runtime_adoption() {
  local container_id image running oom model_mount temporary
  container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
  image="$(docker inspect --format '{{.Config.Image}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
  running="$(docker inspect --format '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
  oom="$(docker inspect --format '{{.State.OOMKilled}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
  model_mount="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/model"}}{{.Source}}{{end}}{{end}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
  [[ -n "${container_id}" ]] || die "cannot adopt missing runtime container: ${CONTAINER_NAME}"
  [[ "${image}" == "${RUNTIME_IMAGE}" ]] || die "adopted runtime image mismatch: expected=${RUNTIME_IMAGE} observed=${image:-missing}"
  [[ "${running}" == true ]] || die "adopted runtime container is not running"
  [[ "${oom}" == false ]] || die "adopted runtime container reports OOMKilled=true"
  [[ -n "${model_mount}" && "$(realpath -m -- "${model_mount}")" == "$(realpath -m -- "${RUNTIME_MODEL_DIR}")" ]] ||
    die "adopted runtime model mount mismatch"

  if [[ -e "${RUNTIME_ADOPT_FILE}" || -L "${RUNTIME_ADOPT_FILE}" ]]; then
    local parsed key value adopt_root="" adopt_name="" adopt_id="" adopt_image="" adopt_served=""
    [[ -f "${RUNTIME_ADOPT_FILE}" && ! -L "${RUNTIME_ADOPT_FILE}" ]] ||
      die "runtime adoption marker is unsafe: ${RUNTIME_ADOPT_FILE}"
    parsed="$(mktemp)"
    if ! python3 "${INSTALL_STATE_PARSER}" runtime-adopt "${RUNTIME_ADOPT_FILE}" >"${parsed}"; then
      rm -f -- "${parsed}"
      die "runtime adoption marker failed strict parsing"
    fi
    while IFS= read -r -d '' key && IFS= read -r -d '' value; do
      case "${key}" in
        RUNTIME_ROOT) adopt_root="${value}" ;;
        RUNTIME_CONTAINER_NAME) adopt_name="${value}" ;;
        RUNTIME_CONTAINER_ID) adopt_id="${value}" ;;
        EXPECTED_IMAGE) adopt_image="${value}" ;;
        SERVED_NAME) adopt_served="${value}" ;;
      esac
    done <"${parsed}"
    rm -f -- "${parsed}"
    [[ "${adopt_root}" == "${EXPECTED_RUNTIME_ROOT}" &&
       "${adopt_name}" == "${CONTAINER_NAME}" &&
       "${adopt_id}" == "${container_id}" &&
       "${adopt_image}" == "${RUNTIME_IMAGE}" &&
       "${adopt_served}" == "${SERVED_NAME}" ]] ||
      die "existing runtime adoption marker does not match restored runtime"
    return 0
  fi
  temporary="$(mktemp "${STATE_DIR}/runtime-adopt.env.XXXXXX")"
  {
    printf 'RUNTIME_ADOPT_SCHEMA_VERSION=1\n'
    printf 'RUNTIME_ROOT=%s\n' "${EXPECTED_RUNTIME_ROOT}"
    printf 'RUNTIME_CONTAINER_NAME=%s\n' "${CONTAINER_NAME}"
    printf 'RUNTIME_CONTAINER_ID=%s\n' "${container_id}"
    printf 'EXPECTED_IMAGE=%s\n' "${RUNTIME_IMAGE}"
    printf 'SERVED_NAME=%s\n' "${SERVED_NAME}"
    printf 'CREATED_AT=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  } >"${temporary}"
  python3 "${INSTALL_STATE_PARSER}" runtime-adopt "${temporary}" >/dev/null ||
    { rm -f -- "${temporary}"; die "failed to validate runtime adoption marker"; }
  install -o "${SERVICE_UID}" -g "${SERVICE_GID}" -m 0600 "${temporary}" "${RUNTIME_ADOPT_FILE}"
  rm -f -- "${temporary}"
}

parse_runtime_commit() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${RUNTIME_STATE_PARSER}" runtime-commit "${RUNTIME_COMMIT_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  ATTESTED_RUNTIME_ROOT=""; ATTESTED_CONTAINER_NAME=""; ATTESTED_CONTAINER_ID=""; ATTESTED_COMMITTED_AT=""
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      RUNTIME_COMMIT_SCHEMA_VERSION) [[ "${value}" == 1 ]] || { rm -f -- "${parsed}"; return 1; } ;;
      RUNTIME_ROOT) ATTESTED_RUNTIME_ROOT="${value}" ;;
      RUNTIME_CONTAINER_NAME) ATTESTED_CONTAINER_NAME="${value}" ;;
      RUNTIME_CONTAINER_ID) ATTESTED_CONTAINER_ID="${value}" ;;
      COMMITTED_AT) ATTESTED_COMMITTED_AT="${value}" ;;
      *) rm -f -- "${parsed}"; return 1 ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
  [[ -n "${ATTESTED_RUNTIME_ROOT}" && -n "${ATTESTED_CONTAINER_NAME}" && -n "${ATTESTED_CONTAINER_ID}" && -n "${ATTESTED_COMMITTED_AT}" ]]
}

runtime_commit_matches() {
  local expected_container_id="$1"
  [[ -f "${RUNTIME_COMMIT_FILE}" && ! -L "${RUNTIME_COMMIT_FILE}" ]] || return 1
  parse_runtime_commit || die "runtime commit attestation is invalid: ${RUNTIME_COMMIT_FILE}"
  [[ "${ATTESTED_RUNTIME_ROOT}" == "${EXPECTED_RUNTIME_ROOT}" ]] || return 1
  [[ "${ATTESTED_CONTAINER_NAME}" == "${CONTAINER_NAME}" ]] || return 1
  [[ "${ATTESTED_CONTAINER_ID}" == "${expected_container_id}" ]] || return 1
}

print_readiness_progress() {
  local elapsed="$1" candidate_container_id="$2"
  local active_state sub_state container_state health_state attestation_state log_line container_log ple_worker_state

  active_state="$(systemctl show "${UNIT}" --property=ActiveState --value 2>/dev/null || printf unknown)"
  sub_state="$(systemctl show "${UNIT}" --property=SubState --value 2>/dev/null || printf unknown)"

  container_state=missing
  if [[ -n "${candidate_container_id}" ]]; then
    container_state="$(docker inspect --format '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || printf unknown)"
  fi

  health_state=waiting
  if curl -fsS --max-time 3 http://127.0.0.1:8888/health >/dev/null 2>&1; then
    health_state=ready
  fi

  attestation_state=missing
  if [[ -f "${RUNTIME_COMMIT_FILE}" && ! -L "${RUNTIME_COMMIT_FILE}" ]]; then
    if parse_runtime_commit; then
      if [[ -n "${candidate_container_id}" &&
            "${ATTESTED_RUNTIME_ROOT}" == "${EXPECTED_RUNTIME_ROOT}" &&
            "${ATTESTED_CONTAINER_NAME}" == "${CONTAINER_NAME}" &&
            "${ATTESTED_CONTAINER_ID}" == "${candidate_container_id}" ]]; then
        attestation_state=matching
      else
        attestation_state=present-mismatch
      fi
    else
      attestation_state=invalid
    fi
  fi

  log_line="$(journalctl -u "${UNIT}" -n 1 --no-pager -o cat 2>/dev/null | tail -n 1 || true)"
  [[ -n "${log_line}" ]] || log_line="(no service log yet)"

  container_log="(no container log yet)"
  ple_worker_state=unknown
  if [[ -n "${candidate_container_id}" ]]; then
    container_log="$(docker logs --timestamps --tail 1 "${CONTAINER_NAME}" 2>&1 | tail -n 1 | cut -c1-240 || true)"
    [[ -n "${container_log}" ]] || container_log="(no container log yet)"
    if docker top "${CONTAINER_NAME}" -eo pid,args 2>/dev/null | grep -Fq PleOffloadWorker; then
      ple_worker_state=present
    elif docker logs --tail 200 "${CONTAINER_NAME}" 2>&1 | grep -Fq "(PleOffloadWorker pid="; then
      ple_worker_state=seen-in-log
    else
      ple_worker_state=missing
    fi
  fi

  printf 'Waiting for committed replacement runtime attestation: %d/1800 seconds\n' "${elapsed}"
  printf '  service     : %s/%s\n' "${active_state}" "${sub_state}"
  printf '  container   : %s%s\n' "${container_state}" "${candidate_container_id:+ (${candidate_container_id})}"
  printf '  health      : %s\n' "${health_state}"
  printf '  attestation : %s\n' "${attestation_state}"
  printf '  service log : %s\n' "${log_line}"
  printf '  vLLM log    : %s\n' "${container_log}"
  printf '  PLE worker  : %s\n' "${ple_worker_state}"
}

print_readiness_failure_diagnostics() {
  local candidate_container_id="${1:-}"
  local monitor_log="${STATE_DIR}/monitor.log"

  printf '%s\n' 'Readiness failure diagnostics:' >&2
  printf '%s\n' '--- systemd state ---' >&2
  systemctl show "${UNIT}" \
    --property=ActiveState,SubState,Result,ExecMainCode,ExecMainStatus \
    --no-pager >&2 2>&1 || true

  printf '%s\n' '--- service journal (tail) ---' >&2
  journalctl -u "${UNIT}" -n 120 --no-pager -o cat >&2 2>&1 || true

  printf '%s\n' '--- memory monitor (tail) ---' >&2
  if [[ -r "${monitor_log}" ]]; then
    tail -n 120 "${monitor_log}" >&2 || true
  else
    printf '(monitor log unavailable: %s)\n' "${monitor_log}" >&2
  fi

  printf '%s\n' '--- container state ---' >&2
  if docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
    docker inspect --format \
      'state={{.State.Status}} exit={{.State.ExitCode}} oom_killed={{.State.OOMKilled}} error={{json .State.Error}} started={{.State.StartedAt}} finished={{.State.FinishedAt}}' \
      "${CONTAINER_NAME}" >&2 2>&1 || true
    printf '%s\n' '--- container log (tail) ---' >&2
    docker logs --timestamps --tail 200 "${CONTAINER_NAME}" >&2 2>&1 || true
  elif [[ -n "${candidate_container_id}" ]]; then
    printf 'candidate container unavailable (id=%s)\n' "${candidate_container_id}" >&2
  else
    printf '%s\n' '(candidate container unavailable)' >&2
  fi
}

if [[ -e "${UNIT_FILE}" ]]; then
  managed_file "${UNIT_FILE}" || die "refusing to replace unmanaged unit: ${UNIT_FILE}"
fi
[[ "${YES}" == 1 ]] || { read -r -p "Install ${UNIT} for ${SERVICE_USER}? [Y/n]: " answer; [[ -z "${answer}" || "${answer}" == y || "${answer}" == Y ]] || exit 0; }

tmp_dir="$(mktemp -d)"
trap 'rm -rf -- "${tmp_dir}"' EXIT
if [[ "${ADOPT_EXISTING}" == 1 ]]; then
  SERVICE_EXEC_START="/bin/bash ${ADOPT_RUNNER} --runtime-root ${EXPECTED_RUNTIME_ROOT}"
else
  SERVICE_EXEC_START="/bin/bash ${RUNTIME_ROOT}/scripts/service-runner.sh"
fi
SERVICE_EXEC_STOP="-/bin/bash ${SERVICE_STOP_HELPER}"
cat >"${tmp_dir}/${UNIT}" <<EOF
# ${MARKER}; installed by scripts/manage-service.sh
[Unit]
Description=Qwen3.8 Flash Next service on one DGX Spark
Requires=docker.service
Wants=network-online.target
After=docker.service network-online.target
StartLimitIntervalSec=3600
StartLimitBurst=2

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${RUNTIME_ROOT}
Environment=HOME=${SERVICE_HOME}
Environment=QWEN38_STATE_FILE=${STATE_FILE}
ExecStart=${SERVICE_EXEC_START}
ExecStop=${SERVICE_EXEC_STOP}
Restart=on-failure
RestartSec=60
TimeoutStartSec=infinity
TimeoutStopSec=180
KillMode=control-group

[Install]
WantedBy=multi-user.target
EOF

install -o root -g root -m 0644 "${tmp_dir}/${UNIT}" "${UNIT_FILE}"
systemctl daemon-reload
if [[ "${ENABLE}" == 1 ]]; then
  systemctl enable "${UNIT}"
else
  systemctl disable "${UNIT}" 2>/dev/null || true
fi
if [[ "${START}" == 1 ]]; then
  previous_container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
  if [[ "${ADOPT_EXISTING}" == 1 ]]; then
    prepare_runtime_adoption
  elif [[ -e "${RUNTIME_ADOPT_FILE}" || -L "${RUNTIME_ADOPT_FILE}" ]]; then
    die "stale runtime adoption marker exists: ${RUNTIME_ADOPT_FILE}"
  fi
  rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"
  systemctl reset-failed "${UNIT}" 2>/dev/null || true
  systemctl stop "${UNIT}" 2>/dev/null || true
  systemctl start "${UNIT}"
  ready=0
  candidate_container_id=""
  for attempt in $(seq 1 180); do
    unit_state="$(systemctl show "${UNIT}" --property=ActiveState --value)"
    candidate_container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
    case "${unit_state}" in
      active|activating|reloading) ;;
      *)
        print_readiness_failure_diagnostics "${candidate_container_id}"
        die "service stopped before readiness (state=${unit_state})"
        ;;
    esac
    identity_ok=0
    if [[ -n "${candidate_container_id}" ]]; then
      if [[ "${ADOPT_EXISTING}" == 1 && "${candidate_container_id}" == "${previous_container_id}" ]]; then
        identity_ok=1
      elif [[ "${ADOPT_EXISTING}" != 1 && "${candidate_container_id}" != "${previous_container_id}" ]]; then
        identity_ok=1
      fi
    fi
    if [[ "${identity_ok}" == 1 ]] && \
       curl -fsS --max-time 3 http://127.0.0.1:8888/health >/dev/null 2>&1 && \
       runtime_commit_matches "${candidate_container_id}"; then
      ready=1
      break
    fi
    if (( attempt % 6 == 0 )); then print_readiness_progress "$((attempt * 10))" "${candidate_container_id}"; fi
    sleep 10
  done
  if [[ "${ready}" != 1 ]]; then
    print_readiness_failure_diagnostics "${candidate_container_id:-}"
    die "replacement runtime did not commit and attest within 30 minutes"
  fi
  models="$(curl -fsS --max-time 15 http://127.0.0.1:8888/v1/models)"
  python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); assert any(item.get("id") == expected for item in data.get("data", [])), expected' \
    "${SERVED_NAME}" <<<"${models}" || die "served model ID validation failed"
  runtime_commit_matches "${candidate_container_id}" || die "runtime commit attestation changed after model validation"
  systemctl is-active --quiet "${UNIT}" || die "service became inactive after committed readiness"
  if [[ "${ADOPT_EXISTING}" == 1 ]]; then
    [[ ! -e "${RUNTIME_ADOPT_FILE}" && ! -L "${RUNTIME_ADOPT_FILE}" ]] ||
      die "runtime adoption marker was not consumed by the supervisor"
    printf 'Managed service adopted the existing runtime without replacement: %s\n' "${candidate_container_id}"
  fi
  if [[ "${ENABLE}" == 1 ]]; then
    printf 'Runtime service is enabled, committed, and healthy. Logs:\n  journalctl -fu %s\n' "${UNIT}"
  else
    printf 'Runtime service is committed and healthy; boot enable is deferred. Logs:\n  journalctl -fu %s\n' "${UNIT}"
  fi
else
  if [[ "${ENABLE}" == 1 ]]; then
    printf 'Runtime service installed and enabled; current runtime was not restarted.\n'
  else
    printf 'Runtime service installed with boot enable deferred; current runtime was not restarted.\n'
  fi
fi
