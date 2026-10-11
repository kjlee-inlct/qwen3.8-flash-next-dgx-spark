# Managed runtime journal Attempt 01 — protected candidate abort and stopped old runtime (2026-10-12)

## Provenance and source classification

**Observed operator-pasted DGX Spark historical service journal**, collected with exact clean checkout `efafe36fcc2e477e9d0cd110e4db275ba40dc489`. This is **real, bounded source log evidence**, not CI, not a new model run and not operator authorization to restart. The original logfile `/tmp/managed-runtime-stop-journal-attempt01-20261012.txt` was reported but was **not independently retrieved/byte-hashed**. The supplied 118-line console transcript included the bounded historic journal lines and final return markers.

```text
RUNTIME_STOP_JOURNAL_PREFLIGHT=BEGIN
checkout_sha=efafe36fcc2e477e9d0cd110e4db275ba40dc489
timezone=Asia/Seoul(+0900)
unit=qwen38-flash-next.service
window_kst=2026-10-07T21:55:00+09:00_to_2026-10-07T22:25:00+09:00
scope=unit_journal_160_lines_max_read_only_no_service_or_model_mutation
host_service_or_protection_mutation=NO
gpu_or_model_launch=NO
checkpoint_payload_read=NO
journal_read_rc=0
RUNTIME_STOP_CAUSE=NOT_YET_CLASSIFIED
RUNTIME_RESTART_OR_MODEL_LAUNCH=BLOCKED
MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED
RUNTIME_STOP_JOURNAL=COLLECTED_READ_ONLY
journal_audit_rc=0
```

**Important:** The journal collection script intentionally emits `RUNTIME_STOP_CAUSE=NOT_YET_CLASSIFIED` because it does not parse event semantics. **This evidence performs the independent human interpretation** of explicit lines; do not modify the historical inspector's output or represent `COLLECTED_READ_ONLY` as a live-health PASS.

## Timeline — October 7, 2026 KST

| Time | Direct journal fact | Qualification |
|---|---|---|
| 22:06:57–22:08:29 | Existing vLLM API returned HTTP 200 for `/health`, `/v1/models`, `/metrics`, and `/v1/chat/completions` | Previous runtime responded before handover; does **not** qualify new candidate, global model correctness or RM host stability |
| 22:08:29.818994 | `Managed service stop: no runtime attestation; preserving any canonical container.` | Attestation missing on service stop handler, no evidence of file provenance |
| 22:08:29.911287–22:08:30.019832 | `Runtime phase: preflight-start`, memory preflight passed, transition recovery completed and state idle | A preflight PASS is not a safe running-model gate |
| 22:08:30.019832 | `Stopping current runtime container gracefully: qwen38-flash-next` | **Direct evidence explaining why previously observed canonical Docker container exited with exit code 0** |
| 22:08:35.049946 | `Runtime transition prepared (previous=1)` | Old container retained for rollback |
| 22:08:35.485788 | `memory monitor started (protect=1, pid=3127696, log=/home/inlc/.local/state/qwen38-spark/monitor.log)` | Monitor started on the candidate; neither trigger predicate nor sample values in this unit-journal line |
| 22:08:35.485788 | `started qwen38-flash-next (profile=orcarouter, executor=mp, PLE=mmap, SPEC=mtp k=2, qsa_det_topk=0, qsa_exact_topk=1, maxlen=262144, util=0.80)` | Start-command completion; not a candidate health/identity success |
| 22:08:35.569030–22:17:26.592148 | `candidate-validating`; readiness waits logged through `540/1800 seconds` | Candidate did not complete managed readiness before next event; not proof of model failure cause |
| 22:18:16.743613 | **`Candidate runtime was stopped by memory protection during startup; leaving managed runtime stopped.`** | Explicit managed service source record of protection-triggered candidate stop |
| 22:18:17.125073 | **`Previous runtime container restored but left stopped after memory protection.`** | Explicit reason old canonical runtime exists yet is stopped |
| 22:18:17.125895 | **`Runtime transition aborted by memory protection (state=idle).`** | Explicit intentional fail-closed transition abort; state-idle confirmed independently at Oct12 |
| 22:18:17.156816 | `Managed service stop: no runtime attestation; preserving any canonical container.` | Consistent with abort leaving no committed active runtime |

