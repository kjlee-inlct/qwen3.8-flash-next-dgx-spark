# OrcaRouter R28b — unquantized Linear per-call RM pattern result — 2026-10-05

## Status

**COMPLETED — READ-ONLY POST-HOC PASS — NO MODEL RESTART / NO CANDIDATE LAUNCH / NO KPROBE CHANGE / NO EVIDENCE MUTATION**

Canonical predecessor:

- `orcarouter-r28-unquant-linear-boundary-result-20261005.md`

Input evidence:

- `/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005`

Analyzer:

- `scripts/benchmark/analyze-orcarouter-r28b-unquant-call-patterns.py`

Execution result:

- `R28B_RC=0`
- `R28B_READ_ONLY_POSTHOC=PASS`
- managed container ID unchanged
- managed `StartedAt` unchanged
- `model_restart=NO`
- `candidate_launch=NO`
- `kprobe_change=NO`
- `evidence_mutation=NO`

## Primary finding

R28b shows that direct-RM activity inside unquantized Linear construction is **sparse across calls and dominated by repeated discrete request sizes**, not broadly proportional to the nominal tensor payload of each call.

Across the 678 selected unquantized Linear calls:

```text
selected_unquant_calls=678
positive_rm_calls=56
zero_rm_calls=622
positive_rm_call_pct=8.259587
unquant_residual_activity_mib=36752.000
uncovered_residual_activity_mib=5802.375
```

Per-call RM-activity histogram:

```text
0.000 MiB   : 622 calls
20.000 MiB  : 9 calls
30.000 MiB  : 1 call
128.000 MiB : 1 call
800.000 MiB : 44 calls
1214.000 MiB: 1 call
```

Every positive call contains exactly one selected 64 KiB-path RM request, so the positive-call activity histogram and raw RM request-size histogram are identical.

Nominal payload does not explain the repeated RM request size:

```text
payload_rm_pearson_all=0.149977822
payload_rm_pearson_positive=-0.035821511
```

These correlation values are diagnostic only; they are not causal proof.

## Hyper-connection closure

Hyper-connection was the largest R28 family:

```text
family.hyper_connection.calls=194
family.hyper_connection.positive_rm_calls=32
family.hyper_connection.zero_rm_calls=162
family.hyper_connection.request_count=32
family.hyper_connection.rm_activity_mib=25600.000
family.hyper_connection.nominal_payload_mib=1242.500
```

The distribution is exact and discrete:

```text
hyper_connection.activity_histogram_mib=0.000:162,800.000:32
hyper_connection.positive_activity_histogram_mib=800.000:32
hyper_connection.request_size_histogram_mib=800.000:32
```

Thus only `16.494845%` of hyper-connection calls align with selected RM activity, and every positive one aligns with exactly one `800 MiB` RM request.

Both main hyper-connection components participate:

```text
input_mix_weight_down_block_inject: 96 calls / 21 positive / 16800 MiB RM / 630 MiB nominal payload
input_mix_weight_up:                96 calls / 11 positive /  8800 MiB RM / 600 MiB nominal payload
```

The two model-level mixer calls were both RM-zero.

Positive decoder layers are distributed across the model rather than confined to one localized layer region:

```text
1,3,4,5,8,11,12,13,15,16,17,19,20,21,23,24,25,27,28,29,31,32,33,35,36,37,39,40,41,43,44,45
```

Gap histogram:

```text
1:20, 2:9, 3:2
```

## Other families

R28b also shows the same discrete request pattern is not unique to hyper-connection:

```text
self_attn:    36 calls / 12 positive / 8928 MiB RM / 1177.500 MiB nominal payload
linear_attn: 144 calls /  2 positive /  820 MiB RM / 3979.688 MiB nominal payload
other:       110 calls /  9 positive / 1374 MiB RM /  847.055 MiB nominal payload
ple:           2 calls /  1 positive /   30 MiB RM /   62.500 MiB nominal payload
router:       96 calls /  0 positive /    0 MiB RM /  120.234 MiB nominal payload
shared_expert:96 calls /  0 positive /    0 MiB RM /  450.000 MiB nominal payload
```

The global positive-call histogram is exactly:

```text
20 MiB x 9
30 MiB x 1
128 MiB x 1
800 MiB x 44
1214 MiB x 1
```

The repeated `800 MiB` request therefore crosses multiple model families and is not unique to one hyper-connection tensor shape or component.

## Uncovered R26 residual

The R28 residual left outside unquantized Linear intervals is:

```text
uncovered_residual_activity_mib=5802.375
uncovered.request_count=51
```

Request-size histogram:

```text
0.125 MiB x 3
2 MiB x 1
20 MiB x 34
24 MiB x 1
30 MiB x 1
42 MiB x 1
66 MiB x 1
80 MiB x 2
128 MiB x 1
256 MiB x 1
800 MiB x 4
1214 MiB x 1
```

The uncovered set therefore also contains the same large discrete `800 MiB` and `1214 MiB` request sizes seen inside unquantized Linear windows. Several uncovered requests fall between adjacent constructor prefixes, including transitions around PLE, attention, hyper-connection and shared-expert construction.

This weakens the hypothesis that an individual unquantized Linear component directly owns the repeated large RM request volume.

## Interpretation boundary

R28b supports the following engineering conclusion:

> The R28 unquantized-Linear temporal localization is primarily a placement boundary for sparse, discrete RM allocation events. The dominant repeated `800 MiB` request is not proportional to nominal tensor payload and appears across multiple model families and between unquantized Linear intervals.

This makes another model-component marker split lower value than an allocator/backing-growth discriminator.

It does **not** establish:

- exact resident ownership;
- that CUDA itself requests 800 MiB at a public API boundary;
- that the NVIDIA RM driver has a fixed 800 MiB growth policy;
- that the preceding tensor allocation causally owns the RM request;
- that the observed RM request is a persistent resident allocation rather than allocation activity.

RM bytes retain the established semantics: logical allocation activity volume, not exact resident ownership. Userspace alignment remains temporal localization, not causal proof.

## Final discriminator

```text
R28B_HYPER_CONNECTION_RM_ACTIVITY_SPARSE_ACROSS_CALLS
```

## Next direction

Do **not** launch another model-component live marker experiment yet.

The next discriminator should be post-hoc first and should ask whether the repeated large RM requests form a global allocation/backing-growth cadence across the entire constructor stream, independent of the model family currently executing.

Priority questions:

1. classify the full constructor order-4 RM request-size histogram, not only R28 residual calls;
2. locate every `800 MiB` and `1214 MiB` request against inherited R26 ModelOpt-MoE, R27 layer and R28 unquantized intervals;
3. measure inter-request timing and sequence spacing for repeated large requests;
4. compare repeated large requests with cumulative nominal model payload since the previous large RM event, without interpreting that payload as ownership;
5. determine whether the large discrete requests span ModelOpt-MoE, unquantized Linear and uncovered constructor regions.

Only if that post-hoc global stream cannot discriminate the pattern should a new live CUDA/RM boundary experiment be considered.

No R29 live run is authorized by this result. H11 remains deferred.

PR #244 remains open and unmerged.
