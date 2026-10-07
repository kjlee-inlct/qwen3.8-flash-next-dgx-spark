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

## Recovered monitor trigger

The preserved `monitor-window.log` was recovered after the run. The exact protection
window was:

```text
22:17:33 protect=0/5 noncma_available=26022MiB noncmafree=2017MiB swapfree=146470MiB swapgrowth=17MiB
22:17:35 protect=1/5 noncma_available=27111MiB noncmafree=1151MiB swapfree=145833MiB swapgrowth=654MiB
22:17:37 protect=2/5 noncma_available=28403MiB noncmafree=1154MiB swapfree=144539MiB swapgrowth=1948MiB
22:17:39 protect=3/5 noncma_available=28959MiB noncmafree=920MiB  swapfree=143570MiB swapgrowth=2917MiB
22:17:41 protect=4/5 noncma_available=29883MiB noncmafree=868MiB  swapfree=143022MiB swapgrowth=3465MiB
22:17:43 protect=5/5 noncma_available=29909MiB noncmafree=913MiB  swapfree=143028MiB swapgrowth=3459MiB
22:17:43 PROTECT stopping qwen38-flash-next gracefully to preserve host stability
```

Important observations:

- the 10 GiB absolute non-CMA-available protection gate was never approached;
- swap-free remained above 139 GiB throughout the counted window;
- protection was armed solely by low non-CMA free plus the 256 MiB swap-growth arm;
- non-CMA available increased from `26022 MiB` to `29909 MiB` across the warning
  window, and from `27111 MiB` to `29909 MiB` across the counted 1/5 -> 5/5
  protection window.

This matches the same monitor-condition family that PR #246 was introduced to refine:
high reclaimable available memory, low immediately-free non-CMA memory, and active swap
growth during cold loading. However, PR #245 exists because real RM
`NV_ERR_NO_MEMORY` was also observed with high reclaimable available memory and low
non-CMA free memory. Therefore these three instantaneous signals are not a proven
classifier by themselves.

The correct conclusion is **monitor heuristic collision**, not HOST-STABILITY PASS and
not confirmed RM OOM. The present production monitor policy must not be weakened from
this run alone.

## Evidence gap found by this attempt

The original `upload-summary.txt` did not include the monitor warning/protection lines.
The terminal diagnostic tail was dominated by the container log emitted by the monitor
after protection.

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

Do not run the follow-up managed H38 gate and do not change the production protection
thresholds yet.

The next discriminator is no longer another identical H38 startup. The recovered
samples prove that the present high-available/low-free/swap-growth heuristic can collide
with a cold-load paging state while strict RM evidence is still absent. PR #245/#246
history also proves that high available plus low free cannot by itself establish safety.

Before changing the monitor, compare the **trajectory** around the preserved
2026-09-30 real RM failure against the two known protected-stop false-positive windows.
The useful candidate discriminator is whether reclaimable non-CMA available is
materially collapsing while low-free + swap-growth persists, versus remaining stable or
recovering during ordinary paging.

Any proposed trend-aware rule must first be replayed against preserved evidence and
regression-tested. The absolute low-available gate, absolute swap-free gate, strict RM
classification, and protection behavior remain unchanged until that discriminator is
proven.
