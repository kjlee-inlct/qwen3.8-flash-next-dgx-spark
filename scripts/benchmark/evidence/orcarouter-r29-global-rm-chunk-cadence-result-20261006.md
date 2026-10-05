# OrcaRouter R29 — global RM chunk cadence post-hoc result — 2026-10-06

## Status

**COMPLETED — READ-ONLY POST-HOC PASS — NO MODEL RESTART / NO CANDIDATE LAUNCH / NO NEW IMAGE / NO KPROBE CHANGE / NO EVIDENCE MUTATION**

Canonical predecessor:

- `orcarouter-r28b-unquant-call-pattern-result-20261005.md`

Input evidence:

- `/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005`

Analyzer:

- `scripts/benchmark/analyze-orcarouter-r29-global-rm-chunk-cadence.py`

Execution result:

```text
R29_RC=0
R29_READ_ONLY_POSTHOC=PASS
model_restart=NO
candidate_launch=NO
new_image=NO
kprobe_change=NO
evidence_mutation=NO
```

Managed runtime identity was unchanged across the analysis:

```text
managed_id_before =4ebf6df5860aef7b6e0681792f8b8a58b165dee454a98cc6f4bbb0926d94f321
managed_id_after  =4ebf6df5860aef7b6e0681792f8b8a58b165dee454a98cc6f4bbb0926d94f321
started_before=2026-10-05T12:32:36.149058234Z
started_after =2026-10-05T12:32:36.149058234Z
```

## Full selected-constructor stream

The selected R26 model-constructor interval contains:

```text
model_ctor.duration_s=2.909661
constructor_order4_request_count=464
constructor_order4_activity_mib=76846.375
```

The full request-size histogram is:

```text
0.125:3
2.000:12
14.000:1
20.000:138
24.000:1
30.000:48
42.000:1
50.000:49
66.000:24
80.000:36
100.000:48
128.000:3
160.000:1
256.000:1
400.000:48
800.000:48
1214.000:2
```

Repeated large requests (`>=256 MiB`, count >=2) are therefore:

```text
400.000 MiB x48
800.000 MiB x48
1214.000 MiB x2
```

## Region distribution

Temporal placement against inherited R26/R28 boundaries is:

```text
region.modelopt_moe.request_count=357
region.modelopt_moe.activity_mib=34292.000

region.unquant_linear.request_count=56
region.unquant_linear.activity_mib=36752.000

region.other_ctor.request_count=51
region.other_ctor.activity_mib=5802.375
```

The `400 MiB` series is region-localized:

```text
size_mib=400.000
count=48
regions=modelopt_moe:48
layer_types=linear_attention:36,qwen_sparse_attention:12
```

Its recurrence cadence is highly regular:

```text
interarrival_ms=min=51.083000 median=52.194000 max=87.506000
intervening_order4_requests=min=7 median=8.000 max=13
```

The first 24 placements show one `400 MiB` request in each successive decoder layer 0 through 23, and the total count is exactly 48, matching the selected 48-layer decoder stack observed in R27.

The `800 MiB` series also occurs exactly 48 times but spans inherited regions:

```text
size_mib=800.000
count=48
regions=other_ctor:4,unquant_linear:44
layer_types=linear_attention:25,qwen_sparse_attention:23
```

Its recurrence cadence is nearly identical to the 400 MiB series:

```text
interarrival_ms=min=50.982000 median=52.182000 max=87.571000
intervening_order4_requests=min=7 median=8.000 max=13
```

The `1214 MiB` series occurs twice:

```text
size_mib=1214.000
count=2
regions=other_ctor:1,unquant_linear:1
layer_types=outside_layer:2
interarrival_ms=2709.210000
intervening_order4_requests=419
```

## Primary discriminator

The strict R29 discriminator is:

```text
spanning_repeated_large_request_sizes_mib=800.000,1214.000
r29_discriminator=R29_REPEATED_LARGE_RM_CHUNKS_SPAN_MULTIPLE_CONSTRUCTOR_BOUNDARIES
```

Therefore model-prefix / constructor-marker placement is not sufficient ownership evidence for the repeated `800 MiB` and `1214 MiB` requests.

This supports the R29 hypothesis that at least some repeated large RM requests are not uniquely owned by one userspace model component boundary.

## Important refinement — do not jump directly to allocator internals yet

R29 also exposes a stronger regularity that was not the original primary discriminator:

- `400 MiB` occurs exactly `48` times;
- `800 MiB` occurs exactly `48` times;
- both series have nearly identical ~`52 ms` median recurrence;
- the first visible stream placements show `800 MiB` immediately followed by `400 MiB` in the order-4 request stream, for example stream indices `48 -> 49`, `60 -> 61`, and `68 -> 69`;
- the `400 MiB` series visibly walks decoder layers sequentially.

This means the next discriminator should first test whether the two large series form a deterministic **per-decoder-layer two-phase RM cadence** before instrumenting a lower allocator/backing boundary.

The current evidence does **not** yet prove:

- exact resident-memory ownership;
- that the 800 MiB request is caused by the nearest unquantized-Linear call;
- that the 400 MiB request is caused by the ModelOpt-MoE marker in a causal sense;
- that the request sizes are an allocator policy quantum rather than model-construction-driven requests.

RM bytes remain logical direct-RM allocation activity volume. Marker alignment remains temporal localization, not causal proof.

## Next direction

Use the same preserved R28 evidence in a read-only R29b analyzer to test:

1. ordinal pairing of all `800 MiB` and `400 MiB` requests;
2. whether every pair is `800 -> 400`;
3. stream-index distance and intervening-request count inside each pair;
4. pair time delta;
5. mapping of each pair to the 48 inherited decoder-layer intervals;
6. layer-type differences between `linear_attention` and `qwen_sparse_attention`;
7. whether userspace boundary shifts explain the four `800 MiB` requests classified as `other_ctor`.

No new live run is justified before that post-hoc pairing closes.

H11 remains deferred.

PR #244 remains open and unmerged.
