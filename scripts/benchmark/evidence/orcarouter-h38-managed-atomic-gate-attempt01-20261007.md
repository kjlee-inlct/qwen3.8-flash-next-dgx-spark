# OrcaRouter H38 managed atomic Gate attempt 01 — 2026-10-07

Status: PROTECTED STOP BEFORE READY — FUNCTIONAL NOT REACHED / HOST-STABILITY INCONCLUSIVE

## Provenance

- repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- branch: `feat/h38-managed-integration`
- exact target / checkout: `05748a9c9a2b206a536b454dc5d662d7750913db`
- previous immutable release: `ff67bab3c94d6992f61b9535836df97f03b9c022`
- profile: `orcarouter`
- previous image: `vllm-skinny-tp1:v1`
- target image: `vllm-orcarouter-v029-h38-decoder-scope:v1`
- target image label: `qwen38.h38scope=decoder-v1`
- local evidence directory:
  `/tmp/orcarouter-h38-managed-migration-20261007T130656Z`

This is the first live execution of the redesigned atomic release + same-profile H38
refresh path. It is intentionally separate from Gate A attempts 01-04, which exercised
the retired legacy-intermediate sequence.

## Matched predecessor baseline

Before mutation, the guarded gate completed the matched legacy decode workload:

- workload: 384-token decode x5;
- status: PASS;
- median decode throughput: `34.6247 tok/s`;
- `MemAvailable` recorded by the benchmark environment: `16.452 GiB`;
- `MemFree`: `10.443 GiB`;
- `SwapFree`: `45.169 GiB`;
- predecessor served alias:
  `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`;
- predecessor managed KV setting: 16 GiB.

## Atomic candidate reached

The transaction successfully crossed the retired legacy-intermediate boundary and
reached the intended H38 runtime directly.

Observed candidate identity/control evidence included:

```text
H38 managed image verified: vllm-orcarouter-v029-h38-decoder-scope:v1
started qwen38-flash-next (
  profile=orcarouter,
  executor=mp,
  PLE=mmap,
  SPEC=mtp k=2,
  qsa_det_topk=0,
  qsa_exact_topk=1,
  maxlen=262144,
  util=0.80
)
```

The candidate remained running through repeated readiness checks up to 540 seconds.
During startup, vLLM reported:

```text
Checkpoint size: 170.88 GiB.
Available RAM: 27.05 GiB.
Auto-prefetch is disabled...
```

The candidate did not reach API READY/attestation.

## Protection event and recovery

The service runner then observed a memory-protection stop during startup:

```text
Candidate runtime was stopped by memory protection during startup;
leaving managed runtime stopped.
Previous runtime container restored but left stopped after memory protection.
Runtime transition aborted by memory protection (state=idle).
```

The outer transaction recovered the previous release + manifest + runtime tuple and
did not cold-start the safety-stopped predecessor merely to make the service active.

The terminal/upload summary recorded:

```text
migration_rc=1
doctor_rc=125
functional=NOT_REACHED
host_stability=INCONCLUSIVE
kernel_window_rc=0
rm_oom_count=0
protected_stop=1
fail_reason=atomic H38 migration failed with rc=1
script_rc=1
```

## Strict classification

This attempt is classified exactly as:

- atomic H38 candidate start: REACHED;
- managed H38 API READY: NOT REACHED;
- managed H38 migration FUNCTIONAL: NOT REACHED;
- kernel evidence collection: PASS (`kernel_window_rc=0`);
- strict NVIDIA RM no-memory evidence: NONE OBSERVED in the captured window
  (`rm_oom_count=0`);
- memory protection: INTERVENED;
- managed H38 HOST-STABILITY: INCONCLUSIVE;
- determinism/performance/restart follow-up: NOT AUTHORIZED.

A protected stop is not HOST-STABILITY PASS. Conversely, because the valid kernel window
contains no `_memdescAllocInternal` / `NV_ERR_NO_MEMORY`, this attempt is not
classified as confirmed RM OOM.

## Evidence gap found by this attempt

The full evidence directory contains `monitor-window.log`, but the generated
`upload-summary.txt` did not include the monitor warning/protection lines. The terminal
diagnostic tail was dominated by the container log emitted by the monitor after
protection, so the exact `available/noncma_available/noncmafree/swapgrowth` trigger
samples are not present in the pasted summary.

This prevents a precise decision about whether the H38 stop matched the repository's
already-known high-available + low-free + swap-growth monitor false-positive shape.

The gate is therefore hardened to extract only:

- monitor start;
- low-memory warning samples;
- recovery samples;
- heartbeat samples;
- `PROTECT stopping`.

Those lines are persisted as `monitor-protection-window.txt` and included in the
upload-oriented summary. This is observability-only. No monitor threshold, protection
behavior, runtime default, or strict RM classification rule is changed.

## Next discriminator

Do not run the follow-up managed H38 gate.

First recover the exact monitor trigger lines from the preserved attempt-01 evidence:

```bash
E=/tmp/orcarouter-h38-managed-migration-20261007T130656Z
grep -E 'monitor started:|WARNING memory margin low protect=|PROTECT stopping |memory margin recovered:|HEARTBEAT healthy:' \
  "$E/monitor-window.log"
```

Use those values to decide the next engineering step:

- if non-CMA available was genuinely low, keep the stop as direct evidence of startup
  memory pressure and investigate candidate memory/residency behavior before any retry;
- if available remained comfortably reclaimable and protection was armed solely by the
  swap-growth branch while low free memory was transient, compare it against the known
  monitor false-positive shape before proposing any policy change;
- in either case, do not disable protection and do not reinterpret `rm_oom_count=0` as
  HOST-STABILITY PASS.

A new live migration attempt is justified only after this preserved evidence has been
classified.
