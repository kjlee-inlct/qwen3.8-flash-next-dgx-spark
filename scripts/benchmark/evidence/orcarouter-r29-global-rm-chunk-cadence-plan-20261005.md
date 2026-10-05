# OrcaRouter R29 — global RM chunk cadence post-hoc plan — 2026-10-05

## Status

**COMPLETED — READ-ONLY POST-HOC PASS — NO NEW LIVE RUN AUTHORIZED**

Canonical predecessor:

- `orcarouter-r28b-unquant-call-pattern-result-20261005.md`

Canonical result:

- `orcarouter-r29-global-rm-chunk-cadence-result-20261006.md`

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

This made another model-component split lower value than checking whether repeated large RM requests span multiple inherited constructor boundaries.

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

## Completed result

R29 completed read-only with:

```text
constructor_order4_request_count=464
constructor_order4_activity_mib=76846.375
repeated_large_request_sizes_mib=400.000,800.000,1214.000
spanning_repeated_large_request_sizes_mib=800.000,1214.000
r29_discriminator=R29_REPEATED_LARGE_RM_CHUNKS_SPAN_MULTIPLE_CONSTRUCTOR_BOUNDARIES
```

The three repeated large-size series are:

```text
400 MiB x48  -> modelopt_moe:48
800 MiB x48  -> unquant_linear:44, other_ctor:4
1214 MiB x2  -> unquant_linear:1, other_ctor:1
```

The 400 MiB and 800 MiB streams both recur at nearly identical ~52 ms median cadence. The visible event stream also shows ordinal adjacency such as `800 -> 400` at request indices `48 -> 49`, `60 -> 61`, and `68 -> 69`.

Therefore the strict R29 cross-boundary discriminator is valid, but it is not sufficient by itself to justify immediately instrumenting deeper allocator internals. The equal 48-count series and apparent adjacent ordering introduce a stronger candidate explanation: a deterministic per-decoder-layer two-phase request cadence.

## Interpretation gate

R29 established that repeated `800 MiB` and `1214 MiB` requests span userspace constructor regions, so nearest-prefix alignment must not be promoted to causal ownership.

R29 also established a new follow-up requirement: test the 48-count 800/400 streams as chronological pairs against the 48 inherited decoder layers before choosing a lower allocator boundary.

That follow-up is R29b:

- `orcarouter-r29b-layer-chunk-pairing-plan-20261006.md`
- `scripts/benchmark/analyze-orcarouter-r29b-layer-chunk-pairing.py`

RM bytes remain logical direct-RM allocation activity volume, not exact resident ownership. Marker alignment remains temporal localization, not causal proof.

## Safety / execution policy

R29 was post-hoc only.

- no model restart;
- no candidate model launch;
- no new diagnostic image;
- no new kprobe group;
- no persistent VM tuning;
- no R28 evidence mutation.

No R29 live run is authorized. H11 remains deferred.

PR #244 remains open and unmerged.
