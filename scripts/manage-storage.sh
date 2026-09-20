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
STORAGE_ASSETS="${SCRIPT_ROOT}/scripts/storage/assets.sh"
# shellcheck source=scripts/storage/assets.sh
source "${STORAGE_ASSETS}"
BENCH_DIR="${SCRIPT_ROOT}/scripts/benchmark/results/local"
HF_CACHE="${HF_HOME:-$HOME/.cache/huggingface}"
ACTION="${1:-status}"
YES=0
DRY_RUN=0
PRUNE_EXPERIMENTS=0
PRUNE_OPTIONAL_IMAGES=0
BUILD_CACHE_DAYS=7
BENCHMARK_DAYS=30

usage() {
  cat <<'EOF'
Usage:
  ./scripts/manage-storage.sh status
  ./scripts/manage-storage.sh recommend
  ./scripts/manage-storage.sh plan [--experiments] [--optional-images] [--build-cache-days N] [--benchmark-days N]
  ./scripts/manage-storage.sh prune [--experiments] [--optional-images] [--build-cache-days N] [--benchmark-days N] [--yes] [--dry-run]

status
  Read-only inventory of filesystem, managed models, Docker usage, releases,
  benchmark results, Hugging Face cache, and the dedicated PLE swap file.

recommend
  Read-only ranked recovery opportunities. Shows inactive managed models,
  Hugging Face cache size, Docker reclaimable bytes, and exact safe follow-up commands.

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

--optional-images
  Additionally remove registered optional-profile image tags (for example
  vllm-nv-mixed:v2). The active manifest image is always protected.

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
    --optional-images) PRUNE_OPTIONAL_IMAGES=1 ;;
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
  status|recommend|plan|prune) ;;
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

managed_model_candidates() {
  declare -A seen=()
  local -a roots=("${HOME}/models" "${SCRIPT_ROOT}/model")
  local root path canonical manifest
  [[ -n "${ACTIVE_MODEL}" ]] && roots+=("${ACTIVE_MODEL}")
  for root in "${roots[@]}"; do
    [[ -e "${root}" ]] || continue
    if [[ -f "${root}/.qwen38-model-manifest.json" ]]; then
      printf '%s\n' "${root}"
      continue
    fi
    [[ -d "${root}" ]] || continue
    while IFS= read -r manifest; do
      [[ -n "${manifest}" ]] || continue
      path="$(dirname -- "${manifest}")"
      canonical="$(realpath -m -- "${path}")"
      [[ -n "${seen[${canonical}]:-}" ]] && continue
      seen["${canonical}"]=1
      printf '%s\n' "${canonical}"
    done < <(find "${root}" -mindepth 1 -maxdepth 2 -type f -name .qwen38-model-manifest.json -print 2>/dev/null | sort)
  done
}

inactive_managed_models() {
  local path canonical_active
  canonical_active=""
  [[ -z "${ACTIVE_MODEL}" ]] || canonical_active="$(realpath -m -- "${ACTIVE_MODEL}")"
  while IFS= read -r path; do
    [[ -n "${path}" ]] || continue
    [[ "$(realpath -m -- "${path}")" == "${canonical_active}" ]] && continue
    printf '%s\n' "${path}"
  done < <(managed_model_candidates)
}

docker_reclaimable_summary() {
  command -v docker >/dev/null 2>&1 || return 0
  docker system df 2>/dev/null | awk '
    NR == 1 {next}
    $1 == "Images" || ($1 == "Build" && $2 == "Cache") {
      print
    }'
}

hf_cache_top() {
  [[ -d "${HF_CACHE}" ]] || return 0
  find "${HF_CACHE}" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null |
    while IFS= read -r -d '' path; do
      bytes="$(bytes_du "${path}")"
      printf '%s\t%s\n' "${bytes}" "${path}"
    done | sort -nr | head -n 12
}

list_optional_storage_images() {
  local image
  while IFS= read -r image; do
    [[ -n "${image}" ]] || continue
    describe_storage_image "${image}" || continue
    [[ "${STORAGE_IMAGE_CLASS}" == optional ]] && printf '%s\n' "${image}"
  done < <(list_storage_images)
}

docker_image_logical_size() {
  local image="$1" bytes
  bytes="$(docker image inspect --format '{{.Size}}' "${image}" 2>/dev/null || true)"
  if [[ "${bytes}" =~ ^[0-9]+$ ]]; then
    numfmt --to=iec-i --suffix=B "${bytes}" 2>/dev/null || printf '%sB' "${bytes}"
  else
    printf '%s' '-'
  fi
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
    printf '\nRegistered Qwen/vLLM images:\n'
    printf '%-12s %-9s %-12s %s\n' CLASS PRESENT LOGICAL_SIZE IMAGE
    while IFS= read -r image; do
      [[ -n "${image}" ]] || continue
      describe_storage_image "${image}" || continue
      if docker image inspect "${image}" >/dev/null 2>&1; then
        printf '%-12s %-9s %-12s %s\n' "${STORAGE_IMAGE_CLASS}" yes "$(docker_image_logical_size "${image}")" "${image}"
      else
        printf '%-12s %-9s %-12s %s\n' "${STORAGE_IMAGE_CLASS}" no - "${image}"
      fi
    done < <(list_storage_images)
    printf '\nQwen containers:\n'
    docker ps -a --filter 'name=qwen38' --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' || true
  else
    printf 'Docker unavailable.\n'
  fi
}

