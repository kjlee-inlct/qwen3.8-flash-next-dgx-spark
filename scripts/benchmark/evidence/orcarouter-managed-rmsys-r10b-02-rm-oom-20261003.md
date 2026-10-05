# OrcaRouter managed RM-sysmem R10b attempt 02 — traced RM OOM — 2026-10-03

## Classification

- Experiment validity: **VALID**
- Functional classification: **PASS**
- Host-stability classification: **FAIL** under the current strict policy
- RM-sysmem classification: **DIRECTLY TRACED RECOVERABLE 64 KiB/order-4 -> 4 KiB/order-0 FALLBACK**
- Protected stop: **not observed**
- Final runtime state: **active/running, API READY, Docker OOMKilled=false**

This is the first valid managed OrcaRouter run that both reproduced the kernel `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)` signature and captured the NVIDIA RM Linux-sysmem allocation boundary in the same trace window.

## Run validity

The corrected trace contract was satisfied:

- immutable release: `ff67bab3c94d6992f61b9535836df97f03b9c022`;
- repository-managed OrcaRouter default: 16 GiB manual KV;
- temporary service-level KV override: absent;
- trace command rc: 0;
- managed child rc: 0;
- replacement container observed: yes;
- analyzer rc: 0;
- no trace-loss markers;
- container changed from `5401222c6d2b02f21f46c4315b97ec05ee493936d532ad702d334348688b52c5` to `d221446b8d63db11d30a81332a7aeae32ab6e840e476732230c208f2861d97e2`.

The trace contains 6,754,237 decoded lines with 1,760 paired `nv_alloc_pages` calls and 1,343 paired `nv_alloc_system_pages` calls.

## Kernel and RM correlation

The kernel emitted six matching RM OOM signals:

- 17:11:04.915 KST;
- 17:11:05.290 KST;
- 17:11:05.865 KST;
- 17:13:01.697 KST;
- 17:13:01.872 KST;
- 17:13:01.878 KST.

The allocator analyzer independently found exactly:

- `nv_alloc_pages_nv_oom_returns=6`;
- `nv_alloc_system_pages_nv_oom_returns=6`.

All six failed outer calls had the same captured allocation policy:

- `contiguous=0`;
- `cache_type=0`;
- `zeroed=1`;
- `unencrypted=0`;
- `node_id=-1`;
- requested page size 64 KiB;
- derived Linux allocation order 4;
- RM return `0x51`.

For every failed outer request, the immediately following same-thread `nv_alloc_pages` call preserved `page_count` and all captured policy fields, changed only the requested page size from 64 KiB to 4 KiB/order 0, and returned success.

## Six directly traced fallback episodes

| Failure | Logical request | 64 KiB/order-4 alloc/free evidence | Candidate failed chunk | Immediate same-thread fallback |
| --- | ---: | --- | ---: | --- |
| 1 | 3.125000 GiB | 9,239 alloc / 9,238 free; 9,238 identical PFNs rolled back | 9,240 | same 3.125 GiB at 4 KiB/order 0 -> success |
| 2 | 1.562500 GiB | 9,111 alloc / 9,110 free; 9,110 identical PFNs rolled back | 9,112 | same 1.5625 GiB at 4 KiB/order 0 -> success |
| 3 | 1.185547 GiB | 18,780 alloc events; 18,779 identical PFNs observed allocated then freed | 18,781 | same 1.185547 GiB at 4 KiB/order 0 -> success |
| 4 | 1.193359 GiB | 7,627 alloc / 7,626 free; 7,626 identical PFNs rolled back | 7,628 | same 1.193359 GiB at 4 KiB/order 0 -> success |
| 5 | 0.039062 GiB | 470 alloc / 469 free; 469 identical PFNs rolled back | 471 | same 40 MiB at 4 KiB/order 0 -> success |
| 6 | 0.039062 GiB | 460 alloc / 459 free; 459 identical PFNs rolled back | 461 | same 40 MiB at 4 KiB/order 0 -> success |

