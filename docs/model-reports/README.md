# Per-model llama-benchy reports — reproducible single-DGX benchmark protocol

## 2026-10-14: actual mazinb benchmark MEASURED

Using a single DGX Spark, vLLM v0.29 experimental runtime and 16-GiB KV:
[mazinb results](mazinb.md) and
[original JSON/Markdown/SHA256](evidence/mazinb/20261014T015805Z/).
TG128: **23.11 ± 1.05 tok/s (PP512)** and
**22.54 ± 1.68 tok/s (PP2048)**. All other profiles and mazinb
Legacy comparison remain NOT_MEASURED. Statements below that every
profile is NOT_MEASURED are historical snapshots predating the M1 result.
The physical M1 shutdown journal was successfully reconciled to `stopped`
without Docker mutation. DGX independently SHA256-verified all three archived
measurement payloads (`smoke.json`, `mazinb.json`, `mazinb-report.md`) against
this repository on 2026-10-14. The original local absolute-path checksum
manifest differs from the relative-path GitHub archival manifest (436 vs
238 bytes), but all three data hashes match. Keep the original 36-KiB output
folder and the two journal backups. Long-term host stability remains
**INCONCLUSIVE**. See [M1 guide](../MAZINB-M1-WIZARD.md) and
[physical evidence](../../scripts/benchmark/evidence/dgx-mazinb-m1-journal-reconcile-physical-20261014.md).


## OrcaRouter A/B trial wizard implementation — SOURCE ONLY (2026-10-13)

**Progress since A/B preview:** A separate, experimental installed-setup
**menu 6** now offers **status / start Legacy / start v0.29 / stop**,
plus a plan-only response under `./install.sh --dry-run`.
A fresh DGX Spark OS with working NVIDIA driver/Docker/Git/Python/curl/sudo
still uses `./install.sh` to select v0.29 (default) or press
`L` (Legacy), automatically download pinned checkpoint and
locally build the selected runtime image if absent. These are
distinct workflows: neither is a pretext to change the existing
managed manifest, immutable release or stopped predecessor.

The A/B trial is **source-implemented but NOT ACTUAL_DGX
qualified**. Safety boundary: interactive choice and explicit
old Docker ID confirmation; shared lifecycle lock; complete
OrcaRouter manifest; service inactive; no conflicting lifecycle
transaction; protected predecessor exact 64-character ID,
`exited`, non-OOM and unchanged; original release and manifest
SHA retained; present pinned checkpoint/config/image; swap and
non-CMA memory margins; exclusive localhost trial API 18888.

Launch uses a new `qwen38-ab-legacy` or `qwen38-ab-v029`
container with immutable predecessor/variant labels, initially
**docker create, not start**; a separately persisted state
watchdog must be **armed to that exact Docker ID** before the
trial can be started. The watchdog uses its own stop journal and
non-CMA/swap monitoring. Failure/stop targets only the exact new
trial ID; Docker container/logs are preserved for evidence.
After stopping A, B can start only if A is cleanly stopped with
proper provenance. Neither trial changes installed image,
manifest, service, old Docker object or release pointer.
Ref: [isolated trial source runbook](DGX-ORCAROUTER-AB-ISOLATED-TRIAL.md).

**Crucial:** A successful GitHub Python/ShellCheck CI tests
source and synthetic mocks, NOT actual GPU load, model READY,
NVIDIA RM correctness, stability or benchmark. No actual
model start, pause or deletion has been performed in this chat.
The host's earlier read-only OrcaRouter wizard dry-run remains
the only verified physical wizard event. A/B results,
raw llama-benchy JSON/Markdown/SHA256 and off-host backup
remain **NOT_MEASURED/NOT_CAPTURED**. Before live use,
conduct an owner-approved exact-SHA read-only menu 6 preview,
check all host prerequisites and watchdog behavior; any
physical launch is a separate explicit operator decision.
OrcaRouter deletion HOLD applies **only during this test**,
not permanently. PR #259 remains Draft/Open/Unmerged.


## OrcaRouter legacy / v0.29 A/B wizard plan staged (2026-10-13)

**Owner's new choice:** do not decide the final runtime image from source inspection alone. Benchmark **both** `vllm-skinny-tp1:v1` (legacy CPU-offload) and `vllm-orcarouter-v029:v1` (official vLLM v0.29 + PLE mmap/GB10 FLA/exact QSA) **sequentially** on the same OrcaRouter checkpoint/revision and a **16 GiB KV cache** starting point. These represent whole-runtime differences, not an image-only isolation. Measure actual load/READY, TTFT/TTFR, PP/TG, concurrency, failure rate and strict NVIDIA RM/non-CMA/swap stability with the same pinned `llama-benchy` workload, separate cold/warm repeats and preserved JSON/Markdown/SHA256/off-host backup. Prefer a stable image only **after** real qualification; both reports are NOT_MEASURED.

