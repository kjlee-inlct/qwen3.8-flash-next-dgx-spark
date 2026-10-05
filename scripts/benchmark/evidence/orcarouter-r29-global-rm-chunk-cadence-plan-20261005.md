# OrcaRouter R29 — global RM chunk cadence post-hoc plan — 2026-10-05

## Status

**IMPLEMENTED — READ-ONLY POST-HOC ONLY — CI REQUIRED — NO NEW LIVE RUN AUTHORIZED**

Canonical predecessor:

- `orcarouter-r28b-unquant-call-pattern-result-20261005.md`

R28b closed as:

```text
R28B_HYPER_CONNECTION_RM_ACTIVITY_SPARSE_ACROSS_CALLS
```

Key R28b observations:

- 678 selected unquantized Linear calls;
- only 56 RM-positive calls (`8.259587%`);
- 622 RM-zero calls;
- positive-call histogram dominated by `800 MiB x 44`;
- hyper-connection: 194 calls, 32 positive, all positive calls exactly `800 MiB x 1 request`;
- uncovered R26 residual still contains `800 MiB x 4` and `1214 MiB x 1`;
- payload/RM Pearson diagnostics are weak (`0.149977822` overall, `-0.035821511` positive-only).

This makes another model-component split lower value than checking whether repeated large RM requests span multiple inherited constructor boundaries.

## Objective

Use the already preserved R28 trace to classify the **entire selected model-constructor order-4 RM request stream**, not just the R28 unquantized-Linear residual.

The discriminator asks:

> Do repeated large RM request sizes recur across ModelOpt-MoE, unquantized Linear, and other constructor regions, consistent with a global backing/reservation growth cadence rather than one model component's nominal tensor payload?

This remains a temporal-pattern question. It does not assert exact ownership or a specific CUDA/RM allocation policy.

## Analyzer

`scripts/benchmark/analyze-orcarouter-r29-global-rm-chunk-cadence.py`

Input:

`/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005`

Read-only inputs:

- `candidate-container.log`;
- `rm-trace.txt`;
- wall/monotonic anchors;
- `host-page-size.txt`.

Inherited boundaries:

- R26 selected model constructor;
- R26 ModelOpt-MoE create-weights intervals;
- R27 Qwen4Exp decoder-layer intervals;
- R28 unquantized Linear intervals.

No Docker, systemd, CUDA launch, sudo, tracefs mutation, probe creation, or evidence mutation is performed.

## Outputs

The analyzer reports:

1. full selected-constructor order-4 request count/activity;
2. full constructor request-size histogram;
3. repeated large request sizes, defined as `>=256 MiB` and observed at least twice;
4. request count/activity by temporal region:
   - `modelopt_moe`;
   - `unquant_linear`;
   - `modelopt_moe+unquant_linear` if any overlap exists;
   - `other_ctor`;
5. for each repeated large size:
   - total count;
   - temporal-region distribution;
   - R27 layer-type distribution;
   - min/median/max interarrival time;
   - min/median/max intervening order-4 request count;
   - up to 24 individual event placements with active layer and nearest R28 unquantized prefix;
6. whether a repeated large size spans at least two constructor-region classes.

## Possible discriminators

```text
R29_REPEATED_LARGE_RM_CHUNKS_SPAN_MULTIPLE_CONSTRUCTOR_BOUNDARIES
R29_REPEATED_LARGE_RM_CHUNKS_REGION_LOCALIZED
R29_NO_REPEATED_LARGE_RM_CHUNK_PATTERN
```

## Interpretation gate

If a repeated large size such as `800 MiB` spans ModelOpt-MoE, unquantized Linear, and other constructor regions, treat model-prefix alignment as a placement boundary rather than ownership evidence and move the next investigation toward a narrow allocator/backing-growth boundary.

If repeated large chunks remain confined to one constructor region, retain that region as the next narrow candidate before instrumenting a lower-level boundary.

If there is no repeated large chunk pattern in the full constructor stream, reassess the R28b local pattern before designing another experiment.

RM bytes remain logical direct-RM allocation activity volume, not exact resident ownership. Marker alignment remains temporal localization, not causal proof.

## Safety / execution policy

R29 is post-hoc only.

- no model restart;
- no candidate model launch;
- no new diagnostic image;
- no new kprobe group;
- no persistent VM tuning;
- no R28 evidence mutation.

No R29 live run is authorized by this plan. H11 remains deferred.

PR #244 remains open and unmerged.
