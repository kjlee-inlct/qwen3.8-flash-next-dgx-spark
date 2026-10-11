# Managed OrcaRouter candidate protection trigger — actual monitor Attempt 01 (2026-10-12)

## Actual DGX read-only source evidence, not a model rerun

Operator supplied the read-only monitor numeric-sample audit output at **clean exact checkout `7e4580bdca4054a788715bdf141e006bbb6b3f59`**. The original operator-reported file `/tmp/managed-monitor-trigger-attempt01-20261012.txt` was **not independently retrieved or SHA256-hashed**. This Markdown is a fact-checked transcription and classification of that console output, not the raw file.

```text
MONITOR_TRIGGER_READONLY_PREFLIGHT=BEGIN
checkout_sha=7e4580bdca4054a788715bdf141e006bbb6b3f59
scope=oct07_local_monitor_numeric_trigger_lines_max_120_no_host_or_service_mutation
source_bytes=2242582
host_service_or_protection_mutation=NO
gpu_or_model_launch=NO
checkpoint_payload_read=NO
monitor_matching_lines=17
HEAD=7e4580bdca4054a788715bdf141e006bbb6b3f59
monitor_read_rc=0
MEMORY_PROTECTION_EVENT=ALREADY_CONFIRMED_BY_SERVICE_JOURNAL
PROTECTION_THRESHOLD_CAUSE=NOT_YET_CLASSIFIED
RUNTIME_RESTART_OR_MODEL_LAUNCH=BLOCKED
MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED
MONITOR_TRIGGER_READONLY=COLLECTED_READ_ONLY
monitor_audit_rc=0
evidence_log=/tmp/managed-monitor-trigger-attempt01-20261012.txt
```

The inspector intentionally emits the literal `PROTECTION_THRESHOLD_CAUSE=NOT_YET_CLASSIFIED`; it performs no semantic evaluation. **This evidence classifies the operator-reported real numeric samples against actual monitoring conditions.** The source monitor's trigger logic is distinct from any assertion of a kernel OOM/NVIDIA RM error.

## Actual candidate monitor startup thresholds

```text
2026-10-07 22:08:35 monitor started: container=qwen38-flash-next mode=protect available-warn=6GiB noncma-free=2GiB free-gate=10GiB swap-growth=256MiB swapfree=8GiB
```

This **runtime-logged startup configuration** resolves the critical thresholds for this candidate (no need to merely assume source defaults). The current monitoring source uses `MIN_FREE_GIB`, `FREE_GATE_GIB`, `SWAP_ACTIVITY_GATE_MIB`, `MIN_SWAP_FREE_GIB`, `CONSECUTIVE` and a protected container stop. Actual warning entries report `protect=N/5`; their timestamps are ~2 seconds apart and satisfy five consecutive samples. We do **not** claim the image/model memory behavior was benign just because higher-level reclaimable available memory was positive.

### Filtered actual event readings

| Local KST | non-CMA free (MiB) | non-CMA available (MiB) | swap free (MiB) | swap increase since monitor start (MiB) | Logged protect |
|---|---:|---:|---:|---:|---|
| 22:17:33 | 2,017 | 26,022 | 146,470 | 17 | 0/5 |
| 22:17:35 | 1,151 | 27,111 | 145,833 | 654 | 1/5 |
| 22:17:37 | 1,154 | 28,403 | 144,539 | 1,948 | 2/5 |
| 22:17:39 | 920 | 28,959 | 143,570 | 2,917 | 3/5 |
| 22:17:41 | 868 | 29,883 | 143,022 | 3,465 | 4/5 |
| 22:17:43 | 913 | 29,909 | 143,028 | 3,459 | **5/5** |

The same operator log explicitly records:

```text
2026-10-07 22:17:33 WARNING memory margin low protect=0/5: available=26089MiB noncma_available=26022MiB free=2084MiB cmafree=67MiB noncmafree=2017MiB swapfree=146470MiB swapgrowth=17MiB
2026-10-07 22:17:35 WARNING memory margin low protect=1/5: available=27179MiB noncma_available=27111MiB free=1218MiB cmafree=67MiB noncmafree=1151MiB swapfree=145833MiB swapgrowth=654MiB
2026-10-07 22:17:37 WARNING memory margin low protect=2/5: available=28470MiB noncma_available=28403MiB free=1222MiB cmafree=67MiB noncmafree=1154MiB swapfree=144539MiB swapgrowth=1948MiB
2026-10-07 22:17:39 WARNING memory margin low protect=3/5: available=29026MiB noncma_available=28959MiB free=988MiB cmafree=67MiB noncmafree=920MiB swapfree=143570MiB swapgrowth=2917MiB
2026-10-07 22:17:41 WARNING memory margin low protect=4/5: available=29951MiB noncma_available=29883MiB free=935MiB cmafree=67MiB noncmafree=868MiB swapfree=143022MiB swapgrowth=3465MiB
2026-10-07 22:17:43 WARNING memory margin low protect=5/5: available=29977MiB noncma_available=29909MiB free=980MiB cmafree=67MiB noncmafree=913MiB swapfree=143028MiB swapgrowth=3459MiB
2026-10-07 22:17:43 PROTECT stopping qwen38-flash-next gracefully to preserve host stability
```

