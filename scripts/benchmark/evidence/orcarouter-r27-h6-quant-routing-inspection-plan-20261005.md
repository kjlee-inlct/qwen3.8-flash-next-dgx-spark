# OrcaRouter R27 — H6 quantization-routing read-only inspection plan — 2026-10-05

## Status

**IMPLEMENTED — READ-ONLY INSPECTION NEXT — NO MODEL RESTART — NO LIVE RM RUN AUTHORIZED**

R27 is closed as:

**VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL — `RM_ORDER4_R26_RESIDUAL_MIXED_WITHIN_QWEN4_LAYERS`**

Canonical predecessor:

- `scripts/benchmark/evidence/orcarouter-r27-linear-residual-result-20261005.md`

R27 found zero runtime invocations of `ModelOptNvFp4W4A16LinearMethod.create_weights()` despite the H6 checkpoint declaring `W4A16_NVFP4`, while `91.996099%` of the R26 non-MoE residual remained inside selected Qwen4 decoder layers.

The next question is therefore routing, not another allocator trace.

## Objective

Determine, without loading or restarting a model:

1. the exact H6 `quantization_config` fields;
2. inherited `ignore` / `exclude_modules` patterns;
3. whether those patterns approximately cover large checkpoint module families;
4. config-group structure, if present;
5. source-level reasons selected Qwen4Exp subpaths may force `quant_config=None` or an unquantized method.

This inspection must remain read-only.

## Inspector

Repository helper:

- `scripts/benchmark/inspect-orcarouter-r27-h6-quant-routing.py`

Default checkpoint:

`models/qwen3.8-h6-modelopt-w4a16`

The helper reads only:

- `config.json`;
- `model.safetensors.index.json`;
- `.qwen38-hybrid-manifest.json`.

It does not import vLLM, instantiate the model, touch CUDA, alter symlinks, or change checkpoint files.

Its checkpoint-name matching against ignore/exclude patterns is explicitly **approximate** because exact vLLM routing also applies packed-module mapping and model-specific `quant_config=None` overrides.

## Static source contracts to verify

In the exact R27 diagnostic image, verify read-only that:

- `LinearBase` chooses `UnquantizedLinearMethod()` when `quant_config is None`;
- ModelOpt exclusion routing can return `UnquantizedLinearMethod()`;
- `ModelOptNvFp4Config` selects `ModelOptNvFp4W4A16LinearMethod` only for modules that actually receive the ModelOpt config and are not excluded;
- Qwen4Exp `without_modelopt_fp4()` converts `modelopt_fp4` to `None`;
- Qwen4Exp QSA `qkv_proj` uses `without_modelopt_fp4(quant_config)`.

These are source-routing facts only; they do not claim RM ownership.

## Decision branches

### Config/source routing explains zero W4A16 calls

If H6 ignore/exclude patterns and explicit Qwen4Exp opt-outs account for the relevant dense families, record the routing closure and use those exact unquantized families to design the next allocator boundary. Do not perform a generic R28 live run merely to rediscover the same routing.

### Config/source routing is insufficient

If the read-only inspection cannot explain the zero W4A16 call count, R28 should be a marker-only generic LinearBase dispatch measurement. It must record:

- parameter prefix;
- LinearBase subclass;
- actual selected `quant_method.__class__.__name__`;
- input/output partition dimensions;
- parameter dtype;
- create-weights begin/end interval.

The analyzer should aggregate direct-RM order-4 activity by actual quant-method class and prefix family. R28 must inherit the validated narrow R24 trace and strict host-stability classification.

## Safety / gate

No live R28 run is authorized by this document.

Do not delete or reuse R27 evidence. Do not repeat R27. Do not apply H11 yet. Do not broaden into UVM, page-allocation, scheduler, function-graph, CUDA-API, Python-profiler, or PLE page-fault tracing.

PR #244 remains open. No merge is implied or authorized.
