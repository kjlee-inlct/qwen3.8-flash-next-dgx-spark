# OrcaRouter R28 — unquantized Linear construction boundary result — 2026-10-05

## Status

**COMPLETED — VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY PASS — BURST UNCHANGED — UNQUANTIZED LINEAR EXPLAINS 86.364798% OF R26 RESIDUAL**

Evidence directory:

`/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005`

Final command result:

- `ORCA_R28_RESULT=VALID_MEASURED`
- `R28_FINAL_COMMAND_RC=0`
- `underlying_harness_rc=0`
- `r28_analyzer_rc=0`
- `managed_restore_ready_rc=0`

## Matched-run classification

The run is valid and functionally successful:

- `run_valid=1`
- `functional_class=PASS`
- `host_stability_class=PASS`
- `rm_oom_count=0`
- `event_snapshot_count=0`
- predecessor age: `4430.463 s`
- forced KV bytes: `17179869184`

No `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` event was observed in this valid run, so the strict per-run host-stability classification is PASS.

This does **not** reclassify H6 as a mitigation. The early burst reproduced essentially unchanged:

- largest five-second residual: `77923.969 MiB`
- R22 ratio: `103.707743%`
- burst band: `BURST_UNCHANGED`
- node0 Normal free delta over burst5: `-78491.680 MiB`
- `nv_alloc_pages` order-4 calls: `526`
- order-4 activity: `77405.938 MiB`

Therefore the R28 clean run demonstrates that the same structural burst can occur without a strict RM OOM. The OOM outcome is not required for burst reproduction and remains margin/host-state sensitive; burst elimination is still unresolved.

## Constructor / R26 residual reproduction

- total order-4 activity: `77405.938 MiB`
- inside selected model constructor: `76846.375 MiB`
- inherited ModelOpt-MoE activity: `34292.000 MiB`
- R26 residual outside ModelOpt-MoE: `42554.375 MiB`

The small `0.125 MiB` difference versus the earlier R26 `42554.250 MiB` value is within the current marker/clock-alignment measurement and does not change the engineering conclusion.

## Unquantized Linear localization

R28 observed:

- marker pairs total: `693`
- selected constructor calls: `678`
- direct-RM activity inside selected unquantized Linear intervals: `36752.000 MiB`
- activity inside the R26 residual: `36752.000 MiB`
- coverage of the R26 residual: `86.364798%`
- nominal unquantized weight payload: `7879.477 MiB`
- diagnostic RM-activity / nominal-payload ratio: `4.664269`
- R26 residual left outside unquantized Linear intervals: `5802.375 MiB`

The ratio above is diagnostic only. RM bytes are logical allocation activity volume; nominal payload bytes are the requested weight-tensor payload. Neither is exact resident ownership, and the ratio must not be described as resident-memory amplification without additional evidence.

The configured primary threshold was `90%`, so the strict discriminator is:

`RM_ORDER4_R26_RESIDUAL_MIXED_OUTSIDE_UNQUANTIZED_LINEAR_CONSTRUCTION`

Engineering interpretation: unquantized Linear construction explains most, but not all, of the R26 non-MoE residual.

## Family split

Observed unquantized Linear families:

| Family | Calls | RM activity MiB | Nominal payload MiB |
| --- | ---: | ---: | ---: |
| `hyper_connection` | 194 | 25600.000 | 1242.500 |
| `self_attn` | 36 | 8928.000 | 1177.500 |
| `linear_attn` | 144 | 820.000 | 3979.688 |
| `other` | 110 | 1374.000 | 847.055 |
| `ple` | 2 | 30.000 | 62.500 |
| `shared_expert` | 96 | 0.000 | 450.000 |
| `router` | 96 | 0.000 | 120.234 |

The dominant observed family is therefore `hyper_connection`, not attention weight payload generally.

Several individual calls align with `800.000 MiB` RM activity despite nominal BF16 payloads of only roughly `6.25–6.56 MiB`, for example hyper-connection input-mix projections. `self_attn.qkv_proj` and one `linear_attn.in_proj_qkvz` call also show `800.000 MiB` aligned activity. This is temporal localization only; it does not prove that the small tensor itself owns or permanently consumes 800 MiB.

## Next action

Do **not** repeat R28 and do not apply H11 yet.

Before any R29 live run, perform a read-only/post-hoc analysis on the preserved R28 evidence to determine:

1. how many of the 194 hyper-connection calls have nonzero RM activity;
2. the histogram of per-call RM activity and underlying RM request sizes;
3. whether `800 MiB` activity occurs as a repeated discrete request pattern;
4. which layer indices and hyper-connection components coincide with those positive-RM calls;
5. whether the positive calls are periodic / allocator-growth-like rather than proportional to nominal tensor payload;
6. the exact composition of the remaining `5802.375 MiB` outside unquantized Linear intervals.

No additional kernel trace is authorized by this result. Use only preserved R28 logs/trace first.

PR #244 remains open and must not be merged without explicit authorization.
