# OrcaRouter managed 16 GiB promoted-release validation — 2026-10-03

## Classification

- **FUNCTIONAL: PASS**
- **HOST-STABILITY: FAIL** under the current strict policy
- **Kernel classification: confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)`**
- **Protection outcome: no protected stop observed**

This run validates the repository-promoted 16 GiB OrcaRouter KV default after removing the temporary service-scoped override and cutting over to immutable release `ff67bab3c94d6992f61b9535836df97f03b9c022`.

## Release promotion

The staged release was verified and qualified before cutover:

- target release: `ff67bab3c94d6992f61b9535836df97f03b9c022`
- release manifest files: 222
- qualification unit tests: 370 passed
- previous immutable release: `a8aeca47433dc4033b3f1f995eb59023467222ce`
- temporary `KV_MEM=17179869184` systemd override was removed before cutover
- release cutover start: 2026-10-03 15:17:50 KST
- update transition committed successfully
- current release after cutover: `ff67bab3c94d6992f61b9535836df97f03b9c022`
- update/runtime/profile-switch transitions returned to idle

The release update therefore validated the repository default independently of the temporary experiment override.

## Runtime configuration confirmation

The replacement OrcaRouter runtime used:

- profile: `orcarouter`
- image: `vllm-skinny-tp1:v1`
- PLE: CPU offload
- speculative decode: MTP, k=2
- max model length: 262144
- managed memory protection: enabled
- no temporary service-level KV override

The runtime itself confirmed the promoted default:

- initial free memory: 114.94 GiB
- reserved KV memory: **16.0 GiB**
- GPU KV cache size: **579,086 tokens**
- maximum reported concurrency at 262144 tokens: **2.21x**

This closes the configuration question: the 16 GiB reservation came from the promoted repository release, not from the earlier `/run` override.

## Functional result

The managed replacement completed successfully:

- candidate remained running throughout startup
- health-ready at 15:32:27 KST, elapsed 871 s
- expected served model validated at 15:32:27
- runtime transition committed at 15:32:27
- runtime attestation written at 15:32:27
- `/health` and `/v1/models` returned HTTP 200
- release update committed successfully
- canonical container remained `running`
- Docker reported `OOMKilled=false`

Strict functional classification: **PASS**.

## Host-stability evidence

Despite functional success, the kernel emitted six top-level NVIDIA RM sysmem allocation failures before readiness:

- 15:29:35 KST: **4** `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)` events
- 15:29:48 KST: **2** `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)` events

The memory monitor did not cross the protected-stop boundary:

- 15:29:06: available 41,704 MiB; non-CMA available 41,637 MiB; non-CMA free 5,079 MiB; swap-free 45,507 MiB
- 15:30:07: available 28,235 MiB; non-CMA available 28,167 MiB; non-CMA free 981 MiB; swap-free 45,518 MiB
- 15:31:08: available 38,540 MiB; non-CMA available 38,472 MiB; non-CMA free 28,261 MiB; swap-free 44,515 MiB
- 15:32:08: available 16,285 MiB; non-CMA available 16,217 MiB; non-CMA free 5,262 MiB; swap-free 46,074 MiB

No new `PROTECT stopping` event was observed for this promoted-release window. The historical protected-stop entries present in the broader monitor log belong to earlier runs and are not attributed to this candidate.

Under the current strict policy, any confirmed RM OOM makes host stability fail even if the runtime recovers and completes startup.

Strict host-stability classification: **FAIL**.

## Startup-phase localization

The RM failures are temporally separated from the manual KV-cache reservation and therefore must not be attributed directly to allocating the 16 GiB KV pool.

Observed order:

1. main long checkpoint load completed at 15:29:33 KST (`Loading weights took 652.96 seconds`)
2. first RM OOM cluster occurred at 15:29:35 KST, concurrent with the post-load FP4/Marlin setup warning
3. MoE prepare/finalize selection followed at 15:29:36
4. second RM OOM cluster occurred at 15:29:48 KST, concurrent with kernel/backend selection
5. another checkpoint-loading phase began at 15:29:49 with only about 28.72 GiB available RAM reported by the loader
6. the complete model load did not finish until 15:31:01
7. the manual KV pool was not reserved until 15:31:39, approximately two minutes after the first RM OOM cluster

Therefore the supported localization is:

> the observed RM sysmem failure occurs in the post-main-weight-load / FP4-MoE initialization and subsequent model-loading transition, before vLLM creates the manual KV cache.

This changes the causal interpretation of the KV mitigation. Lowering KV from 24 GiB to 16 GiB cannot be treated as the direct fix for these early RM allocation failures because the configured KV pool does not yet exist when they occur. The lower KV reservation can still materially improve later survivability and memory margin, which is consistent with the 24 GiB protected-stop versus 16 GiB recoverable outcomes.

The logs do not establish which exact CUDA/RM allocation inside this transition issued the failing request. A lower-level allocation trace is required before attributing it specifically to Marlin, MoE backend initialization, the subsequent draft/model load, or another allocation in the same interval.

## Relationship to the adverse-state A/B

The immediately preceding temporary 16 GiB OrcaRouter B-run was strict **PASS / PASS**: it reached readiness, completed the required soak, and had an empty kernel RM/OOM window.

The promoted-release restart used the same 16 GiB KV size but produced six recoverable RM OOM events while still reaching readiness. Therefore:

1. the earlier A/B result remains valid for its measured allocator state;
2. 16 GiB materially improves resilience relative to the observed 24 GiB fatal/protected-stop case;
3. 16 GiB does **not** deterministically eliminate RM sysmem allocation failures across restarts;
4. restart/lifecycle allocator state remains a material variable even with the lower KV reservation;
5. the RM failure itself occurs before KV allocation, so the KV size is best understood as a survivability control rather than a proven cause/fix for the early RM event.

This is consistent with the earlier mazinb 16 GiB managed revalidation: lower KV pressure can move the runtime away from the fatal/protected-stop boundary without guaranteeing a clean strict host-stability pass on every startup.

## Operational conclusion

Keep OrcaRouter's managed default at **16 GiB** as a resilience mitigation. Do not revert to 24 GiB based on this run: the observed 24 GiB adverse-state recovery failed functionally and crossed protection 5/5, whereas the promoted 16 GiB runtime survived the RM events, reached readiness, committed, and remained active.

However, do not describe 16 GiB as a strict host-stability fix. The supported claim is narrower:

> 16 GiB reduces later memory pressure enough to improve survivability across the observed managed-startup states, but NVIDIA RM sysmem allocation failures remain allocator-state dependent and can occur earlier in startup before the KV pool is created.

The exact lower-level R9 order-4 rollback / order-0 retry mechanism was not traced during this promoted-release run and must not be claimed as independently re-proven here.

## Current machine state at evidence collection

- immutable current release: `ff67bab3c94d6992f61b9535836df97f03b9c022`
- OrcaRouter service: active/running
- canonical container: running
- Docker OOMKilled: false
- temporary 16 GiB service override: removed
- repository-managed 16 GiB default: confirmed in the live runtime