All excerpts above are short verbatim operator-reported log lines. The **new candidate's actual Docker ExitCode**, its specific engine readiness/memory state, and any NVIDIA RM failures were **not independently sampled in this journal inspection**.

## What this resolves — and what it does NOT resolve

**Resolved:** the earlier `RUNTIME_STOP_REASON=NOT_YET_PROVEN` for the **managed transition** can be refined to `CANDIDATE_PROTECTED_STOP_AND_ROLLBACK_CONFIRMED_BY_SERVICE_JOURNAL`. The canonical previous runtime was **gracefully stopped for transition**, and after a memory-protection stop of the candidate was **restored but intentionally left stopped**. The earlier separate Docker snapshot `exit_code=0`, `OOMKilled=false`, correct declared `127.0.0.1:8888` port and systemd `Result=success` are **consistent** with these stop/rollback paths, not proof that memory pressure was absent.

**Still unknown:** *why* the monitor decided to protect. Whether it fired for free-memory floor, available-memory gate, swap-free floor, or low-free **plus swap-growth** threshold — and whether this was a false positive during cold load — requires the timestamped monitor samples. This journal alone does **not** establish a true host OOM, safe/unsafe NVIDIA RM behavior, or causal model/kernel fault. The actual monitor script's implemented protect predicate is:

```text
protection_low = (swap_free < min_swap_free)
     OR (noncma_free < min_free
         AND (noncma_available < free_gate
              OR swap_consumed_since_monitor_start >= swap_activity_gate))
stop after N consecutive protection_low samples while --protect is enabled
```

Configured defaults **in current source** are min_swap_free=8 GiB, min_free=2 GiB, free_gate=10 GiB, swap_activity_gate=256 MiB, N=5 (2-second interval); **do not assume** the actual Oct07 service used every default without reviewing its launch args. The source documents a potential premature protected stop during normal checkpoint loading if swap activity crosses its heuristic; **this is a source-level possibility, not the observed trigger for this specific event**.

A more specific next clue is the monitor output path shown in the journal: `/home/inlc/.local/state/qwen38-spark/monitor.log`. Any follow-up must be strictly bounded and **read-only**, reviewing the same Oct07 event without restarting services, modifying thresholds, or fabricating missing `runtime-commit.env`, `runtime-stop.env`, `monitor.pid`. If log was rotated, inaccessible, not persisted, or inconclusive, retain `PROTECTION_TRIGGER=UNVERIFIED` and stop escalation.

## Updated acceptance gates (historic failures remain immutable)

```text
JOURNAL_ATTEMPT01=COLLECTED_READ_ONLY
MANAGED_TRANSITION_CANDIDATE_PROTECTION_ABORT=CONFIRMED_BY_JOURNAL
MANAGED_TRANSITION_PREVIOUS_CONTAINER_RESTORED_STOPPED=CONFIRMED_BY_JOURNAL
PREVIOUS_CANONICAL_CONTAINER_GRACEFUL_STOP_FOR_TRANSITION=CONFIRMED_BY_JOURNAL
MONITOR_PROTECTION_TRIGGER_PREDICATE=UNVERIFIED
MONITOR_FALSE_POSITIVE_AT_2026_10_07=UNVERIFIED
NVIDIA_RM_HOST_STABILITY=INCONCLUSIVE
RUNTIME_ATTESTATION_POST_ABORT=ABSENT_AT_LATER_READONLY_SNAPSHOT
M1_HOST_HEALTH=NOT_QUALIFIED
M1_READONLY_DOCTOR=FAIL_5_WARN_2
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38_MANAGED=BLOCKED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
GPU_MODEL_RERUN=BLOCKED
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN
MERGE=BLOCKED
```

**Work priority:** this settles the **managed stop/rollback reason** without replaying the model. After at most one bounded monitor-sample review, return engineering focus to installer/uninstaller/model-switch acceptance with isolated synthetic/host-independent destructive tests. No H38 GPU/model rerun, image rebuild, checkpoint payload read, host/monitor changes, service restart, PR Ready or Merge.
