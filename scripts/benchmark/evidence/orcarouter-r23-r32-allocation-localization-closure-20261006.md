# OrcaRouter R23–R32 — early RM allocation localization closure

Status: **CLOSED FOR MODEL-COMPONENT OWNERSHIP LOCALIZATION — ALLOCATOR/BACKING-GROWTH IS THE BEST-SUPPORTED 800 MiB MECHANISM — NO R33 LIVE RUN AUTHORIZED**

This closure connects the driver-level ownership evidence from R23 to the exact userspace/source localization completed in R32.

## Evidence chain

### R23 — driver endpoint

The common early burst is dominated by direct NVIDIA RM system-memory allocation activity through `nv_alloc_pages` / `nv_alloc_system_pages`, not the selected UVM allocation boundaries. Same-window RM activity accounted for about 99.27% of the measured residual-growth burst.

### R24 — H6 is not a burst mitigation

The H6 W4A16 config-only candidate reproduced the same structural burst and a strict RM OOM. It is not a host-stability mitigation.

### R25 / R25b — first model construction

The order-4 RM episode is only about 3.2 seconds and is concentrated in the first `initialize_model()` / immediate model-construction phase, long before the hundreds-of-seconds checkpoint fill completes.

### R26 — constructor / ModelOpt-MoE split

The primary constructor contains `76846.250 MiB` of the traced RM activity. ModelOpt-MoE create-weights accounts for `34292.000 MiB`, leaving about `42554 MiB` in other constructor work.

### R27 / routing closure

The residual localizes to the 48 Qwen4Exp decoder-layer construction intervals. The H6 ignore/exclusion routing explains why the ordinary dense W4A16 method marker is not selected for the attention families; those paths route through unquantized Linear construction.

### R28 / R28b — sparse fixed-size pulse behavior

R28 reproduced the same structural burst even in a valid run with `rm_oom_count=0`, proving that strict RM OOM is not required for the burst itself.

R28b showed that RM activity does not scale with nominal unquantized Linear payload in a simple way:

- selected unquantized Linear calls: `678`;
- RM-positive calls: `56` (`8.259587%`);
- RM-zero calls: `622`;
- positive call histogram is dominated by fixed `800 MiB` events;
- payload/RM Pearson is about `0.150` overall and `-0.036` among positive calls;
- hyper-connection specifically has `32` positive calls and every one is exactly one `800 MiB` request, while `162` hyper-connection calls are zero-RM.

This demotes nearest-prefix temporal overlap as an ownership signal.

### R29 — global cadence

Within the selected constructor:

- order-4 requests: `464`;
- order-4 activity: `76846.375 MiB`;
- `400 MiB x48`;
- `800 MiB x48`;
- `1214 MiB x2`.

The 400 and 800 series both recur at roughly 52 ms median cadence. The 800 MiB family spans inherited userspace regions, so those region markers cannot uniquely own it.

### R29b — strict ordinal adjacency

All 48 ordinal pairs are:

`800 MiB -> 400 MiB`

with:

- `pair_800_before_400_count=48`;
- `pair_adjacent_stream_count=48`;
- `pair_stream_delta_histogram=1:48`;
- median pair delta about `24.925 ms`.

The 400 MiB requests map exactly once to all 48 decoder-layer intervals, while inherited 800-layer placement is non-unique. The corrected semantic closure is therefore strict ordinal cadence, not one unique 800 event per layer marker.

### R30 — exact w13 ownership of 400 MiB

R30 closes the 400 MiB family event-by-event:

- selected w13 intervals: `48`;
- constructor 400 MiB requests: `48`;
- exactly one 400 MiB request in every w13 interval: `48/48`;
- no 400 MiB constructor requests outside w13 intervals;
- `400 MiB * 48 = 19200 MiB`, exactly matching the earlier R26 w13 aggregate.

Therefore the 400 MiB family is directly localized to packed-expert `w13_weight` construction.

Each 400 MiB event also has an immediately preceding 800 MiB request. All 48 preceding 800 MiB requests occur before W13 BEGIN, with median timing:

- 800 -> W13 BEGIN: `8.100208 ms`;
- W13 BEGIN -> 400: `16.894804 ms`.

The preceding 800 userspace placement remains mixed:

