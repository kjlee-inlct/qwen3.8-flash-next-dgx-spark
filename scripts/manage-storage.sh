#!/usr/bin/env bash
# Safe storage inventory and cleanup for the Qwen3.8 DGX Spark project.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
RELEASES_DIR="${DATA_HOME}/releases"
CURRENT_LINK="${DATA_HOME}/current"
PREVIOUS_LINK="${DATA_HOME}/previous"
RUNTIME_TRANSITION="${STATE_DIR}/runtime-transition.env"
UPDATE_TRANSITION="${STATE_DIR}/update-transition.env"
OPERATION_LOCK_LIB="${SCRIPT_ROOT}/scripts/lib/operation-lock.sh"
RELEASE_MANAGER="${SCRIPT_ROOT}/scripts/release-manager.sh"
BENCH_DIR="${SCRIPT_ROOT}/scripts/benchmark/results/local"
HF_CACHE="${HF_HOME:-$HOME/.cache/huggingface}"
ACTION="${1:-status}"
YES=0
DRY_RUN=0
PRUNE_EXPERIMENTS=0
BUILD_CACHE_DAYS=7
BENCHMARK_DAYS=30

usage() {
  cat <<'EOF'
Usage:
  ./scripts/manage-storage.sh status
  ./scripts/manage-storage.sh plan [--experiments] [--build-cache-days N] [--benchmark-days N]
  ./scripts/manage-storage.sh prune [--experiments] [--build-cache-days N] [--benchmark-days N] [--yes] [--dry-run]

status
  Read-only inventory of filesystem, managed models, Docker usage, releases,
  benchmark results, Hugging Face cache, and the dedicated PLE swap file.

plan
  Show what prune would remove. No mutation.

prune
  Safe cleanup:
    - stopped qwen38-orca-* experiment containers
    - dangling Docker images
    - Docker builder cache older than N days (default 7)
    - immutable releases other than current/previous
    - local benchmark result files older than N days (default 30)

--experiments
  Additionally remove known disposable experiment image tags:
    vllm-skinny-qsa-det:v1
    vllm-skinny-qsa-exact:v1
  The active manifest image is always protected. Images still referenced by
  containers are left to Docker's normal safety checks.

Never removed by this command:
  - active MODEL_DIR or any managed checkpoint
  - active manifest VLLM_IMAGE
  - current or previous immutable releases
  - PLE swap
  - Hugging Face cache
  - repository source files

Use ./scripts/manage-models.sh for inactive managed checkpoints.
EOF
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
positive_integer() { [[ "$1" =~ ^[1-9][0-9]*$ ]]; }

shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) YES=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --experiments) PRUNE_EXPERIMENTS=1 ;;
    --build-cache-days)
      [[ $# -ge 2 ]] || die "--build-cache-days requires N"
      BUILD_CACHE_DAYS="$2"; shift
      positive_integer "${BUILD_CACHE_DAYS}" || die "--build-cache-days must be a positive integer"
      ;;
    --benchmark-days)
      [[ $# -ge 2 ]] || die "--benchmark-days requires N"
      BENCHMARK_DAYS="$2"; shift
      positive_integer "${BENCHMARK_DAYS}" || die "--benchmark-days must be a positive integer"
      ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done

case "${ACTION}" in
  status|plan|prune) ;;
  -h|--help|help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

ACTIVE_MODEL=""
ACTIVE_IMAGE=""
ACTIVE_PROFILE=""
if [[ -r "${STATE_FILE}" && -r "${STATE_PARSER}" ]]; then
  parsed="$(mktemp)"
  trap 'rm -f -- "${parsed:-}"' EXIT
  if python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}" 2>/dev/null; then
    while IFS= read -r -d '' key && IFS= read -r -d '' value; do
      case "${key}" in
        MODEL_DIR) ACTIVE_MODEL="${value}" ;;
        VLLM_IMAGE) ACTIVE_IMAGE="${value}" ;;
        MODEL_PROFILE) ACTIVE_PROFILE="${value}" ;;
      esac
    done <"${parsed}"
  fi
  rm -f -- "${parsed}"
  trap - EXIT
fi

human_du() {
  local path="$1"
  if [[ -e "${path}" || -L "${path}" ]]; then
    du -sh -- "${path}" 2>/dev/null | awk '{print $1}'
  else
    printf '%s' '-'
  fi
}

bytes_du() {
  local path="$1"
  if [[ -e "${path}" || -L "${path}" ]]; then
    du -sb -- "${path}" 2>/dev/null | awk '{print $1}'
  else
    printf '0'
  fi
}

read_release_id() {
  local link="$1" target
  [[ -L "${link}" ]] || return 1
  target="$(readlink -f -- "${link}")"
  [[ "${target}" == "${RELEASES_DIR}/"* ]] || return 1
  basename -- "${target}"
}

current_release="$(read_release_id "${CURRENT_LINK}" 2>/dev/null || true)"
previous_release="$(read_release_id "${PREVIOUS_LINK}" 2>/dev/null || true)"

