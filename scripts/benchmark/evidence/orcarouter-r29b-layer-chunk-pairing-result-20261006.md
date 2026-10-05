# OrcaRouter R29b — 800/400 layer-chunk pairing result — 2026-10-06

## Status

**COMPLETED — READ-ONLY POST-HOC PASS — RAW PAIRING VALID — DISCRIMINATOR NAME REQUIRES SEMANTIC CORRECTION**

Input evidence:

- `/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005`

Execution preserved the managed runtime exactly:

- managed container ID unchanged;
- managed `StartedAt` unchanged;
- `model_restart=NO`;
- `candidate_launch=NO`;
- `new_image=NO`;
- `kprobe_change=NO`;
- `evidence_mutation=NO`.

## Raw pairing result

The read-only analyzer observed:

```text
selected_layer_count=48
size400_request_count=48
size800_request_count=48
ordinal_pair_count=48
pair_800_before_400_count=48
pair_adjacent_stream_count=48
pair_stream_delta_histogram=1:48
pair_delta_ms=min=24.518000 median=24.925000 max=27.840000
```

The 400 MiB requests map cleanly to the 48 decoder-layer marker intervals:

```text
layer400.exact_once_count=48
layer400.missing_count=0
layer400.multi_count=0
```

However the 800 MiB requests do **not** map one-per-layer under the inherited R27 layer markers:

```text
layer800.exact_once_count=24
layer800.missing_count=12
layer800.multi_count=12
pair_same_layer_count=15
pair_800_prev_layer_count=33
pair_relation_histogram=800_prev_layer:33,same_layer:15
```

The missing 800-layer placements were:

`2,6,9,14,18,22,26,30,34,38,42,46`

and the multi placements were:

`1,3,7,11,15,19,23,27,31,35,39,43`.

## Semantic correction

The analyzer emitted:

`R29B_STRICT_800_THEN_400_ADJACENT_PAIR_PER_DECODER_LAYER`

The **raw adjacency claim is valid**, but the suffix `PER_DECODER_LAYER` is stronger than the analyzer's strict predicate actually proved. The predicate required:

- 48 total 800 MiB requests;
- 48 total 400 MiB requests;
- 48 exact-once 400 MiB layer placements;
- every ordinal 800 before its 400;
- every ordinal pair adjacent in the RM stream.

It did **not** require `layer800.exact_once_count=48`. The observed output itself shows that condition would fail.

Therefore the canonical engineering interpretation is:

`R29B_STRICT_800_THEN_400_ADJACENT_ORDINAL_CADENCE_WITH_NONUNIQUE_800_LAYER_PLACEMENT`

This preserves the valid evidence without turning temporal layer-marker placement into causal ownership.

## Connection to R26

R26 previously measured:

```text
modelopt_w13.activity_mib=19200.000
modelopt_w2.activity_mib=10776.000
```

R29/R29b found exactly `400 MiB x 48 = 19200 MiB` inside the constructor stream. This numerical identity makes the 400 MiB family the highest-value candidate for direct one-to-one verification against the inherited R26 `QWEN38_R26_MODELOPT_W13_BEGIN/END` intervals.

The next read-only discriminator must therefore verify each individual 400 MiB request against the w13 marker intervals, then classify the immediately preceding 800 MiB request by R28 unquantized prefix/family and by timing relative to the w13 begin marker.

## Next direction

Proceed to R30 post-hoc only:

1. verify 48 selected w13 intervals;
2. require exactly one 400 MiB RM request inside each w13 interval;
3. verify all constructor 400 MiB requests are covered by those w13 intervals;
4. for each w13-400 event, inspect the immediately preceding constructor RM request;
5. test whether that preceding request is 800 MiB for all 48 cases;
6. classify that 800 MiB request by active R28 unquantized prefix/family and inherited R27 layer marker;
7. report 800-to-w13-begin and w13-begin-to-400 timing separately.

No R30 live run is authorized by this result. H11 remains deferred. PR #244 remains open and unmerged.
