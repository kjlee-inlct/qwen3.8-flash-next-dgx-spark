# OrcaRouter R28b — unquantized Linear per-call RM pattern plan — 2026-10-05

## Status

**IMPLEMENTED — READ-ONLY POST-HOC ONLY — CI REQUIRED — NO NEW LIVE RUN AUTHORIZED**

Canonical predecessor:

- `orcarouter-r28-unquant-linear-boundary-result-20261005.md`

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

Before adding another live marker, determine whether this is a sparse/discrete RM request pattern across many small constructor calls.

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

## Outputs

The analyzer reports:

- selected unquantized call count;
- positive-RM versus zero-RM call counts;
- per-call RM-activity histogram;
- raw RM request-size histogram inside unquantized intervals;
- family call / positive / zero / request / RM / nominal-payload totals;
- `hyper_connection` activity and request-size histograms;
- hyper-connection positive layer indices and gap histogram;
- per-component hyper-connection totals;
- top 32 individual calls;
- nominal-payload/RM Pearson diagnostics;
- uncovered R26-residual request-size histogram;
- top uncovered RM requests plus immediately preceding/following unquantized prefixes.

Semantics remain strict:

- RM bytes are logical allocation activity volume, not resident ownership;
- payload bytes are nominal weight-tensor payload;
- temporal alignment does not establish causal ownership;
- correlation or a repeated chunk size does not by itself identify the CUDA/RM allocator policy that created it.

## Decision

If only a minority of hyper-connection calls carry the majority of RM activity and those calls show a repeated large request size such as ~`800 MiB`, prefer an allocator-growth/reservation discriminator next rather than another model-component boundary marker.

If RM activity instead scales broadly with hyper-connection payload/call type, narrow the model constructor to that exact component before considering a behavior-changing mitigation.

If the uncovered `5802.375 MiB` is dominated by one or two repeated request sizes located between consistent constructor prefixes, use those contexts to define the next boundary.

No R29 live run is authorized by this plan. H11 remains deferred.

PR #244 remains open and unmerged.