inactive_releases() {
  local path id
  [[ -d "${RELEASES_DIR}" ]] || return 0
  for path in "${RELEASES_DIR}"/*; do
    [[ -d "${path}" && ! -L "${path}" ]] || continue
    id="$(basename -- "${path}")"
    [[ "${id}" == "${current_release}" || "${id}" == "${previous_release}" ]] && continue
    [[ "${id}" =~ ^[0-9a-f]{12,40}$ ]] || continue
    printf '%s\n' "${id}"
  done
}

stopped_experiment_containers() {
  command -v docker >/dev/null 2>&1 || return 0
  docker ps -a --filter 'name=^/qwen38-orca-' --format '{{.Names}} {{.State}}' 2>/dev/null |
    awk '$2 != "running" {print $1}'
}

benchmark_candidates() {
  [[ -d "${BENCH_DIR}" ]] || return 0
  find "${BENCH_DIR}" -type f -mtime "+${BENCHMARK_DAYS}" -print 2>/dev/null | sort
}

experiment_images() {
  printf '%s\n' vllm-skinny-qsa-det:v1 vllm-skinny-qsa-exact:v1
}

print_status() {
  printf 'Qwen3.8 storage status\n\n'

  printf '[Filesystem]\n'
  df -h "${SCRIPT_ROOT}" 2>/dev/null | tail -n 1 || true
  printf '  repository       : %s (%s)\n' "${SCRIPT_ROOT}" "$(human_du "${SCRIPT_ROOT}")"
  printf '  state            : %s (%s)\n' "${STATE_DIR}" "$(human_du "${STATE_DIR}")"
  printf '  release data     : %s (%s)\n' "${DATA_HOME}" "$(human_du "${DATA_HOME}")"
  printf '  benchmark local  : %s (%s)\n' "${BENCH_DIR}" "$(human_du "${BENCH_DIR}")"
  printf '  HF cache (report): %s (%s)\n' "${HF_CACHE}" "$(human_du "${HF_CACHE}")"

  printf '\n[Active installation]\n'
  printf '  profile : %s\n' "${ACTIVE_PROFILE:-none}"
  printf '  model   : %s (%s)\n' "${ACTIVE_MODEL:-none}" "$([[ -n "${ACTIVE_MODEL}" ]] && human_du "${ACTIVE_MODEL}" || printf '-')"
  printf '  image   : %s\n' "${ACTIVE_IMAGE:-none}"

  printf '\n[Managed models]\n'
  if [[ -x "${SCRIPT_ROOT}/scripts/manage-models.sh" ]]; then
    "${SCRIPT_ROOT}/scripts/manage-models.sh" list || true
  else
    printf 'manage-models.sh unavailable\n'
  fi

  printf '\n[Immutable releases]\n'
  printf '  current  : %s\n' "${current_release:-none}"
  printf '  previous : %s\n' "${previous_release:-none}"
  if [[ -d "${RELEASES_DIR}" ]]; then
    while IFS= read -r path; do
      [[ -n "${path}" ]] || continue
      printf '  %-40s %s\n' "$(basename -- "${path}")" "$(human_du "${path}")"
    done < <(find "${RELEASES_DIR}" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | sort)
  fi

  printf '\n[PLE swap]\n'
  if [[ -e /swap-ple.img ]]; then
    printf '  apparent : %s\n' "$(ls -lh /swap-ple.img 2>/dev/null | awk '{print $5}')"
    printf '  disk use : %s\n' "$(du -sh /swap-ple.img 2>/dev/null | awk '{print $1}')"
    swapon --show /swap-ple.img 2>/dev/null || true
  else
    printf '  not present\n'
  fi

  printf '\n[Docker]\n'
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    docker system df || true
    printf '\nQwen/vLLM images:\n'
    docker image ls --format '{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}' 2>/dev/null |
      awk '$1 ~ /^(vllm-skinny-|vllm-nv-mixed:|vllm\/vllm-openai:qwen38)/ {print}'
    printf '\nQwen containers:\n'
    docker ps -a --filter 'name=qwen38' --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' || true
  else
    printf 'Docker unavailable.\n'
  fi
}

print_plan() {
  local found=0 id path name image
  printf 'Qwen3.8 storage prune plan\n'
  printf '  build cache age : > %s day(s)\n' "${BUILD_CACHE_DAYS}"
  printf '  benchmark age   : > %s day(s)\n' "${BENCHMARK_DAYS}"
  printf '  experiments     : %s\n\n' "$([[ "${PRUNE_EXPERIMENTS}" == 1 ]] && printf remove-known-tags || printf keep)"

  printf '[Stopped experiment containers]\n'
  while IFS= read -r name; do
    [[ -n "${name}" ]] || continue
    found=1; printf '  remove %s\n' "${name}"
  done < <(stopped_experiment_containers)
  [[ "${found}" == 1 ]] || printf '  none\n'

  found=0
  printf '\n[Inactive immutable releases]\n'
  while IFS= read -r id; do
    [[ -n "${id}" ]] || continue
    found=1
    path="${RELEASES_DIR}/${id}"
    printf '  remove %s (%s)\n' "${id}" "$(human_du "${path}")"
  done < <(inactive_releases)
  [[ "${found}" == 1 ]] || printf '  none\n'

  found=0
  printf '\n[Old benchmark result files]\n'
  while IFS= read -r path; do
    [[ -n "${path}" ]] || continue
    found=1; printf '  remove %s (%s)\n' "${path}" "$(human_du "${path}")"
  done < <(benchmark_candidates)
  [[ "${found}" == 1 ]] || printf '  none\n'

  printf '\n[Docker cache]\n'
  if command -v docker >/dev/null 2>&1; then
    printf '  prune dangling images\n'
    printf '  prune builder cache older than %s day(s)\n' "${BUILD_CACHE_DAYS}"
  else
    printf '  Docker unavailable\n'
  fi

  if [[ "${PRUNE_EXPERIMENTS}" == 1 ]]; then
    printf '\n[Known experiment image tags]\n'
    while IFS= read -r image; do
      [[ -n "${image}" ]] || continue
      if [[ "${image}" == "${ACTIVE_IMAGE}" ]]; then
        printf '  PROTECTED active image: %s\n' "${image}"
      elif docker image inspect "${image}" >/dev/null 2>&1; then
        printf '  remove %s\n' "${image}"
      else
        printf '  absent %s\n' "${image}"
      fi
    done < <(experiment_images)
  fi

  printf '\n[Always protected]\n'
  printf '  active model     : %s\n' "${ACTIVE_MODEL:-none}"
  printf '  active image     : %s\n' "${ACTIVE_IMAGE:-none}"
  printf '  current release  : %s\n' "${current_release:-none}"
  printf '  previous release : %s\n' "${previous_release:-none}"
  printf '  PLE swap and Hugging Face cache are report-only.\n'
}

run_or_echo() {
  if [[ "${DRY_RUN}" == 1 ]]; then
    printf 'DRY-RUN:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

prune_storage() {
  local name id path image hours
  [[ ! -e "${RUNTIME_TRANSITION}" && ! -L "${RUNTIME_TRANSITION}" ]] ||     die "runtime transition is active; finish/recover it before pruning"
  [[ ! -e "${UPDATE_TRANSITION}" && ! -L "${UPDATE_TRANSITION}" ]] ||     die "update transition is active; finish/recover it before pruning"

  if [[ "${DRY_RUN}" != 1 ]]; then
    [[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper unavailable"
    # shellcheck source=scripts/lib/operation-lock.sh
    source "${OPERATION_LOCK_LIB}"
    acquire_operation_lock "${STATE_DIR}" "storage prune" || exit $?
  fi

  print_plan
  if [[ "${DRY_RUN}" != 1 && "${YES}" != 1 ]]; then
    printf '\n'
    read -r -p 'Type PRUNE to apply this storage cleanup plan: ' answer
    [[ "${answer}" == PRUNE ]] || die "cancelled"
  fi

  printf '\nApplying storage cleanup\n'

  while IFS= read -r name; do
    [[ -n "${name}" ]] || continue
    run_or_echo docker rm "${name}"
  done < <(stopped_experiment_containers)

  while IFS= read -r id; do
    [[ -n "${id}" ]] || continue
    run_or_echo "${RELEASE_MANAGER}" discard "${id}"
  done < <(inactive_releases)

  while IFS= read -r path; do
    [[ -n "${path}" ]] || continue
    if [[ "${DRY_RUN}" == 1 ]]; then
      printf 'DRY-RUN: rm -f -- %q\n' "${path}"
    else
      rm -f -- "${path}"
    fi
  done < <(benchmark_candidates)

  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    run_or_echo docker image prune -f
    hours=$(( BUILD_CACHE_DAYS * 24 ))
    run_or_echo docker builder prune -f --filter "until=${hours}h"

    if [[ "${PRUNE_EXPERIMENTS}" == 1 ]]; then
      while IFS= read -r image; do
        [[ -n "${image}" ]] || continue
        if [[ "${image}" == "${ACTIVE_IMAGE}" ]]; then
          printf 'PROTECTED active image: %s\n' "${image}"
          continue
        fi
        docker image inspect "${image}" >/dev/null 2>&1 || continue
        if [[ "${DRY_RUN}" == 1 ]]; then
          printf 'DRY-RUN: docker image rm %q\n' "${image}"
        elif ! docker image rm "${image}"; then
          printf 'SKIP: Docker refused experiment image removal (likely still referenced): %s\n' "${image}" >&2
        fi
      done < <(experiment_images)
    fi
  fi

  printf '\nStorage cleanup complete. Managed checkpoints, active runtime image, current/previous releases, PLE swap, and HF cache were preserved.\n'
}

case "${ACTION}" in
  status) print_status ;;
  plan) print_plan ;;
  prune) prune_storage ;;
esac
