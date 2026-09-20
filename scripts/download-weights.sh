#!/usr/bin/env bash
# Resumable, revision-pinned Hugging Face checkpoint downloader.
set -uo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=model-profiles.sh
source "${SCRIPT_DIR}/model-profiles.sh"

CHECK_ONLY=0
QUIET=0
ALLOW_CANDIDATE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) CHECK_ONLY=1 ;;
    --candidate) ALLOW_CANDIDATE=1 ;;
    -q|--quiet) QUIET=1 ;;
    -h|--help)
      printf 'Usage: [MODEL_PROFILE=PROFILE] ./scripts/download-weights.sh [--candidate] [--check] [--quiet]\n'
      printf 'Interactive downloads show per-file and overall progress by default.\n'
      exit 0 ;;
    *) printf 'FATAL: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

expand_user_path() {
  case "$1" in
    "~") printf '%s\n' "${HOME}" ;;
    "~/"*) printf '%s/%s\n' "${HOME}" "${1:2}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

PROFILE="${MODEL_PROFILE:-orcarouter}"
if [[ "${ALLOW_CANDIDATE}" == 1 ]]; then
  load_download_profile "${PROFILE}" || exit $?
else
  load_model_profile "${PROFILE}" || exit $?
fi
REPO="${REPO:-${PROFILE_REPO}}"; REVISION="${REVISION:-${PROFILE_REVISION}}"
DEST="${DEST:-${MODELS_DIR:-$HOME/models}/$(basename "${PROFILE_MODEL_DIR}")}"; REQUIRE_TOKEN="${PROFILE_GATED}"
DEST="$(realpath -m -- "$(expand_user_path "${DEST}")")"

TOKEN="${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN:-}}"
if [[ -z "${TOKEN}" ]]; then
  TOKEN="$(python3 - <<'PY' 2>/dev/null || true
try:
    from huggingface_hub import get_token
    print(get_token() or "", end="")
except ImportError:
    pass
PY
)"
fi
[[ -n "${TOKEN}" || ! -r "${HOME}/.cache/huggingface/token" ]] || TOKEN="$(<"${HOME}/.cache/huggingface/token")"
if [[ "${REQUIRE_TOKEN}" == 1 && -z "${TOKEN}" ]]; then
  printf 'FATAL: OrcaRouter is gated. Accept its terms and run `hf auth login`.\n' >&2; exit 3
fi
AUTH_ARGS=(); [[ -n "${TOKEN}" ]] && AUTH_ARGS=(-H "Authorization: Bearer ${TOKEN}")
API_URL="https://huggingface.co/api/models/${REPO}/revision/${REVISION}?blobs=true"
BASE_URL="https://huggingface.co/${REPO}/resolve/${REVISION}"

metadata_file="$(mktemp)"
missing_names_file="$(mktemp)"
missing_manifest_file="$(mktemp)"
trap 'rm -f "${metadata_file}" "${missing_names_file}" "${missing_manifest_file}"' EXIT
http_code="$(curl -sS -L -o "${metadata_file}" -w '%{http_code}' "${AUTH_ARGS[@]}" "${API_URL}" || true)"
if [[ "${http_code}" != 200 ]]; then
  printf 'FATAL: Hugging Face metadata request returned HTTP %s.\n' "${http_code}" >&2
  [[ "${http_code}" == 401 || "${http_code}" == 403 ]] && printf 'Accept the model terms and run `hf auth login`.\n' >&2
  exit 4
fi
resolved_revision="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("sha", ""))' "${metadata_file}")"
[[ -n "${resolved_revision}" ]] || { printf 'FATAL: repository revision was not returned\n' >&2; exit 4; }
if [[ "${REVISION}" =~ ^[0-9a-f]{40}$ && "${resolved_revision}" != "${REVISION}" ]]; then
  printf 'FATAL: requested revision %s resolved to unexpected %s\n' "${REVISION}" "${resolved_revision}" >&2; exit 4
fi
file_http_code=200
if [[ "${REQUIRE_TOKEN}" == 1 ]]; then
  file_http_code="$(curl -sS -L --range 0-0 -o /dev/null -w '%{http_code}' \
    "${AUTH_ARGS[@]}" "${BASE_URL}/config.json" || true)"
