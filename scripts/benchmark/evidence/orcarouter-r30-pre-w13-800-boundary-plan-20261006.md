# OrcaRouter R30 — pre-w13 800 MiB boundary post-hoc plan — 2026-10-06

## Status

**IMPLEMENTED — READ-ONLY POST-HOC ONLY — NO LIVE RUN AUTHORIZED**

Canonical predecessors:

- `orcarouter-r26-construction-boundary-result-20261005.md`
- `orcarouter-r29-global-rm-chunk-cadence-result-20261006.md`
- `orcarouter-r29b-layer-chunk-pairing-result-20261006.md`

## Motivation

R29 showed:

- `400 MiB x48`;
- `800 MiB x48`;
- both families recur at approximately the same ~52 ms global cadence;
- the 800 MiB family spans userspace constructor regions.

R29b then showed that the 48 ordinal 800/400 pairs are all adjacent in the selected constructor RM stream:

```text
pair_800_before_400_count=48
pair_adjacent_stream_count=48
pair_stream_delta_histogram=1:48
pair_delta_ms=min=24.518 median=24.925 max=27.840
```

However R29b's raw `...PER_DECODER_LAYER` discriminator name overstates the 800-layer placement. The actual R27 layer-marker distribution is:

```text
layer800.exact_once_count=24
layer800.missing_count=12
layer800.multi_count=12
pair_same_layer_count=15
pair_800_prev_layer_count=33
```

The canonical R29b interpretation is therefore ordinal adjacency with non-unique 800-layer placement, not one 800 owner per layer.

A separate R26 fact now becomes decisive:

```text
modelopt_w13.activity_mib=19200.000
```

which numerically equals exactly `400 MiB x48`.

## Objective

Use only the preserved R28 evidence to test whether the constructor's 48 400 MiB requests are **individually one-to-one inside the inherited R26 w13 marker intervals**, and then classify the immediately preceding 800 MiB request.

Questions:

1. Are there exactly 48 selected w13 intervals?
2. Does every w13 interval contain exactly one 400 MiB RM request?
3. Are there any 400 MiB constructor requests outside w13 intervals?
4. Is the immediately preceding constructor RM request 800 MiB for every w13-400 event?
5. Does the 800 MiB request occur before the w13 begin marker?
6. Which R28 unquantized prefix/family is active at each preceding 800 MiB request?
7. How are those 800 MiB placements distributed relative to the inherited R27 layer markers?
8. What are the separate timings:
   - 800 -> w13 begin;
   - w13 begin -> 400;
   - 800 -> 400?

## Analyzer

`scripts/benchmark/analyze-orcarouter-r30-pre-w13-800-boundary.py`

Input:

`/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005`

The analyzer reuses only preserved:

- `candidate-container.log`;
- `rm-trace.txt`;
- wall/monotonic clock anchors;
- host page size;
- inherited R26 w13 markers;
- inherited R27 layer markers;
- inherited R28 unquantized Linear markers.

No service mutation, Docker candidate launch, CUDA model launch, kprobe mutation, image build, or evidence mutation occurs.

## Possible discriminators

```text
R30_EXACT_W13_400_WITH_PRECEDING_800_LOCALIZED_TO_SINGLE_USERSPACE_FAMILY
R30_EXACT_W13_400_WITH_IMMEDIATE_PRECEDING_800_MIXED_USERSPACE_PLACEMENT
R30_W13_400_OR_PRECEDING_800_PATTERN_NOT_EXACT
```

The first discriminator requires exact w13/400/preceding-800 structure and >=90% of preceding 800 events in one R28 userspace family.

The second requires exact w13/400/preceding-800 structure but mixed userspace placement. That outcome would argue that userspace prefix overlap is not a stable owner of the 800 MiB pulse and would prioritize a lower allocator/backing boundary for any later live instrumentation.

The third means the numerical R26/R29 correspondence was not sufficient for exact event-level closure.

## Safety / interpretation

RM logical bytes remain activity volume, not exact resident ownership. Marker overlap remains temporal localization, not causal proof.

No R30 live run is authorized by this plan. H11 remains deferred. PR #244 remains open and unmerged.
