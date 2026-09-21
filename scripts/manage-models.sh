#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
MODEL_ASSETS="${SCRIPT_ROOT}/scripts/model-assets.sh"
ACTION="${1:-list}"
TARGET="${2:-}"
YES=0
DRY_RUN=0

[[ -r "${MODEL_ASSETS}" ]] || { printf 'ERROR: model asset registry missing: %s\n' "${MODEL_ASSETS}" >&2; exit 1; }
# shellcheck source=scripts/model-assets.sh
source "${MODEL_ASSETS}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/manage-models.sh list
  ./scripts/manage-models.sh assets
  ./scripts/manage-models.sh remove PATH [--yes] [--dry-run]
  ./scripts/manage-models.sh retire PROFILE [--yes] [--dry-run]

list:
  Shows managed checkpoint directories discovered from the active installation,
  $HOME/models, and the repository-local ./model directory.

assets:
  Shows profile-level checkpoint, container, image, active/install state, and
  dependency information.

remove:
  Deletes only a checkpoint directory containing a managed manifest. It never
  removes Docker containers or images.

retire:
  Retires one logical PROFILE. Stopped experiment containers are removed, then
  profile-owned disposable images/checkpoints are removed when safe. Active
  installation assets, running containers, and assets required by another
  present profile are protected. Use --dry-run to inspect the plan first.
EOF
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

if [[ "${ACTION}" == remove || "${ACTION}" == retire ]]; then
  [[ $# -ge 2 ]] || die "${ACTION} requires a target"
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
ACTIVE_IMAGE=""
if [[ -r "${STATE_FILE}" && -r "${STATE_PARSER}" ]]; then
  parsed="$(mktemp)"
  if python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}" 2>/dev/null; then
    while IFS= read -r -d '' key && IFS= read -r -d '' value; do
      case "${key}" in
        MODEL_DIR) ACTIVE_MODEL="${value}" ;;
        MODEL_PROFILE) ACTIVE_PROFILE="${value}" ;;
        VLLM_IMAGE) ACTIVE_IMAGE="${value}" ;;
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


container_state() {
  local name="$1"
  command -v docker >/dev/null 2>&1 || { printf '%s' unavailable; return; }
  if docker inspect "$name" >/dev/null 2>&1; then
    docker inspect --format '{{.State.Status}}' "$name" 2>/dev/null || printf '%s' unknown
  else
    printf '%s' absent
  fi
}

image_state() {
  local image="$1"
  command -v docker >/dev/null 2>&1 || { printf '%s' unavailable; return; }
  if docker image inspect "$image" >/dev/null 2>&1; then printf '%s' present; else printf '%s' absent; fi
}

profile_present() {
  local profile="$1"
  describe_model_asset "$profile" || return 1
  [[ -e "$MODEL_ASSET_CHECKPOINT" || -L "$MODEL_ASSET_CHECKPOINT" ]] && return 0
  command -v docker >/dev/null 2>&1 || return 1
  docker inspect "$MODEL_ASSET_CONTAINER" >/dev/null 2>&1 && return 0
  if [[ "$MODEL_ASSET_RETIRE_IMAGE" == 1 ]]; then
    docker image inspect "$MODEL_ASSET_IMAGE" >/dev/null 2>&1 && return 0
  fi
  return 1
}

asset_required_by_present_profile() {
  local target="$1" dependent
  while IFS= read -r dependent; do
    [[ -n "$dependent" ]] || continue
    profile_present "$dependent" && { printf '%s' "$dependent"; return 0; }
  done < <(model_asset_dependents "$target")
  return 1
}

list_assets() {
  local profile checkpoint_state checkpoint_size cstate istate active deps
  printf 'Qwen3.8 profile assets\n'
  printf '%-28s %-7s %-9s %-9s %-10s %-12s %s\n' PROFILE ACTIVE CHECKPOINT CONTAINER IMAGE SIZE DEPENDS_ON
  while IFS= read -r profile; do
    [[ -n "$profile" ]] || continue
    describe_model_asset "$profile" || continue
    checkpoint_state=absent
    checkpoint_size=-
    if [[ -e "$MODEL_ASSET_CHECKPOINT" || -L "$MODEL_ASSET_CHECKPOINT" ]]; then
      checkpoint_state=present
      checkpoint_size="$(du -sh -- "$MODEL_ASSET_CHECKPOINT" 2>/dev/null | cut -f1 || printf '?')"
    fi
    cstate="$(container_state "$MODEL_ASSET_CONTAINER")"
    istate="$(image_state "$MODEL_ASSET_IMAGE")"
    active=no
    [[ "$profile" == "$ACTIVE_PROFILE" ]] && active=yes
    printf '%-28s %-7s %-9s %-9s %-10s %-12s %s\n'       "$profile" "$active" "$checkpoint_state" "$cstate" "$istate" "$checkpoint_size" "${MODEL_ASSET_DEPENDS_ON:--}"
    printf '  checkpoint=%s\n  container=%s\n  image=%s%s\n'       "$MODEL_ASSET_CHECKPOINT" "$MODEL_ASSET_CONTAINER" "$MODEL_ASSET_IMAGE"       "$([[ "$MODEL_ASSET_IMAGE" == "$ACTIVE_IMAGE" ]] && printf ' [active-image]' || true)"
  done < <(model_asset_profiles)
}

