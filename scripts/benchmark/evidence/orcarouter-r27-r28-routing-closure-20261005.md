# OrcaRouter R27→R28 routing closure — 2026-10-05

R27 live measurement and the completed H6 read-only routing inspection close the missing-W4A16 question:

- R27 was valid measured, FUNCTIONAL PASS / HOST-STABILITY FAIL.
- H6 still declares `quant_method=modelopt`, `quant_algo=W4A16_NVFP4`, and changed zero safetensor bytes.
- The inherited ignore list covers `*.self_attn.*` and `*.linear_attn.*` plus several other decoder families.
- Exact source checks confirm ModelOpt exclusion and `quant_config=None` route Linear layers to `UnquantizedLinearMethod`.
- Qwen4Exp QSA additionally opts its qkv projection out of ModelOpt FP4.
- Therefore zero R27 `ModelOptNvFp4W4A16LinearMethod.create_weights()` calls are a routing result, not a marker failure.

R28 is consequently narrowed to `UnquantizedLinearMethod.create_weights()` only. It keeps RM activity-volume semantics separate from nominal tensor payload and does not authorize a behavior-changing mitigation or broader trace.

H11 remains deferred. PR #244 remains open and unmerged.