fi
if [[ "${file_http_code}" != 200 && "${file_http_code}" != 206 ]]; then
  printf 'FATAL: authenticated model-file access returned HTTP %s.\n' "${file_http_code}" >&2
  printf 'The token is valid enough for metadata but cannot download this gated repository.\n' >&2
  printf '1. Accept access at: https://huggingface.co/%s\n' "${REPO}" >&2
  printf '2. Ensure the token has read access to public gated repositories.\n' >&2
  printf '3. Refresh it with `hf auth login --force`, then test:\n' >&2
  printf '   hf download %s config.json --revision %s\n' "${REPO}" "${REVISION}" >&2
  exit 4
fi

manifest="$(python3 - "${metadata_file}" <<'PY'
import json, sys
for item in json.load(open(sys.argv[1])).get("siblings", []):
    name = item["rfilename"]
    if not name.startswith("."):
        lfs = item.get("lfs") or {}
        print(name, item.get("size") or 0, lfs.get("sha256") or "-", sep="\t")
PY
)"
[[ -n "${manifest}" ]] || { printf 'FATAL: empty model manifest\n' >&2; exit 4; }
required_bytes="$(python3 -c 'import json,sys; print(sum(int(x.get("size") or 0) for x in json.load(open(sys.argv[1])).get("siblings", [])))' "${metadata_file}")"
space_probe="${DEST}"
while [[ ! -e "${space_probe}" ]]; do space_probe="$(dirname -- "${space_probe}")"; done
available_bytes="$(df --output=avail -B1 "${space_probe}" | tail -n1 | tr -d ' ')"
existing_bytes=0; [[ ! -d "${DEST}" ]] || existing_bytes="$(du -sb "${DEST}" | cut -f1)"
(( available_bytes + existing_bytes >= required_bytes + 20 * 1024 * 1024 * 1024 )) || {
  printf 'FATAL: insufficient disk space for checkpoint plus 20 GiB reserve.\n' >&2; exit 5; }
if [[ "${CHECK_ONLY}" == 1 ]]; then
  printf 'Preflight passed: %s at %s, %.2f GiB, destination %s\n' \
    "${REPO}" "${resolved_revision}" "$(awk -v n="${required_bytes}" 'BEGIN {print n/1073741824}')" "${DEST}"
  exit 0
fi

mkdir -p "${DEST}" || exit 1
write_model_manifest() {
  local status="$1"
  python3 - "${metadata_file}" "${DEST}/.qwen38-model-manifest.json" "${REPO}" \
    "${resolved_revision}" "${status}" <<'PY'
import json, sys
source, destination, repository, revision, status = sys.argv[1:]
remote = json.load(open(source))
result = {"schema_version": 1, "status": status, "repository": repository,
          "revision": revision,
          "files": [{"path": x["rfilename"], "size": x.get("size") or 0,
                     "sha256": (x.get("lfs") or {}).get("sha256")}
                    for x in remote.get("siblings", []) if not x["rfilename"].startswith(".")]}
temporary = destination + ".tmp"
with open(temporary, "w", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2); stream.write("\n")
import os
os.replace(temporary, destination)
PY
}
write_model_manifest downloading

verify() {
  local path="$1" size="$2" sha="$3"
  [[ -f "${path}" && "$(stat -c %s -- "${path}")" == "${size}" ]] || return 1
  [[ "${sha}" == - || "$(sha256sum -- "${path}" | cut -d' ' -f1)" == "${sha}" ]]
}

printf 'Checkpoint download\n  repository : %s\n  revision   : %s\n  destination: %s\n' "${REPO}" "${resolved_revision}" "${DEST}"

file_count="$(printf '%s\n' "${manifest}" | awk 'NF {count++} END {print count+0}')"
file_index=0
completed_bytes=0
missing_count=0
: >"${missing_names_file}"
: >"${missing_manifest_file}"

while IFS=$'\t' read -r name size sha; do
  [[ -n "${name}" ]] || continue
  file_index=$((file_index + 1))
  output="${DEST}/${name}"
  mkdir -p "$(dirname -- "${output}")"
  overall_pct="$(awk -v done="${completed_bytes}" -v total="${required_bytes}" 'BEGIN {printf "%.1f", total ? done*100/total : 100}')"

  if verify "${output}" "${size}" "${sha}"; then
    printf '  [%d/%d | %s%%] keep %s\n' "${file_index}" "${file_count}" "${overall_pct}" "${name}"
    completed_bytes=$((completed_bytes + size))
    continue
  fi

  if [[ -f "${output}" ]]; then
    printf '  [%d/%d | %s%%] redo %s (partial or failed verification)\n'       "${file_index}" "${file_count}" "${overall_pct}" "${name}"
    rm -f -- "${output}"
  else
    printf '  [%d/%d | %s%%] need %s\n' "${file_index}" "${file_count}" "${overall_pct}" "${name}"
  fi
  printf '%s\n' "${name}" >>"${missing_names_file}"
  printf '%s\t%s\t%s\n' "${name}" "${size}" "${sha}" >>"${missing_manifest_file}"
  missing_count=$((missing_count + 1))
