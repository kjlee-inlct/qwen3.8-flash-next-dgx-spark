#!/usr/bin/env bash
# Real-DGX wizard read-only checks. NO service/model/container/disk mutation.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "$BASH_SOURCE")/../.." && pwd -P)"
TARGET="$(printenv QWEN38_WIZARD_AUDIT_TARGET_SHA 2>/dev/null || true)"
STATE_HOME="$HOME/.local/state"
DATA_HOME="$HOME/.local/share"
if [[ -n "$(printenv XDG_STATE_HOME 2>/dev/null || true)" ]]; then STATE_HOME="$XDG_STATE_HOME"; fi
if [[ -n "$(printenv XDG_DATA_HOME 2>/dev/null || true)" ]]; then DATA_HOME="$XDG_DATA_HOME"; fi
MANIFEST="$STATE_HOME/qwen38-spark/install.env"
OWNERSHIP="$STATE_HOME/qwen38-spark/asset-ownership.json"
CURRENT="$DATA_HOME/qwen38-spark/current"

abort() { printf 'WIZARD_DGX_PREFLIGHT=INVALID reason=%s\n' "$*" >&2; exit 2; }
[[ "$#" -eq 0 ]] || abort unexpected_arguments
[[ "$TARGET" =~ ^[0-9a-f]{40}$ ]] || abort exact_sha_required
command -v git >/dev/null 2>&1 || abort git_missing
command -v python3 >/dev/null 2>&1 || abort python_missing
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$TARGET" ]] || abort sha_mismatch
[[ -z "$(git -C "$ROOT" status --porcelain=v1 --untracked-files=all)" ]] ||
  abort dirty_checkout
for file in "$ROOT/install.sh" "$ROOT/uninstall.sh" \
  "$ROOT/scripts/lifecycle/inspect-selected-profile.py"; do
  [[ -r "$file" ]] || abort missing_script
done
for file in "$MANIFEST" "$OWNERSHIP"; do
  [[ ! -L "$file" ]] || abort symlinked_state_file
done
export PYTHONDONTWRITEBYTECODE=1

fingerprint() {
  if [[ -f "$1" ]]; then sha256sum -- "$1" | awk '{print $1}'
  elif [[ -e "$1" ]]; then printf 'NOT_REGULAR\n'
  else printf 'ABSENT\n'
  fi
}
manifest_before="$(fingerprint "$MANIFEST")"
ownership_before="$(fingerprint "$OWNERSHIP")"
release_before="$(readlink -- "$CURRENT" 2>/dev/null || printf ABSENT)"

printf 'WIZARD_DGX_READONLY=BEGIN\n'
printf 'CHECKOUT_SHA=%s\n' "$TARGET"
printf 'MANIFEST_SHA_BEFORE=%s\nOWNERSHIP_SHA_BEFORE=%s\n' \
  "$manifest_before" "$ownership_before"
printf 'CURRENT_LINK_BEFORE=%s\n' "$release_before"
printf 'HOST_MUTATION=NO\nMODEL_START=NO\nINSTALL_UNINSTALL_PURGE=NO\n'
overall=0
check() {
  local name="$1" rc=0
  shift
  printf '\n=== %s ===\n' "$name"
  "$@" || rc="$?"
  printf 'WIZARD_CHECK=%s rc=%s\n' "$name" "$rc"
  if [[ "$rc" -ne 0 ]]; then overall=1; fi
}
check model_inventory bash "$ROOT/install.sh" --list-models
check backend_inventory bash "$ROOT/install.sh" --list-backends
check selected_profile_readonly python3 -B \
  "$ROOT/scripts/lifecycle/inspect-selected-profile.py"

if [[ -f "$MANIFEST" ]] && grep -qx 'PHASE=complete' "$MANIFEST"; then
  for target in orcarouter nvidia mazinb orcarouter-hybrid; do
    check "installer_$target-dry-run" \
      bash "$ROOT/install.sh" --lang en --model "$target" \
      --yes --no-start --dry-run
  done
  check uninstall_preserve_dry_run bash "$ROOT/uninstall.sh" \
    --lang en --yes --dry-run
  check uninstall_full_purge_preview_only bash "$ROOT/uninstall.sh" \
    --lang en --yes --dry-run --purge-all
else
  printf 'WIZARD_INSTALLED_PREVIEWS=SKIPPED_MANIFEST_NOT_COMPLETE\n'
  overall=1
fi

for pattern in test_wizard_ui.py test_wizard_menu_validation.py \
  test_installer_profile_manager.py test_uninstall_wizard_preview.py \
  test_lychee888_metadata.py; do
  check "fixture_$pattern" python3 -B -m unittest discover \
    -s "$ROOT/tests" -p "$pattern" -q
done

manifest_after="$(fingerprint "$MANIFEST")"
ownership_after="$(fingerprint "$OWNERSHIP")"
release_after="$(readlink -- "$CURRENT" 2>/dev/null || printf ABSENT)"
printf '\nMANIFEST_SHA_AFTER=%s\nOWNERSHIP_SHA_AFTER=%s\n' \
  "$manifest_after" "$ownership_after"
printf 'CURRENT_LINK_AFTER=%s\n' "$release_after"

if [[ "$manifest_before" != "$manifest_after" ||
      "$ownership_before" != "$ownership_after" ||
      "$release_before" != "$release_after" ]]; then
  printf 'WIZARD_DGX_READONLY=STATE_DRIFT_DETECTED\n' >&2
  exit 4
fi
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$TARGET" ]] ||
  abort checkout_changed
[[ -z "$(git -C "$ROOT" status --porcelain=v1 --untracked-files=all)" ]] ||
  abort checkout_dirty_after
if [[ "$overall" -ne 0 ]]; then
  printf 'WIZARD_DGX_READONLY=PARTIAL_CHECK_FAILURE\nM1_LIVE=NOT_QUALIFIED\n'
  exit 3
fi
printf 'WIZARD_DGX_READONLY=PREVIEW_AND_FIXTURES_PASS\n'
printf 'M1_LIVE=NOT_QUALIFIED\nM2_DESTRUCTIVE=NOT_RUN\n'
printf 'M3_LIVE_PAIRS=NOT_QUALIFIED\nM4_H38=BLOCKED\n'
printf 'D0_DISPOSABLE=NOT_GRANTED\n'
