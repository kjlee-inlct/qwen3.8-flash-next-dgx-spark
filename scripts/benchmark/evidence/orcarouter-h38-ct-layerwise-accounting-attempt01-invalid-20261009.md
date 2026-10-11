# H38 CT layerwise accounting — operator Attempt 01 INVALID, 2026-10-09

## Provenance

- Source: DGX Spark terminal output pasted by the operator in the 2026-10-09 continuation. This document transcribes only the provided output; a byte-exact copy and independent SHA256 of the /tmp logfile were **not** collected in this chat.
- Original repository checkout HEAD / explicit guard target: `b9db2c901676ebc974c22f5ee65b37bc6c208c72`.
- Read-only installed H38 Docker image identifier reported by preflight: `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`.
- Operator log path reported: `/tmp/h38-ct-layerwise-accounting-20261009.txt`; existence, full contents and hash have **not** been independently retrieved.
- Guarded script: `scripts/benchmark/check-h38-ct-layerwise-accounting.sh`.
- Exact source-only execution; no model/GPU/checkpoint tensor load was requested.

## Original observed result

```text
=== Git preflight ===
b9db2c901676ebc974c22f5ee65b37bc6c208c72
=== H38 installed-source inspection ===
H38_CT_ACCOUNTING_PREFLIGHT=BEGIN
checkout_sha=b9db2c901676ebc974c22f5ee65b37bc6c208c72
image_id=sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc
scope=exact_installed_source_only_no_checkpoint_no_gpu_no_model_no_network
H38_CT_ACCOUNTING_SOURCE=INVALID reason=unsupported_CT_parameter_wrapper:PerTensorScaleParameter
H38_CT_ACCOUNTING_PREFLIGHT=INVALID reason=installed_source_accounting_contract_invalid

=== Result ===
source_check_rc=2
evidence_log=/tmp/h38-ct-layerwise-accounting-20261009.txt
```

## Evidence interpretation

**Checker contract mismatch, NOT established runtime defect.** This inspector version restricted CT initializer wrappers to `ModelWeightParameter` and `torch.nn.Parameter`, while the exact H38 installed CT source exercised a `PerTensorScaleParameter` initializer. Thus the checker stopped at the first unsupported wrapper; it did not complete registration, accounting or RoutedExperts validation and it did not produce `PASS_SOURCE_CONTRACT_ONLY`.

The inspector validates all five source SHA256 values **before** calling CT allocation AST validation, and the wrapper has already checked the exact image ID, required H11/H12/H38 image labels, clean HEAD and isolation flags. The output therefore supports preflight/source digest acceptance up to the first AST contract failure. The wrapper's post-command image reinspection and identity-unchanged success footer were **not reached**, and must not be claimed.

The operator output does **not** show the particular scale registration where `PerTensorScaleParameter` occurs, nor its initialization arguments, dimensions, dtype, actual weight loader behavior or dispatch counts. Do not infer these details from the error text.

## Repository remediation

- The corrected AST inspector accepts vLLM-supported `PerTensorScaleParameter` for tensor/global-scale registrations and `GroupQuantScaleParameter` for grouped-scale registrations while preserving required symbolic shape, dtype and absent explicit allocation device checks.
- vLLM Parameter subclasses require explicit data=torch.empty(...) and weight_loader source attributes. Sharded GroupQuantScaleParameter also requires input_dim=1/output_dim=2.
- Unknown wrappers, missing loader, unsupported scale-family association, wrong shape/dtype and source hash drift must still fail closed. Added synthetic regression tests cover these distinctions.
- Scale class acceptance is source-only; real Torch dispatch credit, loaded expert/scale completeness and buffer lifetime remain **UNVERIFIED**.

## Next verification and stop conditions

Repeat only the guarded read-only image source inspector from a **new exact clean CI-qualified branch HEAD**, with `H38_CT_ACCOUNTING_TARGET_SHA` equal to that same HEAD. Preserve full stdout/stderr and return code. Another INVALID is an observation to diagnose (not a license for GPU/model runs). A PASS is source-syntax qualified only.

Historical state unchanged: `CHECKPOINT_METADATA_ORDER_GATE=FAIL`; `FUNCTIONAL=NOT_REACHED`; `HOST_STABILITY=INCONCLUSIVE`; `RM_MITIGATION=UNPROVEN`. H38 GPU/model run, CT meta implementation, image rebuild, host-protection changes and PR #259 Ready/Merge remain blocked.
