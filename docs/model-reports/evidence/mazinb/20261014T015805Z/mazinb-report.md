# mazinb — llama-benchy measured report

**Evidence:** parsed upstream benchmark JSON with quantitative values.
**Important:** benchmark throughput is NOT a functional, determinism,
host-stability, NVIDIA RM or managed lifecycle acceptance certificate.

- Selected project profile: \`mazinb\`
- Exact reported model: \`mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4\`
- Capture timestamp (source supplied): \`2026-10-14 01:59:12Z\`
- llama-benchy version: \`0.4.1.dev1+ge9be34457\`
- llama-benchy upstream source SHA: \`e9be344578cec17745066b220798b80a0d2686d3\`
- Project source SHA: \`67f45d506cd773b2c5066659ddcb946970cc5ff1\`
- Installed runtime release SHA: \`ff67bab3c94d6992f61b9535836df97f03b9c022\`
- Raw input JSON SHA256: \`377f5b5745aa16d454269490db408376d5f18d0289e576df8cd5a92a986fc23e\`
- Context/prefix-caching mode: \`False\`
- Upstream latency mode: \`generation\`

| C | Depth | PP tokens | TG tokens | Phase | PP total tok/s | TG total tok/s | TG/request tok/s | Peak tok/s | TTFR ms | Est. PPT ms | E2E TTFT ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | 512 | 128 | standard | 1115.21 ± 428.53 | 23.11 ± 1.05 | 23.11 ± 1.05 | 32.33 ± 1.25 | 758.40 ± 296.44 | 573.08 ± 296.44 | 758.40 ± 296.44 |
| 1 | 0 | 2048 | 128 | standard | 1597.94 ± 53.31 | 22.54 ± 1.68 | 22.54 ± 1.68 | 29.00 ± 2.45 | 1469.04 ± 43.43 | 1283.72 ± 43.43 | 1469.04 ± 43.43 |

## Gates NOT established by this report

- Actual model readiness/API identity and response correctness require a separate functional test.
- RM allocation stability, memory protection, OOM and host safety require a separate bounded monitored window.
- A stopped or candidate-only model must not receive invented throughput values.
- Compare models only when prompt corpus/tokenizer, test dimensions, workload, backend runtime, caching, concurrency, warmup and host protection are recorded and compatible.
