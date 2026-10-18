## 2026-10-19 — Physical redirect block; HEAD-only transport diagnosis (source only)

The owner actually selected Wizard **5 → 23 → 7** on a DGX Spark.
It returned `CATPLUSPLUS_M1_BLOCKED=SOURCE_REDIRECT_BLOCKED`.
The guarded `resolve/<pinned-revision>/...` GET was deliberately not
allowed to follow an HTTP redirect; **we do not yet know** which
of the two files, 3xx status/route, or target host caused the
block. No file source declarations, real engine/loader compatibility
or GB10 residency was attested.

To safely distinguish HF metadata/cache redirects from
unauthorized external storage/CDN redirects, Wizard
**5 → 23 → 8** invokes
`scripts/runtime/catplusplus-m1.py source-transport`:
- Exactly four **HEAD** requests only: `resolve` and `raw`
  for the fixed pinned `config.json` and
  `extra/inference/inference_qwen38_flash_next_sglang.sh`.
  No arbitrary path, repo, method, revision or additional host.
- Explicit redirect handler **never follows** a redirect.
  Only numerical HTTP status and bounded redirect
  *categories* are printed: no Location URL, sensitive
  query string or signed storage token.
- No HTTP body reads, checkpoint weights, packages,
  publisher shell execution, subprocesses, Docker,
  GPU, service, journal or filesystem mutation.
- Return 0 indicates only the four HEAD requests
  provided response metadata without network/HTTP errors;
  **it is NOT a source-audit PASS**. HEAD responses
  may differ from GET, so the cause of the original GET
  remains subject to independent confirmation. Regardless
  of return code: `CATPLUSPLUS_TRANSPORT_LIVE_ADMISSION=BLOCKED`,
  `CATPLUSPLUS_M1_SOURCE_AUDIT=NOT_PERFORMED`.
- The existing **5 → 23 → 7** content audit continues
  to reject *all* redirects. Neither raw URL fallback nor
  any redirect-following or engine/GPU start is enabled.

The `raw` path is a separately documented Hugging Face
file endpoint, but that fact alone is not proof these
specific pinned files will be served directly; use physical
HEAD evidence and a separately reviewed GET strategy
before changing the source-audit transport.

The successful **2026-10-19 physical mazinb retirement**
audit has independently confirmed archived M1
evidence, the exact archived Docker objects and
the absence of a live mazinb checkpoint/runtime.
Its historical vLLM M1 benchmark does not provide
catplusplus mixed MXFP8/NVFP4+FP8-PLE engine qualification.
New physical catplusplus transport diagnosis: **NOT_RUN**
until exact HEAD/CI and Wizard 5 → 23 → 8 are verified.

## 2026-10-18 — Explicit fused-qkvz MXFP8 declaration check

The pinned two-file source audit now distinguishes a fused
`.linear_attn.in_proj_qkvz` **alias existing** from that alias
**explicitly declaring `quant_algo=MXFP8`**. All discovered fused
qkvz aliases must have the expected per-layer algorithm or the
source-declaration assessment returns `MISSING_EXPECTED_DECLARATIONS`
(exit 2); the mere presence of an alias can no longer pass it.
Wizard **5 → 23 → 7** prints total / MXFP8 / non-MXFP8 qkvz counts
and the declared PLE dtype. Synthetic tests include NVFP4 and missing
per-layer algorithm as negative cases. Neither successful source
declarations nor CI prove a real backend consumes MXFP8 scales;
the live gates and DGX physical source-audit requirement remain unchanged.

## New pinned-source inspection gate (source-only; no engine proof)

Operator Wizard: **5 Benchmark -> 23 catplusplus M1 -> 7 pinned
configuration/loader source audit**. The new
`scripts/model/audit_catplusplus_loader_source.py audit` is a
strict HTTPS read of exactly **two** small text files from the
immutable Hugging Face revision
`3251fd8afbd08f76368a9bfa71132d9aef364813`:
`config.json` (256 KiB max) and
`extra/inference/inference_qwen38_flash_next_sglang.sh`
(128 KiB max). It explicitly refuses redirects and
does **not** fetch safetensors, giant packages, git bundles,
an arbitrary publisher command, or actual engine wheels.
The maintained M1 controller action is `source-audit`; tests
can pass `--offline-dir` with two fixture files.

