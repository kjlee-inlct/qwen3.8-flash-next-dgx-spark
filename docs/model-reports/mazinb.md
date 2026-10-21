# mazinb — benchmark report

**LATEST — 2026-10-20 physical R2 trial #3:** candidate
`qwen38-mazinb-m1-20261019221159-90ee9851`,
exact Docker `bee2e3819b7c2fef595357b61ea23934dd8969215a7fe2b957678bbf98eb1dd8`,
physically confirmed `failed_stopped`, `RUNNING=false`,
`ExitCode=137`, Docker `OOMKilled=false`, no
active M1 supervisor/watchdog processes and Docker object
preserved. Bounded watchdog tail showed low non-CMA free,
`swapgrowth` up to 3,482 MiB, `protect=0/5`
and last line `container is no longer running`;
**termination origin not yet identified**. The earlier
trial #2's retained named journal independently showed
`detail=M1Error: NVIDIA RM memory allocation error`
and `kernel_since=2026-10-19 15:54:52` (host local).
Exact matching kernel lines, third journal `detail`,
third Docker logs/full monitor state remain unexamined.
No fourth GPU launch or benchmark is authorized.
**All 2026-10-19/20 R2 throughput: NOT_MEASURED.**
This does not invalidate the original 2026-10-14
measured results below.
[Physical Stage J evidence](../../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).

**Latest 2026-10-19 R2 second trial:** pinned
`llama-benchy 0.4.1.dev1+ge9be34457` is now
physically available, but separately approved second
candidate `qwen38-mazinb-m1-20261019065452-e70d6233`
(exact ID `68cd243882bf117dbccdfad577cfdec7a95063ee8f2a96dbe6bcf51cfd8554e7`)
hit the host kernel **NVIDIA RM allocation error**
guard after STARTED_UNQUALIFIED. Controller stopped
the exact second candidate and retained Docker;
`M1_READY_FOR_BENCH` was NOT emitted and the
wrapper correctly rejected the performance trial.
**R2 performance remains NOT_MEASURED**. This
host-stability failure does not rewrite the earlier
first trial API/soak/smoke PASS or original 2026-10-14
M1 measured results. Await host journal RM line
timestamps and stopped Docker/monitor forensic evidence.
[Stage H physical record](../../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).

## Earlier R2 evidence — 2026-10-19 first-trial protected STOP

**2026-10-19 R2 final actual trial status:** protected isolated
model API + 180-second monitored soak + actual inference smoke
**PASS**; owner explicitly entered `STOP` and controller
confirmed exact new trial Docker ID
`82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424`
**STOPPED**, `M1_DOCKER_REMOVED=NO`. **New R2 llama-benchy
measurements do not exist** because the pinned executable
was unavailable. The only mazinb throughput numbers
below remain the historical 2026-10-14 M1 data.
[Stage G actual physical evidence](../../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).

## Earlier R2 evidence — 2026-10-19 first-trial READY

**2026-10-19 R2 subsequent physical READY:** the user-approved isolated vLLM candidate passed actual model API, 180-second monitored soak and smoke (`M1_INFERENCE_SMOKE=PASS_NO_GENERATED_TEXT_PERSISTED`, `M1_READY_FOR_BENCH=http://127.0.0.1:18889`); exact new Docker ID `82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424`. **New R2 llama-benchy measurement has NOT been performed**, and shell PATH lacks the pinned benchmark CLI. This READY evidence does not establish permanent systemd operation or long-term host stability. [Stage D physical receipt](../../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).

**2026-10-19 R2 physical update:** owner-approved protected trial at clean local source `4612045c11ce47e52606794d63daede4cb35ac82` printed `M1_CANDIDATE_STARTED_UNQUALIFIED=qwen38-mazinb-m1-20261019043708-479dfc86`. The actual R2 API READY/smoke/180-second soak/benchmark remain **NOT_MEASURED**. Operator PATH did not resolve `llama-benchy`; results parent `READY`. No local source sync/package installation should occur during live session. [Full physical receipt](../../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).

**HISTORICAL 2026-10-14 BENCHMARK_STATUS: MEASURED. R2: NOT_MEASURED.**

## New R2 checkpoint and protected preflight — ACTUAL DGX 2026-10-19

Checkpoint `mazinb` at pinned revision `f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f` was restored to the canonical repo `models/qwen3.8-flash-next-mazinb` directory with 108/108 `verified` files (`COMPLETE_DOWNLOADER_VERIFIED`). Wizard `5→24→3` physical preflight returned `M1_PREFLIGHT=PASS_READ_ONLY`, preserving old managed Docker `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`, installed release `ff67bab3c94d6992f61b9535836df97f03b9c022`, experimental image digest `dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734`. **No new R2 GPU start, API READY, soak or actual benchmark yet.** Preserve original 2026-10-14 measurements below as historical. [Physical receipt](../../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).

## Actual DGX Spark M1 benchmark — 2026-10-14

First successful physical mazinb M1 benchmark.

### Provenance

| Field | Value |
|---|---|
| Model | `mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4` |
| Host | Single DGX Spark |
| Runtime | vLLM v0.29 experimental image |
| KV cache | 16 GiB |
| Project source SHA | `67f45d506cd773b2c5066659ddcb946970cc5ff1` |
| Installed release SHA | `ff67bab3c94d6992f61b9535836df97f03b9c022` |
| Exact M1 Docker ID | `7af3966f3d0cae79f8277eaf9ad003fb04c1e15ea01f86574c2d8eeac396e7a1` |
| llama-benchy | `0.4.1.dev1+ge9be34457` |
| Upstream SHA | `e9be344578cec17745066b220798b80a0d2686d3` |
| Concurrency | 1 |
| Depth | 0 |
| Runs | 3 measured, 1 warmup per configuration |
| Prefix caching | Disabled |
| Latency mode | generation |

### Actual measured results

| Metric | PP 512 / TG 128 | PP 2048 / TG 128 |
|---|---:|---:|
| Prompt processing (tok/s) | 1115.21 ± 428.53 | 1597.94 ± 53.31 |
| Token generation (tok/s) | 23.11 ± 1.05 | 22.54 ± 1.68 |
| Peak generation (tok/s) | 32.33 ± 1.25 | 29.00 ± 2.45 |
| E2E TTFT (ms) | 758.40 ± 296.44 | 1469.04 ± 43.43 |

Generation latency probe average: **185.32 ms**.

### Verified gates

- Exact model API identity verified
- 180-second post-ready observation completed
- Actual inference smoke passed
- llama-benchy coherence test passed
- Smoke benchmark completed
- Main benchmark completed
- Before/after benchmark admission passed
- No matching NVIDIA RM events in the checked window
- Original raw results verified with SHA256

The benchmark does not independently certify long-term host stability,
determinism or complete managed lifecycle qualification.

Concurrency scaling above 1 remains NOT_MEASURED.

### Evidence

- [Raw smoke JSON](evidence/mazinb/20261014T015805Z/smoke.json)
- [Raw measured JSON](evidence/mazinb/20261014T015805Z/mazinb.json)
- [Original generated Markdown report](evidence/mazinb/20261014T015805Z/mazinb-report.md)
- [Portable SHA256 manifest](evidence/mazinb/20261014T015805Z/SHA256SUMS)

The original generated Markdown includes literal escaped backticks
due to a report-generator formatting issue. Raw JSON measurements
are preserved unmodified.

See [benchmark protocol](README.md).
