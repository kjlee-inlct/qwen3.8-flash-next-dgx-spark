# OrcaRouter R25b — live attempt 01 probe-group setup failure — 2026-10-05

## Classification

**SETUP INVALID — NO R25b MEASUREMENT CLAIM**

This attempt did not reach the candidate model start or the initialize-model localization measurement. It failed while materializing the narrow NVIDIA RM kprobes.

## Run context

Repository head used by the DGX Spark run:

`009c8d47595765ca5dcf366500dfdc8de8bd2257`

Pre-run gates passed:

- diagnostic image marker contract: PASS;
- `R25B_IMAGE_PREFLIGHT=PASS`;
- inherited R24 matched-control preflight: PASS;
- `R25B_LIVE_PREFLIGHT=PASS`;
- predecessor age: `40954.418 s` versus required `2700 s`;
- `predecessor_age_ok=1`;
- RM probe target count: `2`;
- KV: `17179869184` bytes;
- live ACK gate opened explicitly;
- preserved R24 evidence was not reused.

Intended R25b evidence path:

`/tmp/orcarouter-hybrid-r25b-init-model-boundary-01-20261005`

Intended R25b experiment container:

`qwen38-hybrid-r25b-init-marker`

## Failure

The live harness stopped with:

`ORCA_R24_ERROR: probe event not materialized: r25b_rm:nv_alloc_pages_entry`

The inherited R24 harness `create_probes()` writes four probe definitions whose event group is hard-coded as `r24_rm/...`. The initial R25b wrapper transformed the shell variable `GROUP="r24_rm"` to `GROUP="r25b_rm"`, but did not transform those four heredoc probe definitions.

Therefore the kernel materialized the new probe events under `r24_rm`, while the harness immediately validated the expected `r25b_rm` event directory and failed.

The failure is before candidate launch in the inherited harness control flow: service teardown/conditioning precedes `create_probes()`, and candidate request/start follows successful probe creation. No `INIT_MODEL_BEGIN` / `INIT_MODEL_END` overlap measurement was obtained from this attempt.

## Possible residual state

Because the mismatched definitions created `r24_rm` events while cleanup used `GROUP=r25b_rm`, stale `r24_rm` kprobe events may remain after the failed setup. The partial `-01` evidence directory may also exist.

Neither should be silently deleted or reused. Before retry:

1. verify the managed OrcaRouter service/API has been restored and is READY;
2. inspect and remove only the exact stale R25b-attempt probe events if present;
3. preserve the partial `-01` evidence directory as this invalid-attempt record;
4. use a new `-02` evidence path for the actual measured retry.

Managed restoration and stale-probe cleanup are not claimed by this document until verified on the DGX host.

## Remediation

The R25b wrapper is changed to transform both:

- `GROUP="r24_rm"` → `GROUP="r25b_rm"`;
- all exactly four hard-coded `r24_rm/` probe definitions → `r25b_rm/`.

The transform now requires exactly four probe-definition replacements, rejects any remaining `r24_rm/` definition, and requires exactly four resulting `r25b_rm/` definitions. A regression test executes the exact embedded transform against the canonical R24 harness and verifies the rendered temporary harness.

The retry is not authorized until the corrected branch is CI green, managed restoration is verified, stale probe state is clean, and a corrected R25b preflight passes using the new `-02` evidence path.