The diagnostic checks ModelOpt `MIXED_PRECISION` config,
fused `.linear_attn.in_proj_qkvz` entries in
`quantized_layers`, `ple_embedding_dtype=float8_e4m3fn`,
the SGLang launcher entry point, file-based PLE offload
flags, hierarchy cache declarations, and risk-bearing
`sudo`, `/proc/sys/vm/drop_caches` and `--host 0.0.0.0`.
Any mentioned flag is **SOURCE_DECLARATION_ONLY**, not proof
it is supported by the target built engine. A source-audit
return code 0 means only expected declarations were present
under a two-file bound; it cannot admit checkpoint download,
start GPU, validate MXFP8 block scales in actual tensors,
enable swap paging, or certify memory headroom.

The user-confirmed publisher README advertises a custom
SGLang backend, file PLE offload and a fused qkvz scaling fix;
**the example must not be executed verbatim on GB10**.
An actual DGX output from the new audit is still required;
neither synthetic CI nor a read-only tool's presence attests
the immutable revision's exact two fetched files.

# catplusplus M1 — mazinb M1-style isolated benchmark workflow

**Status (2026-10-18): SOURCE-ONLY / NOT_REGISTERED / NOT_DOWNLOADED / NO GPU SESSION / NO BENCHMARK.**

This follows the **same user-facing process as the successful mazinb M1**, not its assumption of a working model loader. The primary goal remains the integrated interactive `./wizard.sh` (and eventually normal `install.sh` / `uninstall.sh`) rather than manual Docker commands.

## Operator Wizard menu

```text
./wizard.sh
  5 — Benchmark
    22 — catplusplus M0 plan (read-only)
    23 — catplusplus M1 lifecycle (SAFE SOURCE-ONLY GATES)
       1 — M1 plan
       2 — M1 status
       3 — M1 preflight
       4 — M1 Terminal-B benchmark admission
       5 — M1 GPU start gate — explicitly blocked
       6 — M1 journal reconcile — no Docker
       7 — Pinned config and SGLang launcher source audit (small HTTPS text only)
       0 — Back
```

The Wizard routes to the maintained `scripts/runtime/catplusplus-m1.py` read-only source scaffold, NOT to `scripts/runtime/mazinb-m1.py` (which binds different checkpoint, image, service assumptions and localhost port). The original six familiar mazinb-style actions remain; the seventh `source-audit` action is a separate bounded read-only source-inspection gate. `run`, `preflight` and `bench-admission` currently **return exit code 2**, and none creates or starts Docker, changes services, downloads weights, queries a model API or touches GPU. `status` is a strict, bounded read-only local journal view, not live Docker/API verification. `reconcile` is a no-op only when no journal exists; it does not stop/remove an unknown object.

## The mazinb M1-style state sequence — contract ONLY

1. `READ_ONLY_PREFLIGHT`: exact model revision and release, existing protected objects and pending lifecycle markers, filesystem/swap, memory and image source.
2. `EXACT_PROTECTED_OLD_IDENTITY_AND_LIFECYCLE_LOCK`: protect managed OrcaRouter and historical A/B; acquire a shared lifecycle lock, never silently adopt/restart them.
3. `UNIQUE_CANDIDATE_DOCKER_CREATE_ONLY`: model-specific isolated name, local-only port (proposed TCP `18892`, **not reserved**), no automatic restart.
4. `PERSIST_EXACT_ID_AND_ARM_WATCHDOG_BEFORE_START`: secure owner journal, pinned Docker ID, watchdog threshold and fresh heartbeat.
5. `EXACT_ID_START_AND_WATCHDOG_HEARTBEAT`: no unmonitored model loading, preserve GPU/RM/host telemetry.
6. `EXACT_MODEL_API_READY`: read `/health` and `/v1/models` on localhost, require exact served checkpoint identity.
7. `POST_READY_180_SECOND_SOAK`: continuous exact-ID and non-CMA/swap/RM safety supervision.
8. `INFERENCE_SMOKE_AND_RM_AUDIT`: functional response with no persisted generated text.
9. `TERMINAL_B_BENCH_ADMISSION_WITH_LEASE`: only if monitored candidate remains READY and under a pinned session and source identity; separate benchmark lock.
10. `LLAMA_BENCHY_C1_PP512_2048_TG128_WARMUP1_RUNS3`: pinned `e9be344578cec17745066b220798b80a0d2686d3` `llama-benchy`; directly comparable **shape** to mazinb M1, not necessarily performance of differently quantized runtime.
11. `FOREGROUND_EXPLICIT_STOP_EXACT_ID`: end only the newly created candidate, defer on active benchmark and preserve Docker object.
12. `PRESERVE_RAW_JSON_KERNEL_MEMORY_AND_DOCKER_EVIDENCE`: exact revision/image/release/source SHA, timestamp, actual JSON and SHA256, measured reports, STOP cause and final protected-old identities.