print_recommendations() {
  local path bytes image found=0
  printf 'Qwen3.8 storage recovery recommendations\n\n'

  printf '[1. Inactive managed checkpoints]\n'
  while IFS= read -r path; do
    [[ -n "${path}" ]] || continue
    found=1
    bytes="$(bytes_du "${path}")"
    printf '  %12s  %s\n' "$(numfmt --to=iec-i --suffix=B "${bytes}" 2>/dev/null || printf '%sB' "${bytes}")" "${path}"
    printf '    review: ./scripts/manage-models.sh remove %q --dry-run\n' "${path}"
  done < <(inactive_managed_models)
  [[ "${found}" == 1 ]] || printf '  none\n'

  printf '\n[2. Docker reclaimable]\n'
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    docker system df || true
    printf '  safe project cleanup: ./scripts/manage-storage.sh prune --experiments --dry-run\n'
    printf '  optional profile images: ./scripts/manage-storage.sh plan --optional-images\n'
  else
    printf '  Docker unavailable\n'
  fi

  printf '\n[3. Hugging Face cache - report only]\n'
  printf '  total: %s (%s)\n' "${HF_CACHE}" "$(human_du "${HF_CACHE}")"
  found=0
  while IFS=
  local found=0 id path name image
  printf 'Qwen3.8 storage prune plan\n'
  printf '  build cache age : > %s day(s)\n' "${BUILD_CACHE_DAYS}"
  printf '  benchmark age   : > %s day(s)\n' "${BENCHMARK_DAYS}"
  printf '  experiments     : %s\n' "$([[ "${PRUNE_EXPERIMENTS}" == 1 ]] && printf remove-known-tags || printf keep)"
  printf '  optional images : %s\n\n' "$([[ "${PRUNE_OPTIONAL_IMAGES}" == 1 ]] && printf remove-known-tags || printf keep)"

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
        printf '  remove %s (logical=%s)\n' "${image}" "$(docker_image_logical_size "${image}")"
      else
        printf '  absent %s\n' "${image}"
      fi
    done < <(list_disposable_storage_images)
  fi

  if [[ "${PRUNE_OPTIONAL_IMAGES}" == 1 ]]; then
    printf '\n[Optional profile image tags]\n'
    while IFS= read -r image; do
      [[ -n "${image}" ]] || continue
      if [[ "${image}" == "${ACTIVE_IMAGE}" ]]; then
        printf '  PROTECTED active image: %s\n' "${image}"
      elif docker image inspect "${image}" >/dev/null 2>&1; then
        printf '  remove %s (logical=%s)\n' "${image}" "$(docker_image_logical_size "${image}")"
      else
        printf '  absent %s\n' "${image}"
      fi
    done < <(list_optional_storage_images)
  fi

  printf '\n[Always protected]\n'
  printf '  active model     : %s\n' "${ACTIVE_MODEL:-none}"
  printf '  active image     : %s\n' "${ACTIVE_IMAGE:-none}"
  printf '  current release  : %s\n' "${current_release:-none}"
  printf '  previous release : %s\n' "${previous_release:-none}"
  printf '  PLE swap and Hugging Face cache are report-only.\n'
  printf '  Docker image sizes are logical sizes; shared layers mean actual reclaimed bytes may be smaller.\n'
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
      done < <(list_disposable_storage_images)
    fi

    if [[ "${PRUNE_OPTIONAL_IMAGES}" == 1 ]]; then
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
          printf 'SKIP: Docker refused optional image removal (likely still referenced): %s\n' "${image}" >&2
        fi
      done < <(list_optional_storage_images)
    fi
  fi

  printf '\nStorage cleanup complete. Managed checkpoints, active runtime image, current/previous releases, PLE swap, and HF cache were preserved.\n'
}

case "${ACTION}" in
  status) print_status ;;
  recommend) print_recommendations ;;
  plan) print_plan ;;
  prune) prune_storage ;;
esac
\t' read -r bytes path; do
    [[ -n "${path}" ]] || continue
    found=1
    printf '  %12s  %s\n' "$(numfmt --to=iec-i --suffix=B "${bytes}" 2>/dev/null || printf '%sB' "${bytes}")" "${path}"
  done < <(hf_cache_top)
  [[ "${found}" == 1 ]] || printf '  no top-level cache directories found\n'
  printf '  HF cache is never deleted by manage-storage.sh; inspect it before any manual cleanup.\n'

  printf '\n[4. Protected large allocations]\n'
  printf '  active model : %s (%s)\n' "${ACTIVE_MODEL:-none}" "$([[ -n "${ACTIVE_MODEL}" ]] && human_du "${ACTIVE_MODEL}" || printf '-')"
  if [[ -e /swap-ple.img ]]; then
    printf '  PLE swap     : /swap-ple.img (%s disk use, active runtime dependency)\n' "$(human_du /swap-ple.img)"
  else
    printf '  PLE swap     : not present\n'
  fi

  printf '\nRecommended order: inactive checkpoints -> disposable/optional Docker assets -> inspect HF cache.\n'
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
        printf '  remove %s (logical=%s)\n' "${image}" "$(docker_image_logical_size "${image}")"
      else
        printf '  absent %s\n' "${image}"
      fi
    done < <(list_disposable_storage_images)
  fi

  printf '\n[Always protected]\n'
  printf '  active model     : %s\n' "${ACTIVE_MODEL:-none}"
  printf '  active image     : %s\n' "${ACTIVE_IMAGE:-none}"
  printf '  current release  : %s\n' "${current_release:-none}"
  printf '  previous release : %s\n' "${previous_release:-none}"
  printf '  PLE swap and Hugging Face cache are report-only.\n'
  printf '  Docker image sizes are logical sizes; shared layers mean actual reclaimed bytes may be smaller.\n'
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
      done < <(list_disposable_storage_images)
    fi
  fi

  printf '\nStorage cleanup complete. Managed checkpoints, active runtime image, current/previous releases, PLE swap, and HF cache were preserved.\n'
}

case "${ACTION}" in
  status) print_status ;;
  plan) print_plan ;;
  prune) prune_storage ;;
esac
