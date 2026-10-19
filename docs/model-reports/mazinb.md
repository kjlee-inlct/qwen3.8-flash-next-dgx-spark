# mazinb — benchmark report

**2026-10-19 R2 subsequent physical READY:** the user-approved isolated vLLM candidate passed actual model API, 180-second monitored soak and smoke (`M1_INFERENCE_SMOKE=PASS_NO_GENERATED_TEXT_PERSISTED`, `M1_READY_FOR_BENCH=http://127.0.0.1:18889`); exact new Docker ID `82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424`. **New R2 llama-benchy measurement has NOT been performed**, and shell PATH lacks the pinned benchmark CLI. This READY evidence does not establish permanent systemd operation or long-term host stability. [Stage D physical receipt](../../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).

**2026-10-19 R2 physical update:** owner-approved protected trial at clean local source `4612045c11ce47e52606794d63daede4cb35ac82` printed `M1_CANDIDATE_STARTED_UNQUALIFIED=qwen38-mazinb-m1-20261019043708-479dfc86`. The actual R2 API READY/smoke/180-second soak/benchmark remain **NOT_MEASURED**. Operator PATH did not resolve `llama-benchy`; results parent `READY`. No local source sync/package installation should occur during live session. [Full physical receipt](../../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).

**BENCHMARK_STATUS: MEASURED**

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
