#!/usr/bin/env bash
# Create a privacy-conscious support bundle without changing runtime state.
set -uo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
CONTAINER_NAME="qwen38-flash-next"
SERVICE_UNIT="qwen38-flash-next.service"
INCLUDE_LOGS=1
DRY_RUN=0
FORCE=0
UI_LANG="${UI_LANG:-}"
OUTPUT=""

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  printf 'Usage: ./scripts/collect-diagnostics.sh [--output FILE] [--lang en|ko] [--no-logs] [--dry-run] [--force]\n'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) [[ $# -ge 2 ]] || die "--output requires a path"; OUTPUT="$2"; shift ;;
    --lang) [[ $# -ge 2 ]] || die "--lang requires en or ko"; UI_LANG="$2"; shift ;;
    --no-logs) INCLUDE_LOGS=0 ;;
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done

if [[ -z "${UI_LANG}" ]]; then
  [[ "${LANG:-}" == ko_* ]] && UI_LANG=ko || UI_LANG=en
fi
[[ "${UI_LANG}" == en || "${UI_LANG}" == ko ]] || die "--lang must be en or ko"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT="${OUTPUT:-$PWD/qwen38-diagnostics-${timestamp}.tar.gz}"
case "${OUTPUT}" in
  "~") OUTPUT="${HOME}" ;;
  "~/"*) OUTPUT="${HOME}/${OUTPUT:2}" ;;
esac
OUTPUT="$(realpath -m -- "${OUTPUT}")"