**Source implementation** at `394805e62999186afd56d085f279d87f4e4742af` (GitHub workflow pending at the time of documentation): A *newly provisioned DGX Spark OS with functional NVIDIA GPU/Docker* can use `./install.sh` to choose OrcaRouter baseline **v0.29** (provisional new-install default), or press **L** for Legacy; image builds locally if absent and the wizard handles pinned checkpoint download, compatible config, 128 GiB PLE swap, immutable release/service, monitor/protect (fresh OrcaRouter defaults enabled). The normalized equivalent CLI `--orcarouter-runtime legacy` reproduces L, only on fresh OrcaRouter installations. Missing OS/GPU driver/Docker/network prerequisites are **not** silently installed. Full real empty-host online installation has NOT_RUN.

**Existing protected DGX:** `./install.sh` → management menu **5** is a **read-only A/B plan preview**; **4 still cancels**. The installed legacy `vllm-skinny-tp1:v1` manifest/release and historical stopped Docker exact ID are never silently migrated or removed. The preview explicitly prints `WIZARD_ISOLATED_START=NOT_IMPLEMENTED`, no live API or RM acceptance, no benchmark. Actual dual-image isolated wizard launch/stop and exact-ID host safety is **NOT IMPLEMENTED**; never use direct experiment start or `systemctl restart` as a bypass. H38 is separately gated, not the fresh default. See [A/B comparison protocol](DGX-ORCAROUTER-AB-BENCHMARK.md) and [isolated trial design](DGX-ORCAROUTER-WIZARD-TRIAL-DESIGN.md). OrcaRouter checkpoint deletion is held **only for this test**; later review requires explicit approval and benchmark backups. PR #259 stays Draft/Open/Unmerged.


## Actual OrcaRouter wizard preview PASS; no llama-benchy result yet (2026-10-13)

Real DGX interactive existing-install `--dry-run` successfully selected OrcaRouter and showed legacy image `vllm-skinny-tp1:v1`, monitor/protect enabled, `WIZARD_DRY_RUN_RC=0`, original Docker/manifest unchanged. [Exact physical evidence](../../scripts/benchmark/evidence/dgx-orcarouter-wizard-actual-dry-run-20261013.md). No v0.29 experimental or legacy model was started and the `active` registry label is manifest-only, NOT actual serving. Terminal B must wait for a safe approved wizard-contained isolated M1 live trial, served-model API identity and RM/host stability. All five model reports NOT_MEASURED; OrcaRouter checkpoint deletion held only during this test.


## OrcaRouter first; temporary no-delete during this measurement campaign (2026-10-13)

Owner correction: measure OrcaRouter **first**, and do not
delete its checkpoint **during this test**. This rule does
not exclude the checkpoint from **future** selective
reclamation once the experiment is completed, raw measured
JSON/report/SHA256 plus separately verified backup are kept,
dependencies and recovery are analyzed, and the owner
explicitly approves a wizard-mediated cleanup. An
unmeasurable model requires a documented authorized exception;
missing measurements must never become invented numbers.
All five profiles currently remain NOT_MEASURED.
A successful stopped v0.29 preflight RC=0 does not mean
API READY. Terminal A activates only through the
qualified wizard, Terminal B benchmarks with
`with-wizard-lock.sh` only after M1 host/RM acceptance.

## Two-terminal wizard activation prerequisite (2026-10-13)

Per the owner, actual model install/switch/uninstall belongs in
the interactive wizard in **Terminal A**. Real llama-benchy
measurements belong in **Terminal B** but only on the model
previously activated in the wizard and separately verified healthy,
API-served-name-correct, and host/RM-safe.
[Authoritative workflow](../DGX-TWO-TERMINAL-WIZARD-BENCHMARK.md).
A cannot mutate lifecycle or delete model/Docker while B measures.
The upstream benchmark is not automatically serialized with the
wizard's operation lock; an explicit verified lock/admission
mechanism is a remaining implementation task.
ACTUAL_DGX preflight RC=0 for OrcaRouter v0.29 is a **stopped model**
observation, not live readiness. Keep all five cards NOT_MEASURED.
No checkpoint or image may be deleted before a real report +
independently verified off-host backup and separate owner approval.


## Physical S4 link closure done; five benchmark profiles still unmeasured (2026-10-13)

