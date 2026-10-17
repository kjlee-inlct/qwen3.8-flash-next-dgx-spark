# mazinb — benchmark report

**BENCHMARK_STATUS: MEASURED**

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