For failure 3 the raw interval contains more order-4 free events than allocation events because unrelated same-order frees can occur inside the traced interval. The stronger rollback observation is the 18,779 identical PFNs that were directly seen allocated and then freed. As in R9, `candidate_failed_chunk_index` is trace-derived evidence and is not a direct observation of an NVIDIA private loop index.

## Allocator-pressure evidence

The failures were not silent high-order misses. The failing intervals contain substantial order-4 compaction, direct reclaim, and external-fragmentation activity.

Selected counts:

- failure 1: compaction 1,683; direct reclaim 197; extfrag 1,865;
- failure 2: compaction 23; direct reclaim 22; extfrag 1,762;
- failure 3: compaction 389; direct reclaim 388; extfrag 12,239;
- failure 4: compaction 431; direct reclaim 229; extfrag 300;
- failure 5: compaction 23; direct reclaim 22; extfrag 20;
- failure 6: compaction 22; direct reclaim 21; extfrag 18.

This supports an order-4 physical-allocation availability/fragmentation boundary under the allocator state present at those moments.

## Direct comparison with Hybrid R9

Hybrid R9 directly established one approximately 15.998047 GiB non-contiguous RM Linux-sysmem request that failed at 64 KiB/order 4, rolled back 135,365 identical PFNs, and immediately succeeded on the same-thread 4 KiB/order-0 retry with otherwise unchanged captured policy.

OrcaRouter R10b attempt 02 now establishes the same failure/recovery **shape** six times under the same captured policy, but at substantially smaller logical request sizes ranging from 40 MiB to 3.125 GiB.

Therefore the cross-profile proximate mechanism is now directly supported:

> Under some allocator states, NVIDIA RM Linux-sysmem requests using 64 KiB/order-4 physical chunks fail before the requested logical allocation is complete. RM rolls back the high-order allocation attempt and immediately retries the same logical request and captured policy at 4 KiB/order-0 granularity, which succeeds.

The approximately 16 GiB request size observed in Hybrid R9 is **not** a necessary condition for this mechanism. Total request size alone is not sufficient to explain the failure.

## Relationship to the 16 GiB managed KV mitigation

The OrcaRouter manual KV default remains 16 GiB, but this trace further separates that mitigation from the RM failure mechanism:

- the 16 GiB KV setting improves overall startup/runtime memory margin and has avoided the previously observed 24 GiB protected-stop boundary;
- it does not guarantee zero RM OOM events;
- the directly failed RM logical allocations in this run were 3.125 GiB or smaller, not 16 GiB;
- each RM failure recovered internally through lower-granularity fallback and the managed runtime ultimately reached READY.

Accordingly, the 16 GiB setting remains a **resilience mitigation**, not a root-cause fix.

## Strict acceptance result

The runtime functionally succeeded:

- managed replacement committed;
- service ended active/running;
- expected OrcaRouter model was READY;
- Docker `OOMKilled=false`;
- no protected stop was observed.

However, six kernel RM OOM signals occurred. Under the current project policy that is sufficient for **HOST-STABILITY FAIL** even though all six allocation episodes recovered internally.

The previously documented optional `HOST-STABILITY WARN / RECOVERABLE_RM_SYSMEM_FALLBACK` class now has stronger cross-profile evidence, but it remains an explicit acceptance-policy decision and is not adopted implicitly by this run.

## Root-cause status after this trace

The proximate mechanism is no longer Hybrid-specific. It is directly observed in both Hybrid and OrcaRouter.

R11 has since captured the next lower layer: during a valid OrcaRouter restart, Normal-zone order-4+ buddy capacity collapsed to 1.688 MiB immediately before a recoverable RM fallback despite about 20 GiB MemAvailable and about 43.5 GiB SwapFree. The 17,983 rolled-back 64 KiB chunks represented 1,123.9375 MiB, closely matching the 1,121.375 MiB Normal-zone order-4+ capacity observed immediately after rollback. See `scripts/benchmark/evidence/orcarouter-managed-rmsys-r11-allocator-state-20261003.md`.

Further repeated tracing is no longer required merely to prove the 64 KiB/order-4 -> 4 KiB/order-0 fallback shape. The remaining analysis should map the preserved R11 raw PFNs and trace migratetype fields to exact Linux zone and pageblock ownership transitions.