[S4 actual-DGX evidence](../../scripts/benchmark/evidence/dgx-hybrid-all-link-closure-readonly-20261013.md)
resolved all 319 Hybrid symlinks and recorded ext4/free space without
any runtime start or API benchmark. **All five profile reports
NOT_MEASURED**. S1–S4 storage/link audits are complete. The next
step is **separate approval for safely isolated legacy M1 live
readiness**, then real pinned llama-benchy raw JSON and derived
report with independently verified SHA256 copies. Missing local
NVIDIA/lychee888 weights cannot be benchmarked without future model
availability. No throughput or deletion permission inferred.


## Physical S3 is not a llama-benchy measurement (2026-10-13)

[Actual DGX S3](../../scripts/benchmark/evidence/dgx-hybrid-runtime-references-readonly-20261013.md) confirmed virtual shard-reference resolution only (`REFERENCE_GAPS=0`). It did not send API requests, load models or generate raw performance JSON. **All five per-model reports remain NOT_MEASURED**. Do not delete H3/H4 based on H6 index integrity; benchmark and dependency/ownership guards still apply.


## S2 is filesystem evidence, not llama-benchy throughput (2026-10-13)

[Actual DGX S2](../../scripts/benchmark/evidence/dgx-hybrid-block-accounting-readonly-20261013.md) measured allocation/hardlink/symlink counts only. It did **not** start the model API or generate a llama-benchy JSON. All five templates remain `NOT_MEASURED`; H3/H4 are intermediate artifacts, not independent selectable benchmark profiles. Do not infer permission to delete the parents from a future H6 throughput result.


**Status 2026-10-13: templates created; NO NEW MODEL THROUGHPUT HAS BEEN MEASURED.**
The only actual DGX observations currently relevant are A5 dry-run (PASS),
lychee888 L0 pinned remote-index (PASS), and B5 stopped legacy prestart
(PASS). The model API is stopped. Historical benchmark measurements in
other evidence documents are separate and must not be silently copied
into these new per-model reports.

## External reference and pinned source

