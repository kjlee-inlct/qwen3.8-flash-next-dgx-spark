# OrcaRouter managed RM-sysmem R10b clean trace — 2026-10-03

## Classification

- Experiment validity: **VALID / MANAGED RUNTIME RESTART OBSERVED**
- Functional classification: **PASS**
- Host-stability classification: **PASS** under the current strict policy for this measured run
- RM-sysmem result: **NO RM OOM IN CAPTURE WINDOW**

This run is the corrected follow-up to the invalid first R10 attempt. The normal managed OrcaRouter service path executed successfully under the trace, a replacement container was observed, allocator trace data was recorded on every CPU, the replacement runtime committed and became healthy, and no kernel RM/OOM signature appeared inside the capture window.

This clean run does **not** prove that the promoted 16 GiB configuration eliminates the RM sysmem problem. A previous restart of the same promoted OrcaRouter 16 GiB release emitted six `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)` events before recovering to readiness. R10b therefore strengthens the conclusion that the failure is allocator-state-dependent across otherwise comparable managed restarts.

## Preconditions

Before R10b:

- repository branch was current at `409f80d4991e4992e118d3380232a07fe11ff750`;
- immutable current release was `ff67bab3c94d6992f61b9535836df97f03b9c022`;
- update, runtime, and profile-switch transaction states were all idle;
- managed service was active and API health was ready;
- no temporary `kv16-ab.conf` service override was present;
- repository-managed OrcaRouter default remained 16 GiB.

## Validity closure

The corrected runner reported:

```text
trace_rc=0
managed_rc=0
restart_observed=1
run_valid=1
analysis_rc=0
```

The pre-run container was:

```text
4157f17f765b8f82e6a2f0af2903cc1e8fef2669a679e61574e54bee2c992817
```

The post-run container was:

```text
5401222c6d2b02f21f46c4315b97ec05ee493936d532ad702d334348688b52c5
```

The container identity change proves that the managed restart actually occurred, unlike the invalid first R10 attempt.

## Trace capture was substantive

All CPU trace sections contained non-zero data. Several CPUs recorded multi-megabyte compressed traces, including large uncompressed sections on CPUs 7, 15, 16, and 19. This confirms that the allocator/RM trace window covered the real startup rather than an empty child-failure interval.

The replacement runtime progressed through PLE-offload checkpoint loading, the main checkpoint load, backend/MoE selection, the subsequent loading phase, CUDA-graph capture, and finally committed readiness.

## RM/OOM result

The R10b summary contained an empty kernel-error section and the analyzer reported:

```text
RM_SYS_ANALYSIS=NO_RM_OOM_IN_CAPTURE_WINDOW
```

Because `run_valid=1` and the trace contained real allocator activity, this line is a valid clean-run result for this specific restart.

No `_memdescAllocInternal`, `NV_ERR_NO_MEMORY`, kernel OOM-killer event, or protected-stop evidence was reported in the capture summary.

## Functional result

The final managed state was:

```text
CURRENT_RELEASE=ff67bab3c94d6992f61b9535836df97f03b9c022
UPDATE_STATE=idle
TRANSACTION_STATE=idle
PROFILE_SWITCH_STATE=idle
Result=success
ExecMainCode=0
ExecMainStatus=0
ActiveState=active
SubState=running
```

The final container was running with `exit=0` and `oom_killed=false`, and the API returned `HEALTH=ready` with the expected model:

```text
orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Therefore this measured run is **FUNCTIONAL PASS / HOST-STABILITY PASS**.

## Interpretation relative to the promoted-release failure

The promoted immutable-release validation and R10b used the same release and repository-managed 16 GiB OrcaRouter default, but observed different kernel outcomes:

- promoted-release restart: six recoverable RM OOM events before readiness;
- R10b traced restart: zero RM OOM events and strict PASS/PASS.

This is strong evidence that the early RM sysmem failure is not deterministic from profile + KV size alone. The allocator state at the time of the post-weight-load / FP4-MoE / subsequent-load transition materially affects whether the large RM Linux-sysmem allocation path fails.

## Follow-up closure

A later corrected R10b attempt 02 reproduced six RM OOM events with a valid allocator trace on the same immutable release and 16 GiB default.

That follow-up directly captured the same structural recovery pattern previously established by Hybrid R9: every failed 64 KiB/order-4 RM Linux-sysmem request was followed immediately on the same thread by the same logical request and captured policy at 4 KiB/order 0, where it succeeded.

The six failed logical request sizes were 3.125 GiB, 1.5625 GiB, approximately 1.186 GiB, approximately 1.193 GiB, 40 MiB and 40 MiB. This proves the fallback mechanism is not specific to the approximately 16 GiB request observed in R9.

Canonical follow-up evidence:

```text
scripts/benchmark/evidence/orcarouter-managed-rmsys-r10b-02-rm-oom-20261003.md
```

Accordingly, this document remains the canonical **clean** R10b run, while attempt 02 is the canonical traced OrcaRouter RM-fallback run. Further tracing is no longer needed merely to prove the fallback shape; the remaining allocator question is which Linux zone/migratetype/buddy/pageblock state determines whether an order-4 RM allocation succeeds or falls back.
