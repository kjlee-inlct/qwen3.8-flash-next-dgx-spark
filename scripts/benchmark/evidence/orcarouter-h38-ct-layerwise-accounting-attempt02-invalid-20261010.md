# H38 CT layerwise-accounting source check — Attempt 02 INVALID (2026-10-10)

## Provenance and execution scope

- Evidence origin: operator-pasted DGX Spark terminal transcript (2026-10-10). This file is a faithful transcription of significant reported fields, not a byte-for-byte copy of the /tmp file; an independently obtained logfile SHA256 is **not** available.
- Exact clean checkout/guarded target: `88e8a0509676ddfa87780a556d26a82d6ac95a74`.
- Image ID: `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc` (`vllm-orcarouter-v029-h38-decoder-scope:v1`).
- Source-only isolated wrapper: `scripts/benchmark/check-h38-ct-layerwise-accounting.sh`.
- Operator-reported output file: `/tmp/h38-ct-accounting-attempt02-20261010.txt`; file contents/hash have not been independently collected.
- Reported scope: `exact_installed_source_only_no_checkpoint_no_gpu_no_model_no_network`.

## Terminal classification (reported)

```text
HEAD=88e8a0509676ddfa87780a556d26a82d6ac95a74
H38_CT_ACCOUNTING_PREFLIGHT=BEGIN
checkout_sha=88e8a0509676ddfa87780a556d26a82d6ac95a74
image_id=sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc
scope=exact_installed_source_only_no_checkpoint_no_gpu_no_model_no_network
H38_CT_ACCOUNTING_SOURCE=INVALID reason=incorrect_CT_parameter_wrapper:w13_weight_scale:ModelWeightParameter
H38_CT_ACCOUNTING_DIAGNOSTICS=PINNED_CT_SOURCE_ONLY
classification=PINNED_CT_SOURCE_SYNTAX_ONLY_NOT_A_PASS
registration_count=8
missing_expected_registrations=[]
gpu_model_runtime=NOT_EXECUTED
loaded_parameter_coverage=UNVERIFIED
H38_CT_ACCOUNTING_PREFLIGHT=INVALID reason=installed_source_accounting_contract_invalid
source_check_rc=2
evidence_log=/tmp/h38-ct-accounting-attempt02-20261010.txt
```

The fallback diagnostician recomputed the expected **five installed source SHA256 pins** before printing the eight-registration results. This is stronger than the previously absent registration enumeration but does not mean the full AST checker passed or that the wrapper's post-success image reinspection was reached.

## Eight installed CT parameter registrations (operator diagnostics)

| Registration | Class | torch.empty symbolic dimensions | dtype | explicit constructor weight_loader | line |
|---|---|---|---|---|---:|
| w13_weight_packed | ModelWeightParameter | num_experts; w13_num_shards * intermediate_size_per_partition; hidden_size // 2 | torch.uint8 | weight_loader | 103 |
| w2_weight_packed | ModelWeightParameter | num_experts; hidden_size; intermediate_size_per_partition // 2 | torch.uint8 | weight_loader | 117 |
| w13_weight_scale | ModelWeightParameter | num_experts; w13_num_shards * intermediate_size_per_partition; hidden_size // self.group_size | torch.float8_e4m3fn | weight_loader | 133 |
| w2_weight_scale | ModelWeightParameter | num_experts; hidden_size; intermediate_size_per_partition // self.group_size | torch.float8_e4m3fn | weight_loader | 151 |
| w13_weight_global_scale | PerTensorScaleParameter | num_experts; w13_num_shards | torch.float32 | weight_loader | 162 |
| w2_weight_global_scale | PerTensorScaleParameter | num_experts | torch.float32 | weight_loader | 172 |
| w13_input_global_scale | torch.nn.Parameter | num_experts; w13_num_shards | torch.float32 | NOT_EXPLICIT | 183 |
| w2_input_global_scale | torch.nn.Parameter | num_experts | torch.float32 | NOT_EXPLICIT | 192 |

All eight `torch.empty` expressions have `device=NOT_EXPLICIT` in their original **constructor syntax**. Four `ModelWeightParameter` objects carry `input_dim=1`, `output_dim=2`, and `weight_loader=weight_loader` constructor keywords. Two `PerTensorScaleParameter` objects carry `data` and `weight_loader`. Two plain input-scale `torch.nn.Parameter` objects carry `requires_grad=False` and have no **constructor** loader keyword.

**Do not infer** an absent post-construction `set_weight_attrs`, eventual loader, active local expert mapping, default device, successful copy credit, or real live tensor correctness from a registration AST. The report does not include those downstream attribute-assignment paths.

## Interpretation and remediation

**Actual classification:** STATIC CHECKER EXPECTED-WRAPPER MISMATCH, **not established H38 model failure**.

Attempt 01 had stopped on the previously unsupported `PerTensorScaleParameter`. Attempt 02 proves the subsequent allowlist remains too narrow: two group scales are `ModelWeightParameter` rather than `torch.nn.Parameter` or `GroupQuantScaleParameter`. This mismatch occurs even though the symbolic dimension and dtype match the previously expected scale design.

Repository remediation should use the **exact class per registration** shown above (rather than broadly authorizing any wrapper class), retain all SHA256 pins and shape/dtype/weight-loader checks, preserve unknown-wrapper rejection, and include eight-way synthetic coverage with wrong-family/shape/dtype negative tests. Preserve Attempt 01 and Attempt 02 as immutable historical errors; neither is a failure of H38 model loading.

## Next gate and safety

Run the corrected, CI-qualified source-only inspector at its exact clean HEAD. If PASS_SOURCE_CONTRACT_ONLY: source syntax and pinned image contracts are established, not weights or runtime. If INVALID: diagnose the next exact anchor; do not weaken the pinned digest or promote a partial result.

Unverified: installed-image post-construction attribute paths, CopyCounter dispatched events for indexed assignments, 512-expert unique weight/scale coverage, actual split layers 8/11 replay/order/retention, finite buffer peak, functional completion and host stability.

CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN. No H38 GPU/model run, image rebuild, checkpoint payload scan, managed runtime mutation, host-protection relaxation, CT meta implementation, PR #259 Ready or Merge.
