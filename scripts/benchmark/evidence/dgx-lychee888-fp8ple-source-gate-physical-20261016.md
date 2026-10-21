# ACTUAL DGX — lychee888 pinned FP8-PLE JSON/source gate (2026-10-16)

**Evidence class:** ACTUAL_DGX, operator-supplied terminal transcript,
not an independent assistant host session, tensor inspection or GPU run.
Exact wall-clock time, installed image digest, container ID and SHA256
of the original terminal bytes: **NOT_CAPTURED**. This record is a
transcription of the relevant fields supplied in chat; do not imply
an on-host evidence archive or independently calculated checksum.

## Checkout and operator path

The operator ran `git status --short` (no output), fetched and
fast-forwarded the branch
`feature/wizard-modular-phase1-20261014` from
`99f04da` to `aea42fa`. They launched `./wizard.sh` and chose
**3 → 7 → 3**, the lychee888 pinned FP8-PLE source gate.

The Wizard displayed:
`Manifest: valid (phase=complete)`,
`Profile: orcarouter`,
`Image: vllm-skinny-tp1:v1`,
`Runtime: NOT_PROBED`.
That image label is from the installed manifest summary; **the actual
image digest and internal vLLM source were not inspected**.

## Exact visible decision fields

```text
immutable_revision=1b3c3cedc14fb3bee4294dea5e3515af74b8268a
l0_verdict=INDEX_STRUCTURE_PASS_METADATA_ONLY
index_tensor_keys=223047
ple_weight_shards=128
ple_files=10
global_weight_scale_keys=1
ple_embedding_dtype=float8_e4m3fn
quant_method=compressed-tensors
quant_algo=None
quant_format=mixed-precision
nvidia_patch_source_dispatch=NOT_APPLICABLE; NVIDIA PATCH EXPECTS ModelOptMixedPrecisionConfig
managed_runtime_adapter=NOT_IMPLEMENTED_OR_NOT_QUALIFIED
single_gb10_tp1=NOT_VERIFIED
verdict=SOURCE_ONLY_LOADER_UNQUALIFIED
MODEL_PAYLOAD_DOWNLOADED=NO
GPU_RUN=NOT_PERFORMED
```

The terminal then showed:
`SOURCE inspection completed. FP8-PLE loader and single-GB10 TP=1
are NOT qualified.` and `lychee888 remains planned and NOT installable.`

**Verified scope:** immutable Hub revision, returned config/weight-map
JSON, exact 128 PLE keys mapped across ten FP8 files, single global
scale key, `compressed-tensors`/`mixed-precision` config,
and existing repository NVIDIA patch class mismatch. This confirms
the current NVIDIA-only patch is not directly applicable to this
checkpoint. It does NOT establish a model load failure; no attempt
was made to load any checkpoint into the GPU.

**Unresolved:** exact installed vLLM code and digest, compatible
compressed-tensors PLE quant method selection, scale registration,
post-load scale presence and multiplication, actual safetensors header
dtypes/shapes/hash, TP=1 loading/partitioning, peak host memory and
NVIDIA RM safety. No Docker, download or GPU work was performed by
this Wizard source probe; unrelated host state was not independently
audited.

## Next safe gate

Continue **source-only**, using the external
[MiaAI-Lab dual-node FP8 PLE reference](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks)
as an architectural comparison, not as installed or single-GB10
evidence. A future backend adapter must be isolated, fail closed
when PLE dtype or global scale is incompatible, and remain in
unqualified source/tests until installed-image verification and a
separately approved host trial. No Draft PR promotion or merge.
