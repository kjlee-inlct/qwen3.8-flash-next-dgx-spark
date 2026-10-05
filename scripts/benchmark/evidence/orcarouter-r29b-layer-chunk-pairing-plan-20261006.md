# OrcaRouter R29b — decoder-layer 800/400 MiB chunk pairing post-hoc plan — 2026-10-06

## Status

**IMPLEMENTED — READ-ONLY POST-HOC ONLY — CI REQUIRED — NO NEW LIVE RUN AUTHORIZED**

Canonical predecessor:

- `orcarouter-r29-global-rm-chunk-cadence-result-20261006.md`

R29 closed as:

```text
R29_REPEATED_LARGE_RM_CHUNKS_SPAN_MULTIPLE_CONSTRUCTOR_BOUNDARIES
```

Key R29 observations:

- selected constructor: `464` order-4 requests / `76846.375 MiB`;
- repeated large requests: `400 MiB x48`, `800 MiB x48`, `1214 MiB x2`;
- `400 MiB x48` is entirely inside ModelOpt-MoE marker windows;
- `800 MiB x48` spans `unquant_linear:44` and `other_ctor:4`;
- both 400 MiB and 800 MiB series recur at almost identical ~52 ms median cadence;
- the first visible placements show ordinal stream adjacency such as `800 stream 48 -> 400 stream 49`, `60 -> 61`, and `68 -> 69`;
- R27 already established exactly `48` selected decoder layers.

These observations justify one more read-only discriminator before adding lower-level allocator instrumentation.

## Objective

Determine whether the repeated `800 MiB` and `400 MiB` request streams form a deterministic **two-phase per-decoder-layer cadence**.

The primary questions are:

1. Are there exactly 48 requests of each size inside the selected constructor?
2. When the two size series are paired by chronological ordinal, is each `800 MiB` request before its corresponding `400 MiB` request?
3. Are paired requests adjacent in the full selected order-4 request stream?
4. Does the 400 MiB series map exactly once to each of the 48 inherited decoder-layer intervals?
5. Are the four R29 `800 MiB` requests classified as `other_ctor` explainable as userspace marker-boundary shifts relative to the layer-locked pair cadence?

This remains a temporal-pattern analysis. It does not assert causal ownership or an allocator policy quantum.

## Analyzer

`scripts/benchmark/analyze-orcarouter-r29b-layer-chunk-pairing.py`

Input:

`/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005`

Read-only inputs:

- `candidate-container.log`;
- `rm-trace.txt`;
- wall/monotonic anchors;
- `host-page-size.txt`.

Inherited markers:

- R26 selected model constructor;
- R27 Qwen4Exp decoder-layer intervals.

No Docker, systemd, CUDA launch, sudo, tracefs mutation, probe creation, or evidence mutation is performed.

## Outputs

The analyzer reports:

- selected decoder-layer count;
- `400 MiB` and `800 MiB` request counts;
- chronological ordinal pair count;
- count of pairs where 800 MiB precedes 400 MiB;
- count of pairs adjacent in the order-4 stream;
- pair stream-index delta histogram;
- pair time-delta min/median/max;
- active-layer relationship histogram between the two pair members;
- exact-once/missing/multiple layer coverage separately for 400 MiB and 800 MiB;
- per-layer 400/800 counts;
- every ordinal pair with stream index, time delta, active layers, and layer relation.

## Discriminators

```text
R29B_STRICT_800_THEN_400_ADJACENT_PAIR_PER_DECODER_LAYER
R29B_800_THEN_400_TWO_PHASE_CADENCE_PER_DECODER_LAYER
R29B_800_400_CADENCE_NOT_STRICTLY_LAYER_PAIRED
```

The strict discriminator requires:

- selected layer count > 0;
- number of 400 MiB requests == selected layer count;
- number of 800 MiB requests == selected layer count;
- all selected layers contain exactly one 400 MiB request;
- every ordinal pair is ordered `800 -> 400`;
- every ordinal pair is adjacent in the full selected order-4 stream.

The second discriminator relaxes only the adjacency requirement while retaining equal counts, exact 400 MiB layer coverage, and `800 -> 400` order.

## Interpretation gate

If the strict discriminator passes, treat the R29 cross-boundary placement of 800 MiB requests as insufficient evidence for global allocator ownership. The stronger observed structure is a deterministic layer-construction two-phase request cadence. The next investigation should inspect the exact userspace/CUDA allocation calls bracketing the paired phases rather than broadening RM/kernel tracing.

If only the relaxed two-phase discriminator passes, quantify what requests intervene between 800 MiB and 400 MiB before deciding whether the next boundary belongs in userspace or allocator internals.

If neither passes, retain the broader R29 allocator/backing-growth hypothesis and design the next narrow lower-level discriminator from that closure.

RM bytes remain logical direct-RM allocation activity volume, not exact resident ownership. Marker alignment remains temporal localization, not causal proof.

## Safety / execution policy

R29b is post-hoc only.

- no model restart;
- no candidate model launch;
- no new diagnostic image;
- no new kprobe group;
- no persistent VM tuning;
- no R28 evidence mutation.

No R29b live run is authorized. H11 remains deferred.

PR #244 remains open and unmerged.
