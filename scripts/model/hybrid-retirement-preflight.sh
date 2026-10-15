#!/usr/bin/env bash
# Read-only combined Hybrid retirement admission report. Never deletes assets.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
echo "=== LOCAL ARCHIVE CHECKSUMS ==="
python3 "${ROOT}/scripts/model/verify-hybrid-retirement-evidence.py" || {
  echo "HYBRID_RETIREMENT_PREFLIGHT=BLOCKED_LOCAL_EVIDENCE"
  exit 3
}
echo "=== EXACT SIX STOPPED CONTAINERS ==="
python3 "${ROOT}/scripts/model/hybrid-container-evidence.py" || {
  echo "HYBRID_RETIREMENT_PREFLIGHT=BLOCKED_DOCKER_IDENTITY"
  exit 3
}
echo "=== H3-H6 REFERENCE CLOSURE ==="
blocked=0
for stage in qwen3.8-hybrid-quant-layout qwen3.8-h4-orca-all qwen3.8-h5-neutral-input-scale qwen3.8-h6-modelopt-w4a16; do
  if bash "${ROOT}/scripts/model/hybrid-retirement-audit.sh" "${ROOT}/models/${stage}"; then
    echo "STAGE_REFERENCES=ZERO ${stage}"
  else
    echo "STAGE_REFERENCES=BLOCKED ${stage}"
    blocked=1
  fi
done
echo "OFF_HOST_BACKUP=NOT_VERIFIED"
echo "HYBRID_RETIREMENT_DELETE=NOT_AUTHORIZED"
if [[ "${blocked}" == 1 ]]; then
  echo "HYBRID_RETIREMENT_PREFLIGHT=BLOCKED_REFERENCES"
  exit 3
fi
echo "HYBRID_RETIREMENT_PREFLIGHT=INVENTORY_ONLY"
