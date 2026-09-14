#!/usr/bin/env bash
# Resumable, revision-pinned Hugging Face checkpoint downloader.
set -uo pipefail

CHECK_ONLY=0
case "${1:-}" in
  --check) CHECK_ONLY=1; shift ;;
  -h|--help)
    printf 'Usage: [MODEL_PROFILE=orcarouter|nvidia] ./scripts/download-weights.sh [--check]\n'
    exit 0 ;;
  "") ;;
  *) printf 'FATAL: unknown argument: %s\n' "$1" >&2; exit 2 ;;
esac
[[ $# -eq 0 ]] || { printf 'FATAL: unexpected arguments\n' >&2; exit 2; }

readonly ORCA_REPO="orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
readonly ORCA_REVISION="c1209bda15a6bbc4c68b585e93d40c0d85f50306"
readonly NVIDIA_REPO="nvidia/Qwen3.8-Flash-Next-NVFP4"

PROFILE="${MODEL_PROFILE:-orcarouter}"
case "${PROFILE}" in
  orcarouter)
    REPO="${REPO:-${ORCA_REPO}}"; REVISION="${REVISION:-${ORCA_REVISION}}"
    DEST="${DEST:-${MODELS_DIR:-$HOME/models}/qwen3.8-flash-next-orcarouter}"; REQUIRE_TOKEN=1 ;;
  nvidia)
    REPO="${REPO:-${NVIDIA_REPO}}"; REVISION="${REVISION:-main}"
    DEST="${DEST:-${MODELS_DIR:-$HOME/models}/qwen3.8-flash-next-nvidia}"; REQUIRE_TOKEN=0 ;;
  *) printf 'FATAL: unknown MODEL_PROFILE: %s\n' "${PROFILE}" >&2; exit 2 ;;
esac

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
mkdir -p "${DEST}" || exit 1

metadata_file="$(mktemp)"
trap 'rm -f "${metadata_file}"' EXIT
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
if [[ "${REQUIRE_TOKEN}" == 1 ]] && ! curl -fsSL --range 0-0 "${AUTH_ARGS[@]}" \
    "${BASE_URL}/config.json" >/dev/null; then
  printf 'FATAL: authenticated model-file access failed; accept the gated terms and run `hf auth login`.\n' >&2
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
available_bytes="$(df --output=avail -B1 "${DEST}" | tail -n1 | tr -d ' ')"
existing_bytes="$(du -sb "${DEST}" | cut -f1)"
(( available_bytes + existing_bytes >= required_bytes + 20 * 1024 * 1024 * 1024 )) || {
  printf 'FATAL: insufficient disk space for checkpoint plus 20 GiB reserve.\n' >&2; exit 5; }
if [[ "${CHECK_ONLY}" == 1 ]]; then
  printf 'Preflight passed: %s at %s, %.2f GiB, destination %s\n' \
    "${REPO}" "${resolved_revision}" "$(awk -v n="${required_bytes}" 'BEGIN {print n/1073741824}')" "${DEST}"
  exit 0
fi

verify() {
  local path="$1" size="$2" sha="$3"
  [[ -f "${path}" && "$(stat -c %s -- "${path}")" == "${size}" ]] || return 1
  [[ "${sha}" == - || "$(sha256sum -- "${path}" | cut -d' ' -f1)" == "${sha}" ]]
}
printf 'Checkpoint download\n  repository : %s\n  revision   : %s\n  destination: %s\n' "${REPO}" "${resolved_revision}" "${DEST}"
fail=0
while IFS=$'\t' read -r name size sha; do
  [[ -n "${name}" ]] || continue
  output="${DEST}/${name}"; mkdir -p "$(dirname -- "${output}")"
  if verify "${output}" "${size}" "${sha}"; then printf '  ok    %s\n' "${name}"; continue; fi
  if [[ -f "${output}" && "$(stat -c %s -- "${output}")" == "${size}" ]]; then
    printf '  BAD   %s (SHA-256 mismatch; refetching)\n' "${name}" >&2; rm -f -- "${output}"
  fi
  printf '  get   %s (%.2f GiB)\n' "${name}" "$(awk -v n="${size}" 'BEGIN {print n/1073741824}')"
  curl -fL -C - --retry 5 --retry-delay 5 --retry-all-errors --no-progress-meter \
    "${AUTH_ARGS[@]}" -o "${output}" "${BASE_URL}/${name}" || { printf '  FAIL  %s\n' "${name}" >&2; fail=1; continue; }
  verify "${output}" "${size}" "${sha}" || { printf '  FAIL  %s (verification failed)\n' "${name}" >&2; fail=1; }
done <<< "${manifest}"
[[ "${fail}" == 0 ]] || { printf 'FINISHED WITH ERRORS -- rerun to resume.\n' >&2; exit 6; }

python3 - "${metadata_file}" "${DEST}/.qwen38-model-manifest.json" "${REPO}" "${resolved_revision}" <<'PY'
import json, sys
source, destination, repository, revision = sys.argv[1:]
remote = json.load(open(source))
result = {"schema_version": 1, "repository": repository, "revision": revision,
          "files": [{"path": x["rfilename"], "size": x.get("size") or 0,
                     "sha256": (x.get("lfs") or {}).get("sha256")}
                    for x in remote.get("siblings", []) if not x["rfilename"].startswith(".")]}
with open(destination, "w", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2); stream.write("\n")
PY
printf 'done -> %s (%s), revision %s\n' "${DEST}" "$(du -sh "${DEST}" | cut -f1)" "${resolved_revision}"
