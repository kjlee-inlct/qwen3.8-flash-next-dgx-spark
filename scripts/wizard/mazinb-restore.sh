#!/usr/bin/env bash
# Wizard-owned checkpoint restore only; never mutate the installed OrcaRouter.
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
ACTION="${1:-}"
[[ "$ACTION" == preflight || "$ACTION" == apply ]] || {
  printf 'MAZINB_RESTORE=BLOCKED_BAD_ACTION\n' >&2; exit 2;
}
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env"
MODEL_ROOT="$ROOT_DIR/models"
TARGET="$MODEL_ROOT/qwen3.8-flash-next-mazinb"
REPO_PIN="mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4"
SHA_PIN="f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f"
[[ -f "$STATE" && ! -L "$STATE" && -d "$MODEL_ROOT" && ! -L "$MODEL_ROOT" ]] || {
  echo 'MAZINB_RESTORE=BLOCKED_MANIFEST_OR_MODEL_ROOT_UNSAFE' >&2; exit 2;
}
python3 - "$ROOT_DIR" "$STATE" "$MODEL_ROOT" <<'PY'
import pathlib, sys
repo, state, root = map(pathlib.Path, sys.argv[1:])
sys.path.insert(0, str(repo / "scripts/lib"))
from state_file import parse_install
d = parse_install(state, "install-maintenance")
if d.get("PHASE") != "complete" or d.get("MODEL_PROFILE") != "orcarouter":
    raise SystemExit("MAZINB_RESTORE=BLOCKED_EXPECTED_ORCAROUTER_INSTALL")
if d.get("SERVICE_ENABLED") != "0":
    raise SystemExit("MAZINB_RESTORE=BLOCKED_MANAGED_SERVICE_MUST_BE_DISABLED")
model = pathlib.Path(d.get("MODEL_DIR") or "")
if not model.is_absolute() or model.resolve().parent != root.resolve():
    raise SystemExit("MAZINB_RESTORE=BLOCKED_MANAGED_MODEL_ROOT_MISMATCH")
print("MAZINB_RESTORE_MANAGED_PREDECESSOR=ORCAROUTER_DISABLED")
PY
python3 -B "$ROOT_DIR/scripts/diagnostics/verify-managed-idle.py" || {
  echo 'MAZINB_RESTORE=BLOCKED_MANAGED_HOST_NOT_IDLE' >&2; exit 2;
}
[[ ! -L "$TARGET" ]] || { echo 'MAZINB_RESTORE=BLOCKED_SYMLINK_TARGET' >&2; exit 2; }
if [[ -e "$TARGET" ]]; then
  [[ -d "$TARGET" ]] || { echo 'MAZINB_RESTORE=BLOCKED_NON_DIRECTORY_TARGET' >&2; exit 2; }
  if [[ -e "$TARGET/.qwen38-model-manifest.json" || -L "$TARGET/.qwen38-model-manifest.json" ]]; then
    python3 - "$TARGET/.qwen38-model-manifest.json" "$REPO_PIN" "$SHA_PIN" <<'PY'
import json, os, pathlib, stat, sys
path, repo, sha = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
st = path.lstat()
if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_size > 1048576:
    raise SystemExit("MAZINB_RESTORE=BLOCKED_MODEL_MANIFEST_UNSAFE")
data = json.loads(path.read_text())
if data.get("repository") != repo or data.get("revision") != sha:
    raise SystemExit("MAZINB_RESTORE=BLOCKED_MODEL_REVISION_DRIFT")
PY
  elif [[ -n "$(find "$TARGET" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    echo 'MAZINB_RESTORE=BLOCKED_NONEMPTY_UNATTESTED_DESTINATION' >&2; exit 2;
  fi
fi
export MODEL_PROFILE=mazinb REPO="$REPO_PIN" REVISION="$SHA_PIN"
export MODELS_DIR="$MODEL_ROOT" QWEN38_MODEL_ROOT="$MODEL_ROOT"
printf 'MAZINB_RESTORE_PINNED_REPO=%s\n' "$REPO_PIN"
printf 'MAZINB_RESTORE_PINNED_REVISION=%s\n' "$SHA_PIN"
printf 'MAZINB_RESTORE_TARGET=%s\n' "$TARGET"
bash "$ROOT_DIR/scripts/download-weights.sh" --candidate --check || {
  echo 'MAZINB_RESTORE=BLOCKED_METADATA_OR_DISK_ADMISSION' >&2; exit 2;
}
if [[ "$ACTION" == preflight ]]; then
  echo 'MAZINB_RESTORE_PREFLIGHT=PASS_READ_ONLY_NO_WEIGHT_DOWNLOAD'
  echo 'MAZINB_RESTORE_DOCKER_GPU_SERVICE_ACTION=NONE'
  exit 0
fi
[[ "${QWEN38_MAZINB_RESTORE_APPROVED:-0}" == 1 && -t 0 ]] || {
  echo 'MAZINB_RESTORE=BLOCKED_WIZARD_INTERACTIVE_APPROVAL_MISSING' >&2; exit 2;
}
# Hold the existing managed lifecycle lock throughout the potentially long transfer.
# This is an explicit owner-approved mutation, never part of the preflight.
source "$ROOT_DIR/scripts/lib/operation-lock.sh"
acquire_operation_lock "$(dirname -- "$STATE")" "pinned mazinb checkpoint restore" || {
  echo 'MAZINB_RESTORE=BLOCKED_LIFECYCLE_LOCK' >&2; exit 2;
}
python3 -B "$ROOT_DIR/scripts/diagnostics/verify-managed-idle.py" || {
  echo 'MAZINB_RESTORE=BLOCKED_HOST_DRIFT_AFTER_LOCK' >&2; exit 2;
}
echo 'MAZINB_RESTORE_DOWNLOAD=EXPLICITLY_APPROVED'
echo 'MAZINB_RESTORE_NOTE=Temporary CPU-only Docker download helper possible; no GPU/inference'
bash "$ROOT_DIR/scripts/download-weights.sh" --candidate || {
  echo 'MAZINB_RESTORE=FAILED_OR_PARTIAL_TRANSFER_CAN_RESUME_AFTER_RECHECK' >&2; exit 2;
}
echo 'MAZINB_RESTORE_DOWNLOAD=COMPLETE_DOWNLOADER_VERIFIED'
echo 'MAZINB_RESTORE_GPU_START=NOT_PERFORMED'