A future implementation must have a complete **create-only → arm → exact-ID start → READY → 180-second safety soak → smoke → bench → STOP → archive** path with tested crash/signal recovery and rollback, not a direct `docker run` shortcut. mazinb M1 proof is historical and not inherited by a new checkpoint.

## catplusplus-specific blockers — why the identical live M1 code is not reusable today

The physical pinned Hub API L0 inventory on 2026-10-16 validated revision `3251fd8afbd08f76368a9bfa71132d9aef364813` and 188,540,029,444 repository bytes (~175.59 GiB). Root safetensors rounded ~174.8553 GiB, exceeding the nominal single DGX Spark 128 **decimal GB** RAM before extra allocations; even with host swap, GPU/RM allocation and peak transient requirements are unproven. This is a model **physical-capacity and loader/quantization** problem, not a missing benchmark CLI flag.

The publisher describes an MXFP8 fused `linear_attn.in_proj_qkvz` mapping, NVFP4 experts, global FP8 PLE and customized SGLang/vLLM source. Their separate **Thor** measurements are not accepted as our **GB10** results. The repo's previously validated `mazinb` loader/image is not evidence it handles fused mixed-MXFP8 scales or mmap/file-backed FP8 PLE. The target engine source and exact immutable image/commit for GB10 have **not** been qualified. Do not use publisher snippets that drop host caches, run `sudo` or expose API on `0.0.0.0`.

Block conditions deliberately retained in the new controller:

```text
CATPLUSPLUS_M1_GATE_CHECKPOINT=BLOCKED_NOT_DOWNLOADED_OR_HASH_ATTESTED
CATPLUSPLUS_M1_GATE_ENGINE=BLOCKED_NO_PINNED_GB10_IMAGE
CATPLUSPLUS_M1_GATE_MIXED_LOADER=BLOCKED_MXFP8_QKVZ_AND_SCALE_NOT_VERIFIED
CATPLUSPLUS_M1_GATE_FP8_PLE=BLOCKED_OFFLOAD_RESIDENCY_NOT_QUALIFIED
CATPLUSPLUS_M1_GATE_MEMORY_RM=BLOCKED_PEAK_GPU_RM_AND_NONCMA_BUDGET_NOT_QUALIFIED
CATPLUSPLUS_M1_GATE_PROTECTED_SESSION=BLOCKED_CREATE_ONLY_EXACT_ID_WATCHDOG_NOT_IMPLEMENTED
CATPLUSPLUS_M1_GATE_OWNER_APPROVAL=BLOCKED_NO_CATPLUSPLUS_LIVE_AUTHORIZATION
CATPLUSPLUS_M1_ADMISSION=BLOCKED_COMPATIBILITY_MEMORY_AND_LIVE_AUTHORIZATION
CATPLUSPLUS_M1_BENCHMARK=NOT_MEASURED
```

These are **conservative qualification states**, not assertions that a future approved download can never work. Source CI and a safe physical **Wizard read-only** run may prove only that these refusal paths function.

## Concrete next implementation gates

1. Investigate repository-pinned `extra/inference` and `extra/packages` *source*, safe against external/untrusted scripts; attest correct mixed-precision loader against revision-pinned `config.json` and tensor/header inventory, keeping actual downloaded weights absent.
2. Design peak memory/RM protection and offload plan with measured or justified evidence for single GB10. Never assume swap size equals safe allocatable unified GPU memory.
3. Plan and separately request operator approval for the large checkpoint download (or a separately approved minimal header/metadata experiment), including disk limits and provenance checks. No bulk weights were requested by the phrase “same form.”
4. After loader/weights and host safety gates qualify, add an independent catplusplus M1 *real* controller by reusing tested mazinb M1 state/lock/watchdog conventions and new explicit owner approval for physical GPU startup.
5. Reuse existing mazinb pinned `llama-benchy` benchmark/reporting only upon true exact-model API READY, functional smoke and a protected 180-second soak. Until then every catplusplus throughput and TTFT remains **NOT_MEASURED**.

Links: [catplusplus metadata evidence](CATPLUSPLUS-METADATA-COMPATIBILITY.md), [catplusplus benchmark report plan](model-reports/catplusplus.md), [mazinb M1 original](MAZINB-M1-WIZARD.md).

**Do not merge Draft PR #261 or change actual DGX Docker, host services, model files, swap, watchdog or GPU without separately justified owner authorization.**