run_or_echo() {
  if [[ "$DRY_RUN" == 1 ]]; then
    printf 'DRY-RUN:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

retire_profile() {
  local profile="$TARGET" cstate dependent checkpoint_active=0 image_active=0
  describe_model_asset "$profile" || die "unknown profile: $profile"

  [[ "$profile" != "$ACTIVE_PROFILE" ]] || die "refusing active profile retirement: $profile"
  [[ -z "$ACTIVE_MODEL" || "$(realpath -m -- "$ACTIVE_MODEL")" != "$(realpath -m -- "$MODEL_ASSET_CHECKPOINT")" ]] || checkpoint_active=1
  [[ "$MODEL_ASSET_IMAGE" != "$ACTIVE_IMAGE" ]] || image_active=1

  cstate="$(container_state "$MODEL_ASSET_CONTAINER")"
  [[ "$cstate" != running ]] || die "refusing retirement: container is running: $MODEL_ASSET_CONTAINER"

  dependent="$(asset_required_by_present_profile "$profile" 2>/dev/null || true)"

  printf 'Profile retirement candidate\n'
  printf '  profile    : %s\n' "$profile"
  printf '  checkpoint : %s\n' "$MODEL_ASSET_CHECKPOINT"
  printf '  container  : %s (%s)\n' "$MODEL_ASSET_CONTAINER" "$cstate"
  printf '  image      : %s (%s)\n' "$MODEL_ASSET_IMAGE" "$(image_state "$MODEL_ASSET_IMAGE")"
  printf '  dependent  : %s\n' "${dependent:-none}"

  if [[ -n "$dependent" ]]; then
    printf '  protection : required by present profile %s\n' "$dependent"
  fi
  [[ "$checkpoint_active" == 0 ]] || printf '  protection : checkpoint is active installation MODEL_DIR\n'
  [[ "$image_active" == 0 ]] || printf '  protection : image is active installation VLLM_IMAGE\n'

  if [[ "$DRY_RUN" != 1 && "$YES" != 1 ]]; then
    read -r -p 'Type RETIRE to apply this profile cleanup: ' answer
    [[ "$answer" == RETIRE ]] || die "cancelled"
  fi

  if [[ "$cstate" != absent && "$cstate" != unavailable ]]; then
    run_or_echo docker rm "$MODEL_ASSET_CONTAINER"
  fi

  if [[ "$MODEL_ASSET_RETIRE_IMAGE" == 1 && "$image_active" == 0 && -z "$dependent" ]]; then
    if docker image inspect "$MODEL_ASSET_IMAGE" >/dev/null 2>&1; then
      run_or_echo docker image rm "$MODEL_ASSET_IMAGE"
    fi
  fi

  if [[ "$MODEL_ASSET_RETIRE_CHECKPOINT" == 1 && "$checkpoint_active" == 0 && -z "$dependent" ]]; then
    if [[ -d "$MODEL_ASSET_CHECKPOINT" ]] && manifest_path "$MODEL_ASSET_CHECKPOINT" >/dev/null 2>&1; then
      if mounted_by_running_container "$(realpath -m -- "$MODEL_ASSET_CHECKPOINT")"; then
        die "refusing checkpoint deletion: mounted by a running container"
      fi
      run_or_echo rm -rf --one-file-system -- "$MODEL_ASSET_CHECKPOINT"
    fi
  fi

  printf 'Profile retirement complete/planned: %s\n' "$profile"
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
  list) [[ -z "${TARGET}" ]] || die "list takes no target"; list_models ;;
  assets) [[ -z "${TARGET}" ]] || die "assets takes no target"; list_assets ;;
  remove) remove_model ;;
  retire) retire_profile ;;
  -h|--help|help) usage ;;
  *) usage >&2; exit 2 ;;
esac
