# H38 early-burst mechanism transfer from R11/R23–R32 — 2026-10-08

Status: **READ-ONLY / SOURCE-EVIDENCE RECONCILIATION COMPLETE — DRIVER MECHANISM WELL SUPPORTED, H38-SPECIFIC TRIGGER NOT DIRECTLY TRACED; NO NEW LIVE RUN AUTHORIZED**

## Exact scope

This document reconciles H38 production-shape allocator/protection attempt 01 with the already completed R11 and R23–R32 investigations. It does not add an RM event, infer a safe allocator threshold, or turn a source-code correlation into direct runtime ownership proof. This is **not** a new H38 experiment. It does not reopen the R23–R32 model-prefix trace campaign.

- H38 source: `orcarouter-h38-allocator-protection-offline-analysis-20261008.md`.
- R11 lower page allocator: `orcarouter-managed-rmsys-r11-allocator-state-20261003.md`.
- R23 narrow driver endpoint: `orcarouter-managed-rmsys-r23-ownership-closure-20261004.md`.
- Final userspace/source closure: `orcarouter-r23-r32-allocation-localization-closure-20261006.md`.
- Current PR #259 stays **Draft/Open**. Latest H38 live qualification: **VALID PROTECTED_STOP, FUNCTIONAL NOT_REACHED, HOST-STABILITY INCONCLUSIVE**. Strict RM OOM count in this H38 measured window: zero.

## Evidence matrix: what is directly observed, and in which run?

| Boundary | Previous direct evidence | H38 attempt 01 direct evidence | Allowed joint inference |
|---|---|---|---|
| Host physical free-page loss | R21/R22 5-s approximate core residual +75,174.387 / +75,138.043 MiB | **+74,761.516 MiB** over 01:59:02.196–01:59:07.196Z | A common-scale early host-memory demand recurs across materially different runtime and host preparation |
| Same-window swap contribution | R21/R22 burst precedes later PLE swap churn | **0.000 MiB SwapFree change** in the 5-s burst | Swap churn is not necessary to produce the initial burst |
| Zone / high-order reservoir | R11: node0 Normal/Unmovable order-4 physical demand; Movable fallback and rollback on failure | **Normal order-4+ -74,508.750 MiB**, node0 Normal all free -75,157.254 MiB in same five seconds | Compatible with the previously demonstrated high-order page pressure, not proof of identical page owners |
| NVIDIA driver carrier | R23 traced `nv_alloc_pages` / `nv_alloc_system_pages`: **74,537.938 MiB** of order-4 RM *logical activity* inside a **75,083.652 MiB** independent physical residual 5-s burst (**99.273191%**) | **No live RM/UVM entry/return trace was collected in H38 attempt 01**; the strict measured kernel window had **zero RM OOM logs** | Direct RM system-page activity is the strongest established *prior mechanism*, not a directly measured H38 allocation call stack |
| Selected UVM paths | R23 selected UVM PMA/DMA/PMM silent; two `uvm_mem_alloc` calls contain zero RM allocations | No H38 UVM boundary trace | Do not reopen generic UVM tracing or claim UVM absent from H38 without measurement |
| Model construction vs shard fill | R25–R26: ~3.2 s RM episode in first `initialize_model()` / constructor, far before long shard fill | Burst overlaps initial **0/18** shard progress; first shard finishes later | Construction/materialization boundary is the highest-value cross-run timing hypothesis |
| Decoder-size request families | R29/R29b: 48 ordinal adjacent `800 MiB -> 400 MiB` pairs; R30 **400 MiB x48** mapped one-to-one to packed w13; R31 all **800 MiB x48** occur *before* MoE create-weights | No per-request sizes or kernel call attribution inside the H38 evidence archive | Do not label a particular H38 tensor as 400/800 MiB owner from the earlier request histogram |
| 800 MiB source syntax | R32 exact **R28 diagnostic image**: no distinct direct pre-`create_weights` model-tensor allocation syntax in scoped factory/routed constructor | No exact **H38 installed-image** source contract or RM requests captured during this H38 startup | R32 favors a discrete RM/CUDA backing-growth mechanism in *its measured stack*; it does not certify the H38 image independently |

