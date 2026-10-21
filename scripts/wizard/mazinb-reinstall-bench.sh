#!/usr/bin/env bash
# Terminal B: only after separate M1 READY, behind m1-benchmark-lock.sh.
# No model start/stop, no systemd mutation, no implicit package install.
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
MODE="${1:---plan}"
[[ "$MODE" == --plan || "$MODE" == --run ]] || {
  echo 'MAZINB_R2_BENCH=BLOCKED_BAD_ACTION' >&2; exit 2;
}
MODEL="mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4"
PORT="http://127.0.0.1:18889/v1"
PINNED_BENCHY="0.4.1.dev1+ge9be34457"
UPSTREAM="e9be344578cec17745066b220798b80a0d2686d3"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/mazinb-m1-reinstall/active.json"
MODEL_ROOT="$ROOT_DIR/models/qwen3.8-flash-next-mazinb"
printf 'MAZINB_R2_BENCH_MODEL=%s\n' "$MODEL"
printf 'MAZINB_R2_BENCH_API=%s\n' "$PORT"
printf 'MAZINB_R2_BENCH_BENCHY_VERSION=%s\n' "$PINNED_BENCHY"
echo 'MAZINB_R2_BENCH_SHAPE=PP512_2048_TG128_C1_DEPTH0_WARMUP1_RUNS3'
echo 'MAZINB_R2_BENCH_READY=REQUIRES_LIVE_TERMINAL_A_M1_READY_FOR_BENCH'
if [[ "$MODE" == --plan ]]; then
  echo 'MAZINB_R2_BENCH=PLAN_ONLY_NO_API_OR_HOST_MUTATION'
  exit 0
fi
[[ "${QWEN38_M1_BENCH_LEASE_HELD:-0}" == 1 &&
   "${QWEN38_M1_BENCH_SLOT:-}" == reinstall && -t 0 ]] || {
  echo 'MAZINB_R2_BENCH=BLOCKED_WRAPPER_LEASE_OR_INTERACTIVE_TERMINAL_MISSING' >&2
  exit 2
}
[[ -d "$MODEL_ROOT" && -f "$MODEL_ROOT/config.json" &&
   ! -L "$MODEL_ROOT" && -f "$STATE" && ! -L "$STATE" ]] || {
  echo 'MAZINB_R2_BENCH=BLOCKED_CHECKPOINT_OR_JOURNAL_MISSING' >&2; exit 2;
}
command -v llama-benchy >/dev/null 2>&1 || {
  echo 'MAZINB_R2_BENCH=BLOCKED_PINNED_LLAMA_BENCHY_MISSING' >&2; exit 2;
}
version="$(llama-benchy --version 2>&1)" || {
  echo 'MAZINB_R2_BENCH=BLOCKED_BENCHY_VERSION_UNAVAILABLE' >&2; exit 2;
}
[[ "$version" == *"$PINNED_BENCHY"* ]] || {
  echo 'MAZINB_R2_BENCH=BLOCKED_UNPINNED_BENCHY_VERSION' >&2; exit 2;
}
help="$(llama-benchy --help 2>&1)" || {
  echo 'MAZINB_R2_BENCH=BLOCKED_BENCHY_HELP_UNAVAILABLE' >&2; exit 2;
}
for option in --base-url --model --tokenizer --pp --tg --depth --concurrency \
              --runs --warmup-runs --latency-mode --save-result --format; do
  [[ "$help" == *"$option"* ]] || {
    printf 'MAZINB_R2_BENCH=BLOCKED_CLI_FLAG_MISSING:%s\n' "$option" >&2; exit 2;
  }
done
mapfile -t provenance < <(python3 - "$STATE" "$MODEL" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
data = json.loads(p.read_text(encoding="utf-8"))
if data.get("phase") != "ready_for_bench" or data.get("model") != sys.argv[2]:
    raise SystemExit(2)
print(data["source_sha"])
print(pathlib.Path(data["release"]).name)
PY
)
[[ "${#provenance[@]}" == 2 &&
   "${provenance[0]}" =~ ^[a-f0-9]{40}$ &&
   "${provenance[1]}" =~ ^[a-f0-9]{40}$ ]] || {
  echo 'MAZINB_R2_BENCH=BLOCKED_UNTRUSTED_SOURCE_OR_RELEASE_SHA' >&2; exit 2;
}
source_sha="${provenance[0]}"
release_sha="${provenance[1]}"
[[ "$(git -C "$ROOT_DIR" rev-parse HEAD)" == "$source_sha" &&
   -z "$(git -C "$ROOT_DIR" status --porcelain=v1)" ]] || {
  echo 'MAZINB_R2_BENCH=BLOCKED_SOURCE_DRIFT' >&2; exit 2;
}
BASE="$HOME/Workspace/llm/qwen38-m1-bench-results"
[[ -d "$BASE" && ! -L "$BASE" ]] || {
  echo 'MAZINB_R2_BENCH=BLOCKED_OUTPUT_PARENT_ABSENT_OR_SYMLINK' >&2; exit 2;
}
umask 077
OUT="$(mktemp -d "$BASE/mazinb-r2-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXXXX")"
printf 'MAZINB_R2_BENCH_EVIDENCE_DIR=%s\n' "$OUT"
llama-benchy \
  --base-url "$PORT" \
  --model "$MODEL" \
  --tokenizer "$MODEL_ROOT" \
  --pp 512 2048 --tg 128 --depth 0 \
  --concurrency 1 --runs 3 --warmup-runs 1 \
  --latency-mode generation \
  --save-result "$OUT/mazinb.json" --format json
python3 -B "$ROOT_DIR/scripts/benchmark/llama-benchy-report.py" \
  --profile mazinb --input "$OUT/mazinb.json" \
  --output "$OUT/mazinb-report.md" --expected-model "$MODEL" \
  --source-sha "$source_sha" --release-sha "$release_sha" \
  --upstream-sha "$UPSTREAM"
(cd -- "$OUT" && sha256sum -- mazinb.json mazinb-report.md > SHA256SUMS &&
   sha256sum -c SHA256SUMS)
echo 'MAZINB_R2_BENCH=RAW_SAVED_CHECKSUMS_PASS_AWAIT_WRAPPER_POST_ADMISSION'
echo 'MAZINB_R2_OFF_HOST_BACKUP=REQUIRED_NOT_PERFORMED'
