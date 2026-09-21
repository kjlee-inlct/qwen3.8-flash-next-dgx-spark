#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
ACTION="${1:-list}"
TARGET="${2:-}"
YES=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  ./scripts/manage-models.sh list
  ./scripts/manage-models.sh remove PATH [--yes] [--dry-run]

list:
  Shows managed model and hybrid-checkpoint directories discovered from the active
  installation, $HOME/models, and the repository-local ./model directory.

remove:
  Deletes only a directory containing .qwen38-model-manifest.json or
  .qwen38-hybrid-manifest.json. The active installation MODEL_DIR and any
  checkpoint mounted by a running Docker container are never deleted here.
  Use ./uninstall.sh --purge-model for the active installation model.
EOF
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

if [[ "${ACTION}" == remove ]]; then
  [[ $# -ge 2 ]] || die "remove requires PATH"
  shift 2
else
  shift || true
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) YES=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done

ACTIVE_MODEL=""
ACTIVE_PROFILE=""
if [[ -r "${STATE_FILE}" && -r "${STATE_PARSER}" ]]; then
  parsed="$(mktemp)"
  if python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}" 2>/dev/null; then
    while IFS= read -r -d '' key && IFS= read -r -d '' value; do
      case "${key}" in
        MODEL_DIR) ACTIVE_MODEL="${value}" ;;
        MODEL_PROFILE) ACTIVE_PROFILE="${value}" ;;
      esac
    done <"${parsed}"
  fi
  rm -f -- "${parsed}"
fi

manifest_path() {
  local path="$1"
  if [[ -f "${path}/.qwen38-model-manifest.json" ]]; then
    printf '%s\n' "${path}/.qwen38-model-manifest.json"
  elif [[ -f "${path}/.qwen38-hybrid-manifest.json" ]]; then
    printf '%s\n' "${path}/.qwen38-hybrid-manifest.json"
  else
    return 1
  fi
}

manifest_summary() {
  python3 - "$1" <<'PY'
import json
import pathlib
import sys

p = pathlib.Path(sys.argv[1])
try:
    d = json.loads(p.read_text(encoding="utf-8"))
except Exception:
    print("INVALID\t-\t-\t-\t-")
    raise SystemExit

status = d.get("status", "-")
if p.name == ".qwen38-hybrid-manifest.json":
    kind = "hybrid"
    repo = f"hybrid:{d.get('variant', '-')}"
    rev = d.get("overlay_revision", d.get("base_revision", "-"))
    files = d.get("affected_shards", [])
else:
    kind = "model"
    repo = d.get("repository", "-")
    rev = d.get("revision", "-")
    files = d.get("files", [])

print(f"{status}\t{kind}\t{repo}\t{rev}\t{len(files) if isinstance(files, list) else '-'}")
PY
}

mounted_by_running_container() {
  local target="$1" cid source
  command -v docker >/dev/null 2>&1 || return 1
  while IFS= read -r cid; do
    [[ -n "${cid}" ]] || continue
    while IFS= read -r source; do
      [[ -n "${source}" ]] || continue
      if [[ "$(realpath -m -- "${source}")" == "${target}" ]]; then
        return 0
      fi
    done < <(docker inspect --format '{{range .Mounts}}{{println .Source}}{{end}}' "${cid}" 2>/dev/null || true)
  done < <(docker ps -q 2>/dev/null || true)
  return 1
}

discover() {
  declare -A seen=()
  local -a candidates=()
  local -a paths=()
  [[ -n "${ACTIVE_MODEL}" ]] && candidates+=("${ACTIVE_MODEL}")
  candidates+=("${HOME}/models" "${SCRIPT_ROOT}/model")

  local base path canonical
  for base in "${candidates[@]}"; do
    [[ -e "${base}" ]] || continue
    paths=()
    if manifest_path "${base}" >/dev/null 2>&1; then
      paths=("${base}")
    elif [[ -d "${base}" ]]; then
      mapfile -t paths < <(
        find "${base}" -mindepth 1 -maxdepth 2 -type f \
          \( -name .qwen38-model-manifest.json -o -name .qwen38-hybrid-manifest.json \) \
          -printf '%h\n' 2>/dev/null | sort -u
      )
    else
      continue
    fi
    for path in "${paths[@]}"; do
      canonical="$(realpath -m -- "${path}")"
      [[ -n "${seen[${canonical}]:-}" ]] && continue
      seen["${canonical}"]=1
      printf '%s\n' "${canonical}"
    done
  done
}