**Do not numerically equate** R23 logical requested RM activity with H38 physical resident-page accounting. R23 is same-window temporal/size evidence in **R23**; there is no cross-run 99.27% coverage measurement for H38.

## Existing driver and constructor closure — preserve, do not repeat

R11 directly showed the RM 64 KiB logical request using order-4 Linux Unmovable pages, stealing/splitting Movable blocks under scarcity, rolling back accumulated high-order pages when allocation fails, and then succeeding through order-0 fallback. An apparent post-failure buddy reservoir can therefore include recently rolled-back pages and cannot be interpreted as pre-failure availability.

R23 narrowed the *observed driver endpoint* to successful direct NVIDIA RM system-page allocation. The selected UVM allocation boundaries were either silent or did not nest any observed RM calls. Later strict RM OOM failures occurred after that large early successful allocation episode.

R26 localized most (~76,846 MiB) of the RM activity to the top-level model constructor. Of this constructor activity, ModelOpt MoE `create_weights` intervals explained **34,292 MiB**, while **42,554 MiB** remained outside those intervals. R29 decomposed one repeated part of that activity into 48 800 MiB and 48 400 MiB logical request families. R30 directly associated the 400 MiB family with packed `w13_weight`. R31 proved that all 48 preceding 800 MiB requests occur before `ModelOptNvFp4FusedMoE.create_weights()`. R32 did **not** identify an explicit separate 800 MiB tensor and did **not** establish an original userspace CUDA allocator caller.

The strongest existing interpretation is therefore **repeated driver backing/reservation growth related to decoder construction**, *not* a confirmed dedicated 800 MiB weight per layer and *not* a confirmed causal CUDA API. R28 reproduced the structural RM burst with zero strict RM OOM, so the burst alone does not imply inevitable RM failure.

## H38 image provenance and the exact-image limitation

The repository's H38 build path is:

```text
vLLM v0.29 -> H9/H10 -> H11 packed ModelWeightParameter
  -> H12 post-load object-preserving rename -> H38 decoder-scope runtime
```

Repository source inspection confirms:

1. `scripts/Dockerfile.v029-h11-ct-packed-modelweight` applies `patch-v029-ct-moe-packed-modelweight.py`. The patch preserves the OrcaRouter packed weight tensor shape and the `torch.empty` call but changes the containing parameter type from `torch.nn.Parameter` to `ModelWeightParameter` **within `create_weights()`**. This is not evidence of suppressing RM backing growth.
2. `scripts/Dockerfile.v029-h12-ct-postload-preserve` applies `patch-v029-ct-moe-postload-preserve-weight-param.py`, changing later post-load packed-to-weight renaming/wrapping. The early 5-s physical burst precedes shard weight completion; this later patch has **no demonstrated causal effect** on that first burst.
3. `scripts/Dockerfile.v029-h38-decoder-scope` layers Humming FP8 batch-invariance, compressed-tensors Marlin layer tagging and decoder-tagged Marlin token canonicalization. The canonical ordering helper is applied on the Marlin routed-token runtime path; its code presence does not establish any influence on pre-shard constructor allocation.
4. **R32 exact-image syntax was validated on `vllm-orcarouter-v029-r28-unquant-linear-marker:v1`**, not the deployed H38 `vllm-orcarouter-v029-h38-decoder-scope:v1`. The R32 source-negative claim must stay attached to that R28 image and must not be copied as an H38 installed-image result.

The H38 attempt 01 *runtime identity* was attested by its guard, but its archived data do not include per-call `nv_alloc_pages` traces or an exact-image R32-equivalent source capture. The patched source reading above is repository-level **static review**, not an exact installed-image runtime test.

## Mechanism decisions and stop conditions