- hyper_connection: `32`;
- self_attn: `11`;
- linear_attn: `1`;
- outside_unquant: `4`.

No family reaches the 90% ownership threshold.

### R31 — 800 MiB is before ModelOpt create_weights

All 48 800 MiB precursors occur before `ModelOptNvFp4FusedMoE.create_weights()` begins:

- 800 before MoE BEGIN: `48/48`;
- 800 inside MoE pre-w13: `0`;
- 800 inside w13: `0`;
- median 800 -> MoE BEGIN: `8.070243 ms`;
- median MoE BEGIN -> W13 BEGIN: only `0.028849 ms`.

Discriminator:

`R31_PRE800_STRICTLY_BEFORE_MODELOPT_MOE_BEGIN`

Thus the 800 MiB family is not the ModelOpt packed w13/w2 allocation body.

### R32 — exact-image source contract

Attempt01 and Attempt02 are preserved as checker-invalid and make no source-closure claim.

Corrected Attempt03 passed on exact R28 image `sha256:54c1ae1ba05fc34ec10881db4e5a333895eebf5472a5d282fefa354fe39a762f`:

- Qwen4 attention construction precedes MLP: PASS;
- Qwen4 hyper-connection construction follows MLP: PASS;
- installed Sparse-MoE gate: `ReplicatedLinear`, line 170;
- installed shared-expert gate: `ReplicatedLinear`, line 178;
- `FusedMoEFactory`, line 215;
- Sparse-MoE gate/shared-gate before factory: PASS;
- RoutedExperts ordering contract: PASS;
- direct tensor-allocation syntax in FusedMoEFactory before RoutedExperts construction: `0`;
- direct tensor-allocation syntax in RoutedExperts before quant-method `create_weights()`: `0`;
- `direct_precreate_tensor_alloc_syntax=ABSENT`.

Discriminator:

`R32_NO_DIRECT_PRECREATE_WEIGHT_ALLOCATION_SUPPORTS_ALLOCATOR_BACKING_GROWTH`

Managed container ID and `StartedAt` were identical before/after the read-only inspection.

## Final engineering closure

### 400 MiB family

**Closed to packed w13 construction.**

This is the only repeated large family in this chain with exact one-to-one event-level userspace allocation-boundary localization.

### 800 MiB family

The evidence does **not** support treating the nearest model prefix or a distinct explicit model weight as its causal owner:

- it occurs 48 times in a strict ordinal cadence immediately before the 48 w13-associated 400 MiB events;
- nominal payload size does not explain it;
- nearest userspace family placement is mixed;
- every event occurs before ModelOpt `create_weights()` begins;
- exact-image pre-create source contains no separate direct model-tensor allocation syntax matching an 800 MiB owner.

The best-supported interpretation is:

**the 800 MiB family is a discrete CUDA/NVIDIA RM backing/reservation growth event triggered during the repeated decoder-layer construction cycle rather than a distinct 800 MiB model-component weight allocation.**

This is a mechanism-level inference, not proof of the exact lower-level allocator call. Helper constructors can contain indirect allocation behavior; R32 deliberately does not claim otherwise.

## Host-stability interpretation

The structural ~77.4 GiB order-4 burst can occur with or without strict RM OOM. Therefore:

- burst presence is the structural condition;
- `NV_ERR_NO_MEMORY` is an outcome that depends on host-memory/fragmentation margin during that burst;
- a clean single run does not convert H6 into a mitigation;
- any valid future run with confirmed RM OOM remains HOST-STABILITY FAIL even if fallback reaches READY.

## Investigation boundary

The following line of investigation is now closed:

`model prefix -> component marker -> more component marker -> 800 MiB owner`

Do not add more Qwen4/Linear/hyper-connection/model-prefix markers for this question.

R33 is optional, not required for the model-component root-cause closure. A new live R33 is justified only if an actionable mitigation depends on distinguishing the exact lower allocator/backing transition that emits the 800 MiB RM request. Such an R33 must remain narrow and allocator-focused.

Do not broaden to UVM, generic page allocation, scheduler tracing, function graph, blanket CUDA API tracing, broad Python profiling, or broad memory-tuning experiments.

H11 remains deferred until its current-project meaning and validation target are made unambiguous. PR #244 remains open/unmerged.