list_models() {
  local found=0 path manifest status kind repo revision files size active
  printf 'Managed Qwen3.8 model directories\n'
  printf '%-8s %-10s %-8s %-8s %-42s %s\n' ACTIVE STATUS KIND SIZE REPOSITORY PATH
  while IFS= read -r path; do
    [[ -n "${path}" ]] || continue
    found=1
    manifest="$(manifest_path "${path}")"
    IFS=$'\t' read -r status kind repo revision files < <(manifest_summary "${manifest}")
    size="$(du -sh -- "${path}" 2>/dev/null | cut -f1 || printf '?')"
    active=no
    [[ -n "${ACTIVE_MODEL}" && "$(realpath -m -- "${ACTIVE_MODEL}")" == "${path}" ]] && active=yes
    printf '%-8s %-10s %-8s %-8s %-42s %s\n' "${active}" "${status}" "${kind}" "${size}" "${repo}" "${path}"
    printf '         revision=%s files=%s%s\n' "${revision}" "${files}" "$([[ "${active}" == yes ]] && printf ' profile=%s' "${ACTIVE_PROFILE}" || true)"
  done < <(discover)
  [[ "${found}" == 1 ]] || printf '(none found)\n'
}

remove_model() {
  local path manifest status kind repo revision files size allowed
  path="$(realpath -m -- "${TARGET}")"
  [[ -d "${path}" ]] || die "model directory not found: ${path}"
  manifest="$(manifest_path "${path}" 2>/dev/null || true)"
  [[ -n "${manifest}" ]] || die "refusing deletion: model/hybrid manifest missing"

  if [[ -n "${ACTIVE_MODEL}" && "$(realpath -m -- "${ACTIVE_MODEL}")" == "${path}" ]]; then
    die "refusing active model deletion; use ./uninstall.sh --purge-model"
  fi
  if mounted_by_running_container "${path}"; then
    die "refusing deletion: checkpoint is mounted by a running Docker container"
  fi

  allowed=0
  [[ "${path}" == "${HOME}/models/"* ]] && allowed=1
  [[ "${path}" == "${SCRIPT_ROOT}/model" ]] && allowed=1
  [[ "${allowed}" == 1 ]] || die "refusing deletion outside $HOME/models or repository ./model"

  IFS=$'\t' read -r status kind repo revision files < <(manifest_summary "${manifest}")
  [[ "${status}" != INVALID ]] || die "refusing deletion: invalid model manifest"
  size="$(du -sh -- "${path}" 2>/dev/null | cut -f1 || printf '?')"
  printf 'Model removal candidate\n  path     : %s\n  kind     : %s\n  repo     : %s\n  revision : %s\n  status   : %s\n  size     : %s\n' \
    "${path}" "${kind}" "${repo}" "${revision}" "${status}" "${size}"

  if [[ "${DRY_RUN}" == 1 ]]; then
    printf 'DRY-RUN: no files removed.\n'
    return 0
  fi
  if [[ "${YES}" != 1 ]]; then
    read -r -p 'Type DELETE to permanently remove this model directory: ' answer
    [[ "${answer}" == DELETE ]] || die "cancelled"
  fi
  rm -rf --one-file-system -- "${path}"
  printf 'Removed model directory: %s\n' "${path}"
}

case "${ACTION}" in
  list) [[ -z "${TARGET}" ]] || die "list takes no PATH"; list_models ;;
  remove) remove_model ;;
  -h|--help|help) usage ;;
  *) usage >&2; exit 2 ;;
esac
