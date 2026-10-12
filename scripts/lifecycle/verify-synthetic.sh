#!/usr/bin/env bash
# Exact-SHA synthetic-only lifecycle tests for a checked-out repository.
# Intentionally NO fetch/pull/install/uninstall/host doctor or daemon action.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
EXPECTED="${1:-}"
MODE="${2:-}"
BRANCH="feat/h38-managed-integration"

invalid() {
  printf 'LOCAL_SYNTHETIC_PREFLIGHT=INVALID reason=%s\n' "$*" >&2
  exit 2
}

if [[ "${EXPECTED}" == --help || "${EXPECTED}" == -h ]]; then
  printf 'Usage: bash scripts/lifecycle/verify-synthetic.sh EXACT_40_CHAR_SHA [--ci]\n'
  printf 'Checks an already-synchronized clean checkout; runs only isolated tests.\n'
  exit 0
fi

[[ "$#" -ge 1 && "$#" -le 2 ]] || invalid 'expected_sha_and_optional_ci_only'
[[ "${EXPECTED}" =~ ^[0-9a-f]{40}$ ]] || invalid 'exact_sha_required'
[[ -z "${MODE}" || "${MODE}" == --ci ]] || invalid 'unknown_argument'
if [[ "${MODE}" == --ci ]]; then
  [[ "${GITHUB_ACTIONS:-}" == true ]] || invalid 'ci_flag_requires_github_actions'
fi

for command in git bash python3 mktemp; do
  command -v "$command" >/dev/null 2>&1 || invalid "required_command_missing:$command"
done
[[ "$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null)" == "$ROOT" ]] ||
  invalid 'not_a_repository_checkout'
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$EXPECTED" ]] ||
  invalid 'checkout_sha_mismatch'

if [[ "$MODE" != --ci ]]; then
  [[ "$(git -C "$ROOT" branch --show-current)" == "$BRANCH" ]] ||
    invalid 'unexpected_branch'
  TRACKING="$(git -C "$ROOT" rev-parse --verify "refs/remotes/origin/$BRANCH" 2>/dev/null)" ||
    invalid 'origin_tracking_branch_missing'
  [[ "$TRACKING" == "$EXPECTED" ]] || invalid 'remote_tracking_sha_mismatch'
fi

[[ -z "$(git -C "$ROOT" status --porcelain=v1 --untracked-files=all)" ]] ||
  invalid 'dirty_checkout'

# No host state is read or modified. Even accidental host-command calls in a
# regression test are denied by PATH, while tests may create higher-priority
# stub commands under their own disposable fixture trees.
sandbox="$(mktemp -d "${TMPDIR:-/tmp}/qwen38-synthetic-check.XXXXXXXX")" ||
  invalid 'sandbox_creation_failed'
trap 'rm -rf -- "$sandbox"' EXIT
mkdir -p -- "$sandbox/home" "$sandbox/state" "$sandbox/data" "$sandbox/tmp" "$sandbox/deny"

for blocked in docker sudo systemctl swapoff swapon mount umount nvidia-smi; do
  printf '#!/bin/sh\nprintf "DENIED_HOST_COMMAND=%s\\n" "%s" >&2\nexit 125\n' \
    "$blocked" "$blocked" >"$sandbox/deny/$blocked"
  chmod 0700 "$sandbox/deny/$blocked"
done

export HOME="$sandbox/home"
export XDG_STATE_HOME="$sandbox/state"
export XDG_DATA_HOME="$sandbox/data"
export TMPDIR="$sandbox/tmp"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1
export PATH="$sandbox/deny:$PATH"

printf 'LOCAL_SYNTHETIC_SCOPE=DISPOSABLE_FIXTURES_ONLY\n'
printf 'LOCAL_SYNTHETIC_HEAD=%s\n' "$EXPECTED"
printf 'LOCAL_SYNTHETIC_HOST_MUTATION=DENIED\n'
printf 'LOCAL_SYNTHETIC_LIVE_E2E=NOT_QUALIFIED\n'

cd -- "$ROOT"
bash -n install.sh uninstall.sh scripts/lifecycle/verify-synthetic.sh
printf 'BASH_SYNTAX=PASS\n'
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck --severity=error uninstall.sh scripts/lifecycle/verify-synthetic.sh
  printf 'SHELLCHECK=PASS\n'
else
  printf 'SHELLCHECK=SKIPPED_NOT_INSTALLED\n'
fi

for test_file in \
  test_uninstall_wizard_preview.py \
  test_asset_ownership.py \
  test_operation_lock.py \
  test_lifecycle_integration.py \
  test_managed_lifecycle_readonly_snapshot.py
do
  printf '\n=== SYNTHETIC_TEST=%s ===\n' "$test_file"
  python3 -m unittest discover -s tests -p "$test_file" -v
done

[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$EXPECTED" ]] ||
  invalid 'checkout_changed_during_test'
[[ -z "$(git -C "$ROOT" status --porcelain=v1 --untracked-files=all)" ]] ||
  invalid 'dirty_checkout_after_test'
printf '\nLOCAL_SYNTHETIC_RESULT=PASS\n'
printf 'LOCAL_SYNTHETIC_HEAD=%s\n' "$EXPECTED"
printf 'MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED\n'