done <<< "${manifest}"

download_missing_with_curl() {
  local name size sha output
  local curl_progress=(--no-progress-meter)
  if [[ "${QUIET}" == 0 && -t 2 ]]; then curl_progress=(--progress-bar); fi
  while IFS=$'\t' read -r name size sha; do
    [[ -n "${name}" ]] || continue
    output="${DEST}/${name}"
    mkdir -p "$(dirname -- "${output}")"
    printf '  curl fallback: %s (%.2f GiB)\n' "${name}" "$(awk -v n="${size}" 'BEGIN {print n/1073741824}')"
    curl -fL -C - --retry 5 --retry-delay 5 --retry-all-errors "${curl_progress[@]}"       "${AUTH_ARGS[@]}" -o "${output}" "${BASE_URL}/${name}" || return 1
  done <"${missing_manifest_file}"
}

download_missing_with_container() {
  local image="${HF_DOWNLOADER_IMAGE:-vllm-orcarouter-v029:v1}"
  local workers="${HF_DOWNLOAD_MAX_WORKERS:-8}"
  local xet_hp="${HF_XET_HIGH_PERFORMANCE:-1}"
  local helper="${SCRIPT_DIR}/lib/hf_snapshot_download.py"

  docker image inspect "${image}" >/dev/null 2>&1 || return 2
  docker run --pull=never --rm --entrypoint python3 "${image}"     -c 'import huggingface_hub' >/dev/null 2>&1 || return 3

  printf 'Using containerized Hugging Face downloader\n'
  printf '  image       : %s\n' "${image}"
  printf '  workers     : %s\n' "${workers}"
  printf '  xet highperf: %s\n' "${xet_hp}"
  printf '  missing     : %s files\n' "${missing_count}"

  docker run --pull=never --rm     --user "$(id -u):$(id -g)"     --entrypoint python3     -e HOME=/tmp     -e HF_HOME=/tmp/hf     -e HF_TOKEN="${TOKEN}"     -e HF_HUB_DISABLE_TELEMETRY=1     -e HF_HUB_DISABLE_IMPLICIT_TOKEN=1     -e HF_XET_HIGH_PERFORMANCE="${xet_hp}"     -e HF_DOWNLOAD_MAX_WORKERS="${workers}"     -v "${DEST}:/download"     -v "${missing_names_file}:/tmp/qwen38-missing.txt:ro"     -v "${helper}:/opt/qwen38/hf_snapshot_download.py:ro"     "${image}"     /opt/qwen38/hf_snapshot_download.py     "${REPO}" "${resolved_revision}" /download /tmp/qwen38-missing.txt
}

if (( missing_count > 0 )); then
  if ! command -v docker >/dev/null 2>&1; then
    printf 'Container downloader unavailable: docker command not found; using curl fallback.\n' >&2
    download_missing_with_curl || { printf 'FINISHED WITH ERRORS -- rerun to resume.\n' >&2; exit 6; }
  else
    set +e
    download_missing_with_container
    download_rc=$?
    set -e
    if [[ "${download_rc}" -ne 0 ]]; then
      printf 'Container downloader unavailable/failed (rc=%s); using curl fallback.\n' "${download_rc}" >&2
      download_missing_with_curl || { printf 'FINISHED WITH ERRORS -- rerun to resume.\n' >&2; exit 6; }
    fi
  fi
else
  printf 'All files already verified; no transfer needed.\n'
fi

fail=0
while IFS=$'\t' read -r name size sha; do
  [[ -n "${name}" ]] || continue
  output="${DEST}/${name}"
  if verify "${output}" "${size}" "${sha}"; then
    printf '  verified %s\n' "${name}"
  else
    printf '  FAIL  %s (verification failed after transfer)\n' "${name}" >&2
    fail=1
  fi
done <"${missing_manifest_file}"
[[ "${fail}" == 0 ]] || { printf 'FINISHED WITH ERRORS -- rerun to resume.\n' >&2; exit 6; }

write_model_manifest complete
printf 'done -> %s (%s), revision %s\n' "${DEST}" "$(du -sh "${DEST}" | cut -f1)" "${resolved_revision}"
