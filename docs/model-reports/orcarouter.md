# orcarouter — benchmark report

## Legacy vs v0.29 images — BOTH NOT_MEASURED (2026-10-13)

The owner will compare the same checkpoint under `vllm-skinny-tp1:v1` (legacy CPU-offload) and `vllm-orcarouter-v029:v1` (mmap) **sequentially**, initially with 16 GiB managed KV. No real A/B model startup or `llama-benchy` result has been captured. API health, TTFT, PP/TG, strict host stability and reproducibility are unknown. [Wizard-based A/B protocol](../DGX-ORCAROUTER-AB-BENCHMARK.md). The current source adds a **read-only plan menu only**, not live launch. Do not populate benchmark fields from historical unrelated runs.


**BENCHMARK_STATUS: NOT_MEASURED**

| Field | Status / value |
|---|---|
| Project model profile | `orcarouter` |
| Repository/model provenance | `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` |
| Actual DGX context (2026-10-13) | checkpoint present; stopped legacy vllm-skinny-tp1:v1; M1 NOT_QUALIFIED |
| Tool | llama-benchy (planned, source SHA `e9be344578cec17745066b220798b80a0d2686d3`) |
| Source / runtime / container identity of future measurement | NOT_CAPTURED |
| Prompt processing (PP), tok/s | NOT_MEASURED |
| Generation throughput (TG), tok/s | NOT_MEASURED |
| TTFR and end-to-end TTFT, ms | NOT_MEASURED |
| Concurrency scaling | NOT_MEASURED |
| strict NVIDIA RM and monitor verdict for future run | NOT_MEASURED |

No benchmark has been executed under this new report protocol; these
are **intentional placeholders**, not zero measurements or failed
inference requests. Only populate after real `llama-benchy` JSON,
validated API model identity, pinned source/checkpoint/image, model
readiness and bounded host observation are available.

See [the benchmark protocol](README.md). Historical test results may
be separately linked with their original source/conditions, never
silently copied as current comparable measurements.