Prior to the trigger, the candidate monitor logged healthy heartbeats at 22:09:36, 22:10:36, 22:11:37, 22:12:38, 22:13:38, 22:14:39, 22:15:39 and 22:16:40. A separate 22:08:14 healthy heartbeat **precedes the new candidate monitor's 22:08:35 startup** and must not be attributed to that new instance.

## Evaluated threshold branch — confirmed from actual samples + monitor code

The checked-in `monitor-runtime.sh` protection logic reads in conceptual form:

```text
protect_if:
    swap_free < 8 GiB
    OR (
        noncma_free < 2 GiB
        AND (
            noncma_available < 10 GiB
            OR swapgrowth_since_monitor_start >= 256 MiB
        )
    )
consecutive_count_limit = 5
```

The values at **22:17:33** satisfy `noncma_free < 2048 MiB` but `swapgrowth=17 MiB < 256 MiB`, `noncma_available=26022 MiB >=10240 MiB`, and `swapfree=146470 MiB >=8192 MiB`: **warning but no protection count**, exactly as `protect=0/5`.

At **22:17:35** and in the next four readings:
- `noncma_free` is below **2048 MiB**;
- `swapgrowth` is above **256 MiB**;
- `noncma_available` remains above **10240 MiB**;
- `swapfree` remains well above **8192 MiB**.

Therefore the **specific branch confirmed by the actual numeric readings** is:

```text
LOW_NONCMA_FREE_AND_SWAP_GROWTH=TRUE
LOW_AVAILABLE_GATE=FALSE
LOW_SWAP_FREE_GATE=FALSE
FIVE_CONSECUTIVE_PROTECT_SAMPLES=TRUE
PROTECT_STOP_RECORDED=2026-10-07_22:17:43_KST
```

The installed October 7 monitor startup line supplies the thresholds; the current source supplies the predicate; the recorded `protect=N/5` sequence and final stop independently corroborate the branch. This is stronger than the earlier service journal's generic statement `Candidate runtime was stopped by memory protection`.

**What this does NOT prove:** whether the policy is correctly tuned for this workload; whether normal checkpoint loading temporarily crosses the heuristic (possible false positive); whether NVIDIA RM `NV_ERR_NO_MEMORY` occurred, whether the kernel itself OOM-killed any process, or whether host stability would have failed absent protection. Here `OOMKilled=false` was from the **previous** stopped container, not this candidate. No model correctness, candidate READY or strict host-stability PASS can be inferred.

### Relationship to previous service unit journal

Prior real bounded service journal recorded **22:08:30** graceful stop of old container, **22:08:35** start of new candidate and memory monitor `protect=1`, **22:18:16** the managed service's protected-candidate-stop report, **22:18:17** restoration of the previous container **in stopped state**, and `Runtime transition aborted by memory protection (state=idle)`. The ~33-second difference between monitor `PROTECT stopping` and service detection is consistent with a stop/observation interval but the exact scheduling causality was **not independently measured**.

The earlier Doctor's `5 FAIL / 2 WARN` and `M1_HOST_HEALTH=NOT_QUALIFIED` remain; this observed protection path explains their correlation without approving a stopped service. The Docker configured loopback `127.0.0.1:8888` is correct, the runtime port map absent due to stop, and the transient runtime commit/stop/monitor PID files were all absent in a later snapshot. Those absences don't erase the historic protection events.

## Gate update / stop the H38 runtime diagnostic loop

```text
MONITOR_TRIGGER_ATTEMPT01=COLLECTED_READ_ONLY
MANAGED_PROTECTION_TRIGGER_BRANCH=PASS_ACTUAL_LOW_FREE_PLUS_SWAP_GROWTH
MONITOR_TRIGGER_NUMERIC_THRESHOLD=CONFIRMED_BY_SAMPLES
CONSECUTIVE_PROTECTION_SAMPLES=5_OF_5_OBSERVED
MONITOR_FALSE_POSITIVE=UNVERIFIED
HOST_KERNEL_OR_NVIDIA_RM_OOM=UNVERIFIED
M1_HOST_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38_MANAGED=BLOCKED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
FUNCTIONAL=NOT_REACHED
HOST_STABILITY=INCONCLUSIVE
RM_MITIGATION=UNPROVEN
GPU_MODEL_RERUN=BLOCKED
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN
MERGE=BLOCKED
```

**Engineering transition:** The bounded service-journal and local monitor numeric evidence have resolved the **trigger branch** without a new model run. **No further H38 live runtime/protection experiments or more journal hunts are requested.** Return to the user's primary goal: verifiable installer/uninstaller/profile switching correctness, focusing on non-destructive UI/CLI ownership and fail/rollback testing, plus an independent disposable-host E2E plan. Do not alter protection thresholds to force a startup, generate missing runtime attestation, install/purge on the active Spark, launch H38 GPU/model, rebuild H38 image, scan tensor payload, mark PR Ready or Merge.
