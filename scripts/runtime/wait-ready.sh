#!/usr/bin/env bash
set -Eeuo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:8888}"
CONTAINER="${CONTAINER:-qwen38-flash-next}"
MODEL="${MODEL:-}"
TIMEOUT="${TIMEOUT:-1800}"
INTERVAL="${INTERVAL:-10}"
LOG_TAIL="${LOG_TAIL:-20}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/wait-ready.sh [--container NAME] [--model MODEL_ID] [--timeout SEC] [--interval SEC] [--base-url URL]

Checks container state, /health, and /v1/models. Exits only after the runtime is
healthy and, when --model is supplied, that exact served-model ID is present.
Defaults: container=qwen38-flash-next, base-url=http://127.0.0.1:8888,
timeout=1800, interval=10.
EOF
}
die() { printf 'ERROR: %s\n' "$*" >&2; exit 2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --container) [[ $# -ge 2 ]] || die "--container requires a value"; CONTAINER="$2"; shift ;;
    --model) [[ $# -ge 2 ]] || die "--model requires a value"; MODEL="$2"; shift ;;
    --timeout) [[ $# -ge 2 ]] || die "--timeout requires seconds"; TIMEOUT="$2"; shift ;;
    --interval) [[ $# -ge 2 ]] || die "--interval requires seconds"; INTERVAL="$2"; shift ;;
    --base-url) [[ $# -ge 2 ]] || die "--base-url requires a URL"; BASE_URL="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done

[[ "${TIMEOUT}" =~ ^[1-9][0-9]*$ ]] || die "--timeout must be a positive integer"
[[ "${INTERVAL}" =~ ^[1-9][0-9]*$ ]] || die "--interval must be a positive integer"
[[ "${BASE_URL}" =~ ^http://(127\.0\.0\.1|localhost|\[::1\]):[0-9]+/?$ ]] || die "--base-url must be loopback HTTP with an explicit port"
command -v docker >/dev/null 2>&1 || die "docker is required"
command -v curl >/dev/null 2>&1 || die "curl is required"

started="$(date +%s)"
next_report=0
while :; do
  now="$(date +%s)"; elapsed=$((now - started))
  if (( elapsed >= TIMEOUT )); then
    printf 'TIMEOUT after %ss waiting for %s\n' "${elapsed}" "${CONTAINER}" >&2
    docker logs --tail "${LOG_TAIL}" "${CONTAINER}" 2>&1 || true
    exit 1
  fi

  state="$(docker inspect --format '{{.State.Status}}' "${CONTAINER}" 2>/dev/null || true)"
  if [[ -n "${state}" && "${state}" != running ]]; then
    printf 'CONTAINER STOPPED: %s status=%s\n' "${CONTAINER}" "${state}" >&2
    docker logs --tail "${LOG_TAIL}" "${CONTAINER}" 2>&1 || true
    exit 1
  fi

  healthy=0; models_json=""
  if curl -fsS --max-time 3 "${BASE_URL%/}/health" >/dev/null 2>&1; then
    healthy=1
    models_json="$(curl -fsS --max-time 5 "${BASE_URL%/}/v1/models" 2>/dev/null || true)"
  fi

  model_ok=1
  if [[ -n "${MODEL}" ]]; then
    model_ok=0
    if [[ -n "${models_json}" ]]; then
      if MODELS_JSON="${models_json}" python3 - "${MODEL}" <<'PY' >/dev/null 2>&1
import json, os, sys
wanted = sys.argv[1]
data = json.loads(os.environ["MODELS_JSON"])
ids = [x.get("id") for x in data.get("data", []) if isinstance(x, dict)]
raise SystemExit(0 if wanted in ids else 1)
PY
      then model_ok=1; fi
    fi
  fi

  if (( healthy == 1 && model_ok == 1 )); then
    printf 'READY after %ss: %s %s\n' "${elapsed}" "${CONTAINER}" "${BASE_URL%/}"
    [[ -z "${models_json}" ]] || printf '%s\n' "${models_json}"
    exit 0
  fi

  if (( elapsed >= next_report )); then
    printf 'waiting... %s/%ss container=%s health=%s model=%s\n' "${elapsed}" "${TIMEOUT}" "${state:-missing}" "$([[ "${healthy}" == 1 ]] && printf ready || printf waiting)" "$([[ "${model_ok}" == 1 ]] && printf ready || printf waiting)"
    docker logs --tail 3 "${CONTAINER}" 2>&1 || true
    next_report=$((elapsed + 60))
  fi
  sleep "${INTERVAL}"
done