**Established:** (A) H38 shares the same-scale, pre-swap physical-page burst; (B) existing R23 directly attributes its own comparable burst to RM system-page activity; (C) R26–R32 close model-component temporal localization and favor backing-growth for the 800 MiB family; (D) R11 establishes the order-4 Unmovable/Movable and RM rollback/fallback failure mechanism.

**Supported but unproven transfer:** H38 most plausibly exercises a related RM allocator/backing-growth demand early in model construction. This is a *mechanism transfer hypothesis*, not a newly observed H38-specific RM call stack, allocator user, per-page owner, or a proof that the H38 protected stop would become strict RM OOM.

**Not established:** Whether changing ModelWeightParameter/H11 or post-load H12 reduces that initial demand; which CUDA allocator boundary triggers each 800 MiB RM request; how much of R23 logical activity is retained as H38 resident pages; an H38-safe Normal order-4+ threshold; or whether the current monitor would be safe to loosen.

**Work specifically not authorized by this document:** Repeat H38 candidate without a new variable; increase or disable protection; alter UFW/VM/sysctl/compaction/drop-cache; add broad UVM/CUDA/Python/kprobe tracing; instrument more model-prefix/Linear/hyper-connection markers; promote managed H38; Ready/merge PR #259; or turn H11/H12 into an unqualified production mitigation.

## Smallest information-gaining next step (static only)

1. Preserve the full archived H38 timeline as the baseline and the R23/R28 raw traces as distinct historical comparators. **Do not require another live host run just to repeat the burst.**
2. If and only if an actionable mitigation is specified, first perform a **read-only exact-H38-image source/patch contract** using the existing guarded image and `R32` checker methodology. Verify any claimed code change before a new allocator trace is considered; repository patch-text inspection alone is not exact-image verification.
3. Define the intervention's mechanism in advance: the concrete allocator/backing transition it modifies, expected change in **same-window logical RM request volume** and **physical free-page accounting**, and an independently valid host-protection/strict-RM test. Do not accept readiness or a single absence of RM OOM as mitigation.
4. A narrower R33 is **optional** only after the previous step yields a specific change whose acceptance truly depends on distinguishing the lower CUDA/RM backing transition. No R33 is implied or currently authorized.

For this PR, the immediate correct decision is **recorded cause-chain closure with H38-specific attribution still unmeasured**, retain the protected-stop gate and keep the managed promotion blocked.

## Prepared but not executed: exact H38 installed-image source preflight

A minimum-scope CPU-only source-contract preflight is now staged at
`orcarouter-h38-exact-image-source-contract-plan-20261008.md`, with
source-only runner `scripts/benchmark/check-h38-exact-image-source.sh`
and installed-source inspector `scripts/benchmark/inspect-h38-exact-image-source.py`.
It reuses R32 as a separate check **on the H38 image**, and verifies
H11/H12 allocation/alias syntax and H38 runtime patch sources.
It creates only one transient unprivileged no-network/no-GPU runc
inspector container, without loading vLLM or changing the managed
service. **No DGX execution is claimed by this staged source code.**
An eventual PASS would not establish fewer RM bytes or a safe managed
startup. R33 live tracing remains unauthorized.

## Exact-H38-installed-image contract — observed DGX PASS

The previously planned source-only check was executed on the original
H38 image (checkout `1a4416581f4064baa110fc83947c442c360c4689`,
image ID `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`)
and produced `H38_EXACT_IMAGE_SOURCE_PREFLIGHT=PASS` with exit code 0.
Canonical result:
`orcarouter-h38-exact-image-source-contract-result-20261008.md`.
This **closes the H38-specific direct source syntax gap** identified
above: exact H38 installed source passes the original R32 direct precreate
allocation syntax contract, without cloning the earlier R28 live
allocation trace into this run. H11 still retains the packed `torch.empty`
requests, H12 preserves parameter objects, and H38 runtime patch
source guards pass. The unknown CUDA/RM backing-growth caller and
H38 HOST-STABILITY qualification remain **open/unproven**; no live
R33, memory-protection change, service migration, promotion or merge.
