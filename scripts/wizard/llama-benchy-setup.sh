#!/usr/bin/env bash
# Install only the pinned llama-benchy source into a separate user venv.
# NEVER use from an active protected M1/GPU trial. No sudo, model or Docker mutations.
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
ACTION="${1:---plan}"
[[ "$#" -le 1 && ( "$ACTION" == --plan || "$ACTION" == --install ) ]] || {
  echo 'BENCHY_SETUP=BLOCKED_UNKNOWN_ACTION' >&2; exit 2;
}
PIN="e9be344578cec17745066b220798b80a0d2686d3"
VERSION="0.4.1.dev1+ge9be34457"
VENV="${HOME}/.local/share/qwen38-benchmark-tools/llama-benchy-${PIN:0:9}"
EXE="${VENV}/bin/llama-benchy"
echo "BENCHY_SETUP_ACTION=${ACTION}"
echo "BENCHY_SETUP_PINNED_SOURCE_SHA=${PIN}"
echo "BENCHY_SETUP_EXPECTED_VERSION=${VERSION}"
echo "BENCHY_SETUP_ISOLATED_PATH=${VENV}"
echo "BENCHY_SETUP_HOST_INSTALLATION=USER_VENV_ONLY_NOT_SYSTEM"
echo 'BENCHY_SETUP_MODEL_DOCKER_GPU_SERVICE_CHANGE=NONE'
if [[ "$ACTION" == --plan ]]; then
  echo 'BENCHY_SETUP=PLAN_ONLY_NO_NETWORK_OR_MUTATION'
  exit 0
fi
[[ -t 0 && "${QWEN38_BENCHY_SETUP_APPROVED:-0}" == 1 ]] || {
  echo 'BENCHY_SETUP=BLOCKED_INTERACTIVE_DEFAULT_NO_APPROVAL_REQUIRED' >&2
  exit 2
}
printf 'Type INSTALL_PINNED_BENCHY exactly (or press Enter to cancel): '
IFS= read -r confirm
[[ "$confirm" == INSTALL_PINNED_BENCHY ]] || {
  echo 'BENCHY_SETUP=BLOCKED_CONFIRMATION_NOT_MATCHED' >&2; exit 2;
}
for cmd in python3 git flock stat docker ss; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "BENCHY_SETUP=BLOCKED_MISSING_TOOL:${cmd}" >&2; exit 2;
  }
done
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
LOCK="${STATE}/operation.lock"
[[ -d "$STATE" && ! -L "$STATE" && -f "$LOCK" && ! -L "$LOCK" ]] || {
  echo 'BENCHY_SETUP=BLOCKED_EXISTING_LIFECYCLE_LOCK_MISSING' >&2; exit 2;
}
[[ "$(stat -c %u -- "$LOCK")" == "$(id -u)" ]] || {
  echo 'BENCHY_SETUP=BLOCKED_LIFECYCLE_LOCK_OWNER' >&2; exit 2;
}
exec {lock_fd}<"$LOCK"
if ! flock -n -x "$lock_fd"; then
  echo 'BENCHY_SETUP=BLOCKED_ACTIVE_LIFECYCLE_SHARED_OR_EXCLUSIVE_LOCK' >&2
  exit 3
fi
# Extra fail-closed check: active candidate could have lost its controller.
running="$(docker ps --format '{{.Names}}')" || {
  echo 'BENCHY_SETUP=BLOCKED_DOCKER_STATE_UNKNOWN' >&2; exit 2;
}
if grep -Eq '^qwen38-' <<<"$running"; then
  echo 'BENCHY_SETUP=BLOCKED_RUNNING_PROJECT_CONTAINER' >&2; exit 2;
fi
listeners="$(ss -H -ltn)" || {
  echo 'BENCHY_SETUP=BLOCKED_LISTENER_INSPECTION_FAILED' >&2; exit 2;
}
if awk '{print $4}' <<<"$listeners" | grep -Eq '(^|:|\])18889$'; then
  echo 'BENCHY_SETUP=BLOCKED_ACTIVE_M1_LOCALHOST_PORT' >&2; exit 2;
fi
[[ -z "$(git -C "$ROOT_DIR" status --porcelain=v1)" ]] || {
  echo 'BENCHY_SETUP=BLOCKED_PROJECT_DIRTY' >&2; exit 2;
}
if [[ -e "$VENV" || -L "$VENV" ]]; then
  [[ -f "$EXE" && -x "$EXE" && ! -L "$VENV" ]] || {
    echo 'BENCHY_SETUP=BLOCKED_EXISTING_UNVERIFIED_VENV' >&2; exit 2;
  }
else
  TOOLS_ROOT="$HOME/.local/share/qwen38-benchmark-tools"
  for dir in "$HOME/.local" "$HOME/.local/share" "$TOOLS_ROOT"; do
    [[ ! -L "$dir" ]] || {
      echo 'BENCHY_SETUP=BLOCKED_SYMLINKED_VENV_PARENT' >&2; exit 2;
    }
    if [[ -e "$dir" && ! -d "$dir" ]]; then
      echo 'BENCHY_SETUP=BLOCKED_NON_DIRECTORY_VENV_PARENT' >&2; exit 2;
    fi
    if [[ -d "$dir" && "$(stat -c %u -- "$dir")" != "$(id -u)" ]]; then
      echo 'BENCHY_SETUP=BLOCKED_VENV_PARENT_WRONG_OWNER' >&2; exit 2;
    fi
  done
  umask 077
  mkdir -p -- "$TOOLS_ROOT"
  python3 -m venv "$VENV" || {
    echo 'BENCHY_SETUP=BLOCKED_VENV_CREATION_FAILED_KEEP_PARTIAL_FOR_REVIEW' >&2; exit 2;
  }
  "$VENV/bin/python" -m pip install --no-input --disable-pip-version-check \
    "git+https://github.com/eugr/llama-benchy.git@${PIN}" || {
    echo 'BENCHY_SETUP=BLOCKED_PINNED_PIP_INSTALL_FAILED_KEEP_PARTIAL_FOR_REVIEW' >&2; exit 2;
  }
fi
version="$("$EXE" --version 2>&1)" || {
  echo 'BENCHY_SETUP=BLOCKED_VERSION_QUERY_FAILED' >&2; exit 2;
}
[[ "$version" == *"$VERSION"* ]] || {
  echo 'BENCHY_SETUP=BLOCKED_VERSION_MISMATCH' >&2; exit 2;
}
help="$("$EXE" --help 2>&1)" || {
  echo 'BENCHY_SETUP=BLOCKED_HELP_QUERY_FAILED' >&2; exit 2;
}
for flag in --base-url --model --tokenizer --pp --tg --depth --concurrency \
  --runs --warmup-runs --latency-mode --save-result --format; do
  [[ "$help" == *"$flag"* ]] || {
    echo "BENCHY_SETUP=BLOCKED_CLI_OPTION_ABSENT:${flag}" >&2; exit 2;
  }
done
"$VENV/bin/python" -m pip freeze --all > "$VENV/benchy-dependency-freeze.txt"
sha256sum -- "$VENV/benchy-dependency-freeze.txt" > "$VENV/benchy-dependency-freeze.sha256"
echo "BENCHY_SETUP_EXECUTABLE=$EXE"
echo "BENCHY_SETUP_VERSION=$version"
echo 'BENCHY_SETUP=PASS_PINNED_SOURCE_VENV_AND_CLI'
echo 'BENCHY_SETUP_REQUIRES_NEW_EXPLICIT_M1_TRIAL=YES'
