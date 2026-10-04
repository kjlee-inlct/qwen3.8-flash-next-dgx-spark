# OrcaRouter R20 post-stop compaction replication — INVALID protected stop — 2026-10-04

## Purpose

R20 attempted to replicate the R18 aged-predecessor treatment using the already-proven R18 runner and a distinct evidence directory:

> aged predecessor >=45 min -> full stop -> post-stop allocator snapshot -> one `vm.compact_memory` pass -> post-compaction snapshot -> start the same immutable OrcaRouter release

The intended sequence was treatment / control / treatment:

- R18 treatment: post-stop compaction -> strict clean
- R19 control: stop only, no compaction -> RM OOM x5
- R20 treatment replication: post-stop compaction again

Host policy remained at the managed defaults:

- `vm.watermark_scale_factor=10`
- `vm.compaction_proactiveness=20`
- OrcaRouter managed KV default: 16 GiB
- immutable release: `ff67bab3c94d6992f61b9535836df97f03b9c022`

## Validity

The age condition was satisfied:

- predecessor age at the operator gate: ~85.90 min
- runner-recorded predecessor age: `5157.136 s` (~85.952 min)
- minimum age guard: `2700 s`

However the replacement did not reach committed readiness. The runner summary was:

- `run_valid=0`
- `managed_rc=1`
- `collector_rc=0`
- `restart_observed=0`
- `api_ready=0`
- `rm_oom_count=0`
- `event_snapshot_count=0`
- result: `ORCA_R18_RESULT=INVALID`

Therefore R20 is **not** a valid clean-treatment replication and must not be counted as the second clean treatment in the proposed treatment/control/treatment sequence.

## Protected-stop boundary

The candidate started and entered managed validation, but the runtime memory monitor reached its protection boundary before API readiness.

The monitor window showed:

- initial candidate heartbeat: available ~19696 MiB, non-CMA free ~1892 MiB
- low-margin warnings with an intermediate recovery after protect 2/5
- a second low-margin sequence that advanced through protect 5/5
- final protected-stop sample: available ~7430 MiB, non-CMA available ~7362 MiB, free ~1407 MiB, non-CMA free ~1340 MiB, swap free ~133261 MiB
- action: `PROTECT stopping qwen38-flash-next gracefully to preserve host stability`

The managed transition then aborted by memory protection and left the managed service inactive. The previous runtime container was restored but intentionally left stopped by the protected-stop path.

This is direct host-safety evidence. For acceptance purposes the observed startup is:

- FUNCTIONAL FAIL: API readiness/commit was not reached
- HOST-STABILITY FAIL / PROTECTED STOP: the configured memory-safety gate fired

The benchmark treatment itself remains INVALID because it never completed the replacement/readiness boundary required by the R18/R19 runner contract.

## RM/sysmem observation

No `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` line was recorded in the R20 kernel window before the protected stop:

- `rm_oom_count=0`
- `event_snapshot_count=0`
- printed kernel-error window: empty

This is notable but not sufficient to classify post-stop compaction as a replicated RM mitigation success because the candidate was terminated before the valid startup boundary. R20 neither reproduces the R19 RM failure nor reproduces the R18 full successful startup.

## Post-stop compaction effect

R20 captured Normal-zone buddy state before and after the one-shot compaction.

The Normal-zone counts imply:

- order-4+ free before compaction: ~102109.438 MiB
- order-4+ free after compaction: ~105263.438 MiB
- delta: +3154.000 MiB

The order distribution again moved upward:

- exact order-4 free: ~2218.938 -> ~1761.062 MiB
- order-5+ free: ~99890.500 -> ~103502.375 MiB
- order-5+ delta: +3611.875 MiB

Thus the explicit post-stop compaction action executed and visibly coalesced free memory into larger buddy blocks, consistent with the allocator effect seen in R18.

R20 nevertheless began from a weaker post-stop high-order state than either earlier comparison point:

- R20 pre-compaction order-4+: ~102109.438 MiB
- R20 post-compaction order-4+: ~105263.438 MiB
- R19 stop-only order-4+: ~105494.875 MiB
- R18 pre-compaction order-4+: ~110184.313 MiB
- R18 post-compaction order-4+: ~112597.438 MiB

Do not infer a hard high-order threshold from these values: R20 was stopped by the independent memory-protection gate before readiness, so the runs do not provide a completed like-for-like outcome at the same point in startup.

## Recovery follow-up

After preserving the R20 invalid evidence, the managed OrcaRouter service was started normally without another benchmark treatment.

The recovery completed successfully:

- current immutable release pointer remained `ff67bab3c94d6992f61b9535836df97f03b9c022`
- update/runtime/profile-switch transaction states were idle before recovery
- the protected-stop rollback container was exited before recovery
- the replacement container reached API/model readiness after `852 s`
- recovered container ID: `91685b554aaf6b279715eab4c5608e0293310e57369c6b5e1116f4cdacf33c42`
- recovered container state: running
- Docker `OOMKilled=false`
- managed runtime/profile-switch transitions remained idle after recovery
- final service state: active

The host after recovery reported approximately:

- MemAvailable: `15983 MiB`
- swap used: `101382 MiB`
- swap free: `46073 MiB`

The startup therefore demonstrates that large PLE swap consumption by itself does not imply the R20 protected-stop outcome. The R20 protection event remains a distinct transient memory-margin boundary rather than a simple total-swap-use condition.

The new stable age waiter was also exercised on this recovered runtime. `scripts/wait-runtime-age.sh` pinned the same recovered container ID and `StartedAt`, reported progress without following a replacement container, and returned:

- `WAIT_RUNTIME_AGE_READY`
- `age_s=2700`
- `min_age_s=2700`

This live-host validation replaces the repeated inline Python age polling used in the earlier R18-R20 operator steps.

## Interpretation

R20 changes the mitigation conclusion in an important but limited way.

Still supported:

1. Full stop alone is insufficient: R19 was valid and emitted RM OOM x5.
2. Post-stop compaction has a real allocator effect: R18 and R20 both show upward buddy coalescing.
3. R18 remains the only completed aged-predecessor post-stop-compaction run and was strict clean.
4. The managed service can recover normally after the R20 protected-stop boundary.

Not established:

1. R20 is not a second clean treatment replication.
2. Post-stop compaction is not yet proven sufficient across aged allocator states.
3. The absence of RM OOM in R20 cannot be promoted to HOST-STABILITY PASS because the safety monitor stopped the candidate first.
4. A simple pre-start MemAvailable or SwapFree threshold has not been established as the discriminator.

The next read-only discriminator is a direct R18-clean versus R20-invalid comparison of the already-captured post-stop pre/post-compaction snapshots, including buddy order distribution, migratetype composition, MemAvailable/MemFree/SwapFree, Normal-zone watermarks, and compaction vmstat deltas. No additional restart is required for this comparison.

## Current conclusion

The current sequence is:

- R18 treatment: valid clean
- R19 stop-only control: valid, RM OOM x5
- R20 treatment replication: invalid, RM OOM x0 observed before a memory-protection stop
- normal managed recovery after R20: successful and active

Post-stop compaction therefore remains the leading RM/sysmem mitigation candidate, but production integration is **not yet justified**. Analyze the existing R18/R20 post-compaction state before another treatment restart; the protected-stop path must remain separate from the recoverable RM/sysmem classification.
