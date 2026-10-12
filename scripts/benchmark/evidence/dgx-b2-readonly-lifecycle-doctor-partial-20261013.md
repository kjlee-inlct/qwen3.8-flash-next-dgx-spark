# Actual DGX stage B2 full read-only lifecycle + Doctor — partial (2026-10-13)

**Evidence class:** physical-DGX operator-pasted terminal output; not independent host attestation or a byte-for-byte log archive. The output contains no independently reliable execution timestamp. No GPU/model/service or lifecycle mutation was performed by this inspection.

## Exact checkout, invocation scope and verdict

- Git checkout asserted with exact 40-character SHA: `b35d0f3d7840d00c55f4c633813e88ac367c6373`.
- Auditor preflight: `MANAGED_LIFECYCLE_READONLY_PREFLIGHT=BEGIN`; scope `read_only_inventory_transaction_status_doctor_no_mutation`.
- `host_mutation=NO`, `model_or_gpu_launch=NO`, `no_install_uninstall_or_purge=YES`.
- Successful sections (`rc=0`): selected-profile snapshot, model inventory, backend registry, profile-switch status, runtime-transition status, update-transition status, release-profile-refresh status.
- Doctor returned `rc=1`, with **5 FAIL / 2 WARN**.
- Final result: `MANAGED_LIFECYCLE_READONLY=PARTIAL_CHECK_FAILURE`, `MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED` (auditor's nonzero final exit is expected from the failing Doctor, not evidence of a mutating rollback).

## Installed state, model and runtime

| Field | Observed |
|---|---|
| Manifest / phase | `VALID` / `complete` |
| Selected / recorded profile | `orcarouter` / `orcarouter` |
| Repository | `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` |
| Expected image | `vllm-skinny-tp1:v1` (legacy) |
| Expected served name | `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` |
| Model marker | `MARKER_PRESENT_NOT_VERIFIED` (compact snapshot) |
| Checkpoint doctor | index present, **18 referenced shards complete**, checkpoint manifest complete |
| Four transactions | `IDLE` / all status commands `idle` |
| Stale artifacts | `NONE` |
| Monitor settings | `MONITOR_PROTECT=1`, `MONITOR_ENABLED=1` |
| Container / service | `EXITED` / `INACTIVE` |
| Runtime attestation | `MISSING` |
| Actual served profile | `NOT_VERIFIED` |
| Release qualification | current and previous immutable releases verified; current digest qualified |
| Runtime configuration | `NOT_APPLICABLE` while stopped |

The inventory listed OrcaRouter, mazinb and OrcaRouter Hybrid as locally installed; NVIDIA as absent; lychee888 as planned/non-installable. vLLM was the stable registered backend; SGLang was planned and not installable.

## Full Doctor failures and warnings (verbatim classification)

| Class | Diagnostic |
|---|---|
| FAIL 1 | runtime commit attestation is missing or unsafe |
| FAIL 2 | container state is exited |
| FAIL 3 | API port is not loopback-only: no published port |
| FAIL 4 | memory protection monitor PID file is missing |
| FAIL 5 | health endpoint does not respond |
| WARN 1 | managed OrcaRouter still uses a legacy image; `--refresh-profile-defaults` suggested after immutable release update |
| WARN 2 | systemd service exists but is inactive |

**Interpretation:** All five failures were observed while no runtime service was running; the missing published *running* port is not by itself evidence that the Docker host binding is misconfigured. Missing attestation, inactive monitor and failed health do not become a success merely because an intentional stopped state is possible. The older October 7 journal/monitor evidence documented a candidate protection stop and restoration of the predecessor in stopped state; that historical evidence may explain the lineage, but this B2 alone cannot prove a current live runtime is stable or establish a fresh stop cause.

## Host reserve and unchanged protection evidence

- Doctor: `non-CMA memory reserve` PASS — **118 GiB available**, `CmaFree=0 GiB`.
- `non-CMA free-memory floor` PASS — **79,620 MiB free**.
- Swap reserve PASS — **143 GiB free**; dedicated PLE swap active.
- Model-filesystem reserve PASS — **104 GiB free**.
- Docker daemon available, vLLM image present, container image/model mount/served name match manifest, container init enabled.
- Managed API socket active; Docker-app `8000` and LAN `10.221.50.65:8000` configuration checks PASS.
- No evidence of disabling/protection-threshold changes or installation/removal.

## Acceptance and next decision

```text
ACTUAL_DGX_SOURCE_SHA=b35d0f3d7840d00c55f4c633813e88ac367c6373
ACTUAL_DGX_A_SYNTHETIC=PASS_134_OF_134_PREVIOUSLY_COLLECTED
ACTUAL_DGX_B1_SELECTED_PROFILE=COLLECTED_STOPPED_BASELINE
ACTUAL_DGX_B2_READONLY=COLLECTED_PARTIAL_DOCTOR_5_FAIL_2_WARN
DOCTOR_READONLY_RC=1
MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED
M1_HOST_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_LIVE_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
D0_INDEPENDENT_DISPOSABLE_ADMISSION=NOT_GRANTED
D1_D5_DESTRUCTIVE_E2E=NOT_RUN
CHECKPOINT_METADATA_ORDER_GATE=FAIL
HOST_STABILITY=INCONCLUSIVE
PR_259=DRAFT_OPEN_UNMERGED
```

B2 is **collected**, not clean/healthy. Before any owner-scoped reversible OrcaRouter startup, use the operator-facing staged-validation runbook to verify exact installed immutable release and service identity, distinguish the legacy baseline from H38 migration, confirm idle transactions and unchanged monitor protection, specify exact rollback/stop conditions and retention of host/kernel evidence. Do not fabricate `runtime-commit.env`, direct-start the exited Docker container, force recovery, refresh defaults to silence the warning, or infer H38 authorization. No new live launch occurred as part of this evidence.
