# OrcaRouter R28b — unquantized Linear per-call RM pattern plan — 2026-10-05

## Status

**COMPLETED — READ-ONLY POST-HOC PASS — `R28B_HYPER_CONNECTION_RM_ACTIVITY_SPARSE_ACROSS_CALLS` — NO NEW LIVE RUN AUTHORIZED**

Canonical predecessor:

- `orcarouter-r28-unquant-linear-boundary-result-20261005.md`

Canonical result:

- `orcarouter-r28b-unquant-call-pattern-result-20261005.md`

R28 closed as:

**VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY PASS — BURST_UNCHANGED — `RM_ORDER4_R26_RESIDUAL_MIXED_OUTSIDE_UNQUANTIZED_LINEAR_CONSTRUCTION`**

R28 reproduced the same structural direct-RM burst without any strict RM OOM:

- order-4 calls/activity: `526` / `77405.938 MiB`;
- largest five-second residual: `77923.969 MiB`;
- R22 ratio: `103.707743%`;
- burst band: `BURST_UNCHANGED`;
- strict RM OOM count: `0`.

This proves only that the burst can reproduce without an OOM in a valid run. It does not show burst mitigation.

## Why R28b

R28 localized `36752.000 MiB` of the `42554.375 MiB` R26 non-MoE residual inside unquantized Linear construction (`86.364798%`). The largest family was:

- `hyper_connection`: `194` calls, `25600.000 MiB` RM activity, `1242.500 MiB` nominal payload.

Several individual calls aligned with `800.000 MiB` RM activity while requesting only roughly `6.25–6.56 MiB` nominal BF16 payload.

Before adding another live marker, R28b tested whether this was a sparse/discrete RM request pattern across many small constructor calls.

## Analyzer

`scripts/benchmark/analyze-orcarouter-r28b-unquant-call-patterns.py`

Input is the preserved R28 evidence only:

`/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005`

The analyzer reads:

- `candidate-container.log`;
- `rm-trace.txt`;
- the existing wall/monotonic anchors;
- `host-page-size.txt`.

It does not invoke Docker, systemd, CUDA, sudo, tracefs, or the model runtime.

## Completed result

Across 678 selected unquantized Linear calls:

```text
positive_rm_calls=56
zero_rm_calls=622
positive_rm_call_pct=8.259587
```

The positive-call/request histogram is:

```text
20 MiB x 9
30 MiB x 1
128 MiB x 1
800 MiB x 44
1214 MiB x 1
```

Payload/RM correlation diagnostics:

```text
payload_rm_pearson_all=0.149977822
payload_rm_pearson_positive=-0.035821511
```

Hyper-connection closes as a sparse placement boundary:

```text
calls=194
positive=32
zero=162
rm_activity_mib=25600.000
nominal_payload_mib=1242.500
positive_request_histogram=800.000 MiB x 32
```

Both main hyper components carry the same fixed positive chunk:

```text
input_mix_weight_down_block_inject: 21 positive / 16800 MiB
input_mix_weight_up:                11 positive /  8800 MiB
```

The uncovered R26 residual remains `5802.375 MiB` and itself contains:

```text
800 MiB x 4
1214 MiB x 1
```

plus smaller repeated requests.

Read-only non-mutation passed:

- managed container ID unchanged;
- managed `StartedAt` unchanged;
- `model_restart=NO`;
- `candidate_launch=NO`;
- `kprobe_change=NO`;
- `evidence_mutation=NO`.

## Interpretation

The R28b observation satisfies the plan's allocator-growth branch:

- only a minority of hyper-connection calls carry RM activity;
- all RM-positive hyper calls align with exactly one fixed `800 MiB` request;
- the same `800 MiB` request size also appears in other families and outside unquantized Linear intervals;
- nominal payload does not scale with the positive RM activity.

Therefore another model-component boundary marker is lower value than a global allocator/backing-growth discriminator.

This remains a temporal observation. It does not prove exact resident ownership or identify a CUDA/RM policy responsible for the repeated chunk.

## Final discriminator

```text
R28B_HYPER_CONNECTION_RM_ACTIVITY_SPARSE_ACROSS_CALLS
```

## Next direction

Use the preserved R28 evidence first. The next read-only discriminator should classify the **entire constructor RM order-4 stream**, especially `800 MiB` / `1214 MiB` events, against inherited ModelOpt-MoE, Qwen4 layer and unquantized Linear intervals.

The goal is to decide whether repeated large requests behave as a global backing/reservation growth cadence independent of the current model family.

No R29 live run is authorized by this plan. H11 remains deferred.

PR #244 remains open and unmerged.