if [[ "${DRY_RUN}" == 1 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    printf '진단 번들 DRY-RUN\n  출력: %s\n  로그 포함: %s\n  시스템 상태는 변경하지 않습니다.\n' \
      "${OUTPUT}" "$([[ "${INCLUDE_LOGS}" == 1 ]] && printf 예 || printf 아니요)"
  else
    printf 'Diagnostic bundle DRY-RUN\n  output: %s\n  include logs: %s\n  no system state will be changed.\n' \
      "${OUTPUT}" "$([[ "${INCLUDE_LOGS}" == 1 ]] && printf yes || printf no)"
  fi
  exit 0
fi

for command in date realpath mktemp tar sed; do
  command -v "${command}" >/dev/null 2>&1 || die "${command} is required"
done
[[ ! -e "${OUTPUT}" || "${FORCE}" == 1 ]] || die "output already exists; use --force: ${OUTPUT}"
mkdir -p "$(dirname -- "${OUTPUT}")"

work_dir="$(mktemp -d)"
bundle_dir="${work_dir}/qwen38-diagnostics"
mkdir -p "${bundle_dir}"
cleanup() { rm -rf -- "${work_dir}"; }
trap cleanup EXIT

capture() {
  local destination="$1"; shift
  {
    printf '$'; printf ' %q' "$@"; printf '\n\n'
    if command -v timeout >/dev/null 2>&1; then
      timeout 30 "$@"
    else
      "$@"
    fi
  } >"${bundle_dir}/${destination}" 2>&1 || true
}

redact_file() {
  local path="$1" temporary="${path}.redacted"
  local host_name escaped_host
  host_name="$(hostname 2>/dev/null || true)"
  escaped_host="${host_name//./\\.}"
  escaped_host="${escaped_host//#/\\#}"
  sed -E \
    -e 's/(Authorization:[[:space:]]*Bearer[[:space:]]+)[^[:space:]]+/\1<REDACTED>/Ig' \
    -e 's/hf_[A-Za-z0-9]{10,}/<REDACTED_HF_TOKEN>/g' \
    -e 's/((TOKEN|PASSWORD|SECRET|API_KEY)[A-Za-z0-9_]*=)[^[:space:]]+/\1<REDACTED>/Ig' \
    -e "s#${HOME//\#/\\#}#<HOME>#g" \
    ${escaped_host:+-e "s#${escaped_host}#<HOST>#g"} \
    "${path}" >"${temporary}"
  mv -- "${temporary}" "${path}"
}

cat >"${bundle_dir}/ABOUT.txt" <<EOF
Qwen3.8 Flash Next diagnostic bundle
Created (UTC): $(date -u --iso-8601=seconds)
Logs included: ${INCLUDE_LOGS}

This archive excludes model weights, caches, full Docker environment variables and
authentication files. Automated redaction is best-effort; review the archive before
sharing it outside your organization.
EOF

capture system.txt uname -a
capture os-release.txt sh -c 'test -r /etc/os-release && cat /etc/os-release'
capture memory.txt free -h
capture swap.txt swapon --show
capture filesystems.txt df -hT
capture docker-version.txt docker version
capture service-status.txt systemctl status "${SERVICE_UNIT}" --no-pager
capture proxy-status.txt systemctl status qwen38-openwebui-proxy.socket --no-pager
capture listening-ports.txt sh -c 'command -v ss >/dev/null && ss -lntp || true'

if [[ -x "${SCRIPT_ROOT}/doctor.sh" ]]; then
  capture doctor.txt "${SCRIPT_ROOT}/doctor.sh"
fi

if [[ -r "${STATE_FILE}" && ! -L "${STATE_FILE}" ]]; then
  (
    # Installer output is shell-escaped and owned by the current installation user.
    # shellcheck disable=SC1090
    source "${STATE_FILE}"
    for name in SCHEMA_VERSION PHASE INSTALL_ROOT MODEL_PROFILE MODEL_REPO MODEL_REVISION \
      MODEL_DIR MODEL_OWNED SWAP_FILE SWAP_OWNED VLLM_IMAGE IMAGE_OWNED SERVED_NAME \
      CONTAINER_NAME CONFIG_OVERRIDE CONFIG_OWNED MONITOR_ENABLED MONITOR_PROTECT \
      MONITOR_MIN_AVAILABLE_GIB MONITOR_MIN_FREE_GIB MONITOR_FREE_GATE_GIB \
      MONITOR_MIN_SWAP_FREE_GIB MONITOR_CONSECUTIVE MONITOR_HEARTBEAT PROXY_ENABLED \
      PROXY_OWNED PROXY_PORT SERVICE_ENABLED SERVICE_OWNED SERVICE_UNIT UI_LANG; do
      printf '%s=%q\n' "${name}" "${!name-}"
    done
  ) >"${bundle_dir}/install-manifest.txt" 2>&1 || true
fi

if command -v docker >/dev/null 2>&1 && docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
  capture container.txt docker inspect --format \
    'name={{.Name}} image={{.Config.Image}} status={{.State.Status}} started={{.State.StartedAt}} restart={{.HostConfig.RestartPolicy.Name}} restart_count={{.RestartCount}} oom={{.State.OOMKilled}} ports={{json .NetworkSettings.Ports}} mounts={{range .Mounts}}{{.Destination}}:{{.RW}} {{end}}' \
    "${CONTAINER_NAME}"
fi

latest_validation=""
for candidate in "${STATE_DIR}"/runtime-validation*.json; do
  [[ -f "${candidate}" ]] || continue
  [[ -z "${latest_validation}" || "${candidate}" -nt "${latest_validation}" ]] && latest_validation="${candidate}"
done
[[ -z "${latest_validation}" ]] || cp -- "${latest_validation}" "${bundle_dir}/runtime-validation.json"

if [[ "${INCLUDE_LOGS}" == 1 ]]; then
  capture service-journal.txt journalctl -u "${SERVICE_UNIT}" --no-pager -n 300
  capture proxy-journal.txt journalctl -u qwen38-openwebui-proxy.service --no-pager -n 200
  if command -v docker >/dev/null 2>&1; then
    capture container-logs.txt docker logs --tail 300 --timestamps "${CONTAINER_NAME}"
  fi
fi

for path in "${bundle_dir}"/*; do
  [[ -f "${path}" ]] && redact_file "${path}"
done
chmod 0700 "${bundle_dir}"
chmod 0600 "${bundle_dir}"/*

temporary_archive="${work_dir}/bundle.tar.gz"
tar --owner=0 --group=0 --numeric-owner -C "${work_dir}" -czf "${temporary_archive}" qwen38-diagnostics
if [[ "${FORCE}" == 1 ]]; then
  install -m 0600 "${temporary_archive}" "${OUTPUT}"
else
  (set -o noclobber; umask 077; : >"${OUTPUT}") 2>/dev/null || die "output appeared during collection: ${OUTPUT}"
  install -m 0600 "${temporary_archive}" "${OUTPUT}"
fi

if [[ "${UI_LANG}" == ko ]]; then
  printf '진단 번들을 생성했습니다: %s\n공유하기 전에 압축 내용을 검토하십시오.\n' "${OUTPUT}"
else
  printf 'Diagnostic bundle created: %s\nReview the archive before sharing it.\n' "${OUTPUT}"
fi