- Upstream: [eugr/llama-benchy](https://github.com/eugr/llama-benchy), MIT licensed.
- Upstream commit reviewed (2026-10-13): [`e9be344578cec17745066b220798b80a0d2686d3`](https://github.com/eugr/llama-benchy/commit/e9be344578cec17745066b220798b80a0d2686d3)
  (July 10, 2026; pinned for review/reproducibility).
- Upstream CLI currently benchmarks OpenAI-compatible
  `/v1/chat/completions`, not offline model files or a stopped API.
- Captures PP prompt-processing tok/s, TG generation tok/s,
  token output peak, TTFR, estimated prompt processing latency,
  end-to-end TTFT and concurrency 1/2. JSON includes source
  version, timestamp and per-test dimensions/results.
- Benchmark text comes from a book; upstream can download it from
  Gutenberg, and tokenizer loading may access the network.
  Never describe the benchmark as offline unless both the corpus and
  tokenizer are explicitly supplied/verified. No automatic package,
  model or book download is part of installing the project's wizard.
- `--latency-mode generation` measures generation-based overhead;
  `--exact-tg` optionally forces fixed output via vLLM extensions.
  Cache policy, prompt corpus, tokenizer and effective model
  revision must be controlled to fairly compare candidates.

## Model report registry — do not invent results

| Profile | Current actual DGX knowledge | Benchy report |
|---|---|---|
| [orcarouter](orcarouter.md) | checkpoint installed, old runtime STOPPED; M1 live NOT_QUALIFIED | NOT_MEASURED |
| [nvidia](nvidia.md) | checkpoint and image ABSENT on 2026-10-13 A5 inventory | NOT_MEASURED |
| [mazinb](mazinb.md) | model/image present; not live-qualified in current session | NOT_MEASURED |
| [orcarouter-hybrid](orcarouter-hybrid.md) | model/image present; historical host-stability failures | NOT_MEASURED |
| [lychee888](lychee888.md) | L0 JSON structural PASS; model non-installable, weights unverified | NOT_MEASURED |

An H38 runtime build is a **configuration variant of OrcaRouter**,
not a sixth model profile. If comparing H38 separately, identify
runtime image, TP=1, speculative decoding parameters and load/monitor
gates in the report provenance. Never conflate historical benchmark
speed with current managed host qualification.

## Benchmark admission prerequisites

1. **Do not launch models for benchmarking.** First complete separately
   approved legacy M1 live readiness, precise API/model identity,
   runtime attestation, host memory/protection and strict NVIDIA RM
   bounded observation. Benchmarking is a later *read-only API load*,
   not a start/restart mechanism or permission to bypass a STOP gate.
2. Verify the exact served model identity against `/v1/models`,
   and use that value for both `--model` and `--served-model-name`.
   Pass an explicit local tokenizer path and record its checkpoint
   identity separately. Do not assume `orcarouter` is accepted by
   the API merely because the manifest selects it.
3. Install `llama-benchy` in an isolated virtual environment **only
   after operator approval** and pin exact upstream source revision;
   do not use an unpinned `pip install -U` on the host's service Python.
4. Record source SHA, immutable release SHA, Docker image digest,
   model checkpoint/revision, config, vLLM version, served name, TP1,
   MTP/spec decode configuration, guard thresholds, actual MemAvailable,
   SwapFree, CmaFree, GPU/RM trace window, and upstream benchy SHA.
   Record exact PP/TG/depth/concurrency/runs/warmup, prompts, cache
   and latency mode. Retain failures explicitly as NOT_MEASURED or
   FAILED, not zero throughput.
5. Start with **bounded smoke** `pp128 tg32 depth0 concurrency1`,
   then guarded standard `pp512/2048 tg32/128 depth0/4096
   concurrency1`; add concurrency2/long context only when proven
   acceptable under memory protection. Run one profile at a time
   on the single Spark. No automatic all-profiles lifecycle switch.

## Example after actual host M1 live acceptance, NOT now

The commands below are a **future operator reference**. They do not
run as part of GitHub CI, A5 or B5. `uv` and any tokenizer/corpus
dependencies may require a separately approved install/download.
Use an already verified local tokenizer path.

```bash
# DO NOT execute on the currently STOPPED model.
# Replace these documented placeholders with ACTUAL live identities.
CHECKPOINT='<verified-local-tokenizer-directory>'
SERVED_NAME='<exact-value-from-v1-models>'
OUT="$HOME/qwen38-bench-reports"
mkdir -p "$OUT"

# The benchmark package must already be installed in an isolated,
# pinned-version virtual environment.
llama-benchy --base-url http://127.0.0.1:8888/v1 \
  --model "$SERVED_NAME" --served-model-name "$SERVED_NAME" \
  --tokenizer "$CHECKPOINT" \
  --pp 128 --tg 32 --depth 0 --concurrency 1 \
  --runs 1 --warmup-runs 1 --latency-mode generation \
  --format json --save-result "$OUT/<profile>-smoke.json" \
  --exit-on-first-fail

# After a complete successful benchmark and validation:
python3 -B scripts/benchmark/llama-benchy-report.py \
  --profile orcarouter \
  --input "$OUT/orcarouter-smoke.json" \
  --output "$OUT/orcarouter-smoke.md" \
  --expected-model "$SERVED_NAME" \
  --source-sha '<actual-project-40hex-source-sha>' \
  --release-sha '<actual-installed-40hex-release-sha>' \
  --upstream-sha 'e9be344578cec17745066b220798b80a0d2686d3'
```

The converter is **strictly offline**, never starts a model or API,
validates JSON model identity, schema dimensions and finite numeric
measurements, hashes the raw JSON, and refuses to overwrite an existing
report. It reports benchmark speed, **not host-stability PASS**.
The `--model` source name must match `--expected-model`.
Never post raw prompts, token streams, API keys or private addresses
in published result documents. JSON/Markdown are local artifacts until
reviewed, sanitized, and explicitly added to evidence.

## Report comparison policy

Only compare like-for-like **actual measurements** with matched
model identifiers, dataset/test dimensions, tokenizer,
MTP/decoding, cache settings, image/backend, runtime configuration,
concurrency, warmup, environmental protection, and stable host state.
If any field differs, display the distinction rather than an
unqualified winner. Prompt-processing PP is a derived estimate;
TTFR is first response chunk, whereas E2E TTFT is first content
token. No cross-model aggregate winner from missing data.


## Bench evidence retention gate before disk cleanup

User requests **benchmark before model/Docker deletion**.
[Reclaim and archive protocol](../BENCHMARK-BEFORE-RECLAIM.md).
Keep per-model raw upstream JSON and derived Markdown outside any
planned cleanup directory; record their SHA256 and Docker image ID
alongside model checkpoint/release/config. All five current
templates are NOT_MEASURED. A future per-asset deletion requires
owner-specific approval, not merely a passing read-only inventory.


## S1 actual DGX storage snapshot: NOT a benchmark

[Physical inventory result](../scripts/benchmark/evidence/dgx-storage-pre-reclaim-readonly-20261013.md)
shows OrcaRouter 171G active, mazinb 174G present,
H3 73G and H4 64G as registered H6 parents despite
the small H6 34M directory. No new llama-benchy
numeric result exists. Preserve all five NOT_MEASURED
states pending approved model runtime validation.
