# Actual DGX Spark A/B protection results — 2026-10-13

## Measurement classification

ACTUAL_DGX: YES
MODEL_API_READY: NO
LLAMA_BENCHY: NOT_MEASURED
GPU_THROUGHPUT: NOT_MEASURED
OFF_HOST_BACKUP: NOT_YET_VERIFIED

## Physical observations

| Result | Legacy A | v0.29 B |
| --- | --- | --- |
| Runtime | CPU PLE offload | PLE mmap |
| Last reported checkpoint progress | 2/18 | 11/18 |
| Stop reason | memory-protection | memory-protection |
| Exit code | 137 | 137 |
| Docker OOMKilled | false | false |
| Model/API READY | No | No |
| Actual llama-benchy | NOT_MEASURED | NOT_MEASURED |

## Forensic evidence

- Original archive basename: `qwen38-ab-evidence-20261013.tar.gz`
- Original archive SHA256: `e851100fcb674cfeac1bd99642c2a89888b8f28ea8d34fff8f07f1a4235f5dac`
- Original files remain outside this Git working tree.
- No inference-throughput comparison is justified.
- No model, image, Docker or experiment evidence is approved for deletion.
- The archive requires a separately verified off-host backup.

## Next priority

Measure installed, actually READY model profiles individually.
Do not use the experimental OrcaRouter A/B containers as a production baseline.
