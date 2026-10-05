# OrcaRouter Hybrid R24 — H6 16 GiB RM mitigation result — 2026-10-05

## Status

**VALID_RM_OOM — FUNCTIONAL PASS / HOST-STABILITY FAIL — H6 NO RM MITIGATION**

R24 tested the generated H6 ModelOpt W4A16 Hybrid checkpoint against the canonical R22 v0.29 PLE-mmap control while forcing the same `16 GiB` KV allocation (`17179869184` bytes). The run is valid and the H6 candidate reached API readiness, but the common early RM burst was not reduced and one strict NVIDIA RM `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` event occurred.

Per project policy, any confirmed strict RM OOM in a valid measured run is HOST-STABILITY FAIL even if the runtime reaches READY.

The live discriminator is therefore:

`H6_NO_RM_MITIGATION_HOST_FAIL`

This closes H6 ModelOpt W4A16 representation as a mitigation candidate for the already-identified RM mechanism under the matched R22 runtime controls.

## Run validity

Observed live summary:

- `run_valid=1`
- `candidate_start_rc=0`
- `collector_rc=0`
- `trace_rc=0`
- `trace_report_rc=0`
- `analyzer_rc=0`
- `wait_ready_rc=0`
- `api_ready=1`
- `protected_stop=0`
- `trace_window_valid=1`
- `candidate_identity_valid=1`
- `functional_class=PASS`
- `host_stability_class=FAIL`
- predecessor age: `5761.229 s` (minimum `2700 s`)
- `rm_oom_count=1`
- `event_snapshot_count=1`
- final result: `ORCA_R24_RESULT=VALID_RM_OOM`

The H6 candidate therefore completed the intended matched-control startup path and was functionally healthy enough to reach READY. Its host-stability gate nevertheless fails because the strict RM OOM occurred.

## Matched candidate identity

R24 preserved the predeclared matched-control constraints:

- profile: `orcarouter-hybrid`;
- H6 candidate checkpoint: `qwen3.8-h6-modelopt-w4a16`;
- image: `vllm-orcarouter-v029:v1`;
- image stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`;
- KV cache: `17179869184` bytes (`16 GiB`);
- exact candidate identity validation: PASS;
- PLE mmap / exact QSA path preserved by the runner contract;
- no persistent VM tuning;
- aged predecessor requirement satisfied.

The purpose was to change the H6 checkpoint/loader representation without simultaneously changing the R22 KV allocation or broad host conditioning.

## Common burst comparison against R22

Canonical R22 baseline:

- largest five-second unexplained residual: `75,138.043 MiB`.

R24 H6 candidate:

- largest one-second unexplained residual: `+29,308.809 MiB`;
- largest five-second unexplained residual: `+77,937.680 MiB`;
- candidate / R22 burst ratio: `103.725991%`;
- candidate burst reduction: `-3.725991%`;
- operational burst band: `BURST_UNCHANGED`.

Thus H6 did not suppress the closed approximately 75 GiB startup mechanism. The measured five-second residual was actually about `2,799.637 MiB` larger than R22, a `3.725991%` increase. This run is not evidence that H6 intrinsically worsens the mechanism by exactly that amount; the operational conclusion is only that it remains in the unchanged band and provides no material mitigation.

## Same-window RM activity

The independently detected largest five-second burst was fully covered by the narrow RM trace:

- `trace_covers_burst5=1`;
- trace start monotonic: `382532.326729610`;
- trace end monotonic: `382582.728837660`;
- burst start monotonic: `382548.943040064`;
- burst end monotonic: `382553.943487653`.

Observed RM activity:

- `nv_alloc_pages`: `575` matched calls/events as reported by the analyzer;
- `nv_alloc_system_pages`: `538`;
- 64 KiB/order-4-path `nv_alloc_pages` calls total: `526`;
- 64 KiB/order-4-path activity total: `77,405.938 MiB`;
- 64 KiB/order-4-path calls inside the five-second burst: `526`;
- 64 KiB/order-4-path activity inside the five-second burst: `77,405.938 MiB`;
- 4 KiB/order-0-path activity total: `1.613 MiB`;
- unmatched `nv_alloc_pages` entries/returns: `0/0`;
- unmatched `nv_alloc_system_pages` entries/returns: `0/0`.

All observed 64 KiB RM activity occurred inside the independently selected five-second burst window. The RM activity volume is approximately `99.318%` of the `77,937.680 MiB` residual increase in that same window.

As with R23, cumulative RM requested bytes are **activity volume, not exact resident ownership**. The numerical alignment is used only as a discriminator for the already-closed driver-level mechanism.

## Host allocator movement during the H6 burst

Across the candidate's largest five-second burst:

- node0 Normal free delta: `-78,832.938 MiB`;
- global `nr_free_pages` delta: `-78,833.074 MiB`;
- nearest Normal Unmovable order-4+ before/at burst start: `104,382.688 MiB`;
- nearest Normal Unmovable order-4+ after/at burst end: `46,869.812 MiB`;
- nearest Normal Movable order-4+ before/at burst start: `10,761.938 MiB`;
- nearest Normal Movable order-4+ after/at burst end: `10,118.875 MiB`.

The H6 path therefore consumes essentially the same class of node0 Normal high-order supply identified in R11/R21/R22/R23 rather than avoiding that demand.

## Strict RM failure

The valid H6 run recorded one strict NVIDIA RM failure:

- `2026-10-05T00:30:45.114568+09:00`
- `_memdescAllocInternal(pMemDesc)` returned `NV_ERR_NO_MEMORY` at `mem_desc.c:1359`.

This is sufficient for strict HOST-STABILITY FAIL.

The candidate nevertheless reached API readiness, so functional and host-stability classifications remain separate:

- FUNCTIONAL: PASS;
- HOST-STABILITY: FAIL.

## Mitigation conclusion

R24 answers the intended question directly:

**The H6 ModelOpt W4A16 Hybrid representation does not mitigate the common direct NVIDIA RM system-memory burst under R22-matched 16 GiB runtime controls.**

Specifically:

1. the approximately 75 GiB early burst remains unchanged (`103.725991%` of R22);
2. the same five-second window contains `77,405.938 MiB` of observed 64 KiB RM activity;
3. node0 Normal free pages fall by about `78.8 GiB` during that burst;
4. later strict RM OOM still occurs;
5. functionality and candidate identity remain valid.

Therefore H6 should not be promoted as a host-stability mitigation and there is no basis to change the managed Hybrid default on the strength of this run.

This result also argues against further broad ownership/UVM tracing: R24 independently reproduces the same direct RM mechanism under the H6 path.

## Managed-service restoration closure

At script completion, cleanup restarted the managed service and `systemctl is-active qwen38-flash-next.service` returned `active`, but the immediately following `/health` request disconnected before restored API READY had been proven.

A later explicit restoration check on 2026-10-05 closes that follow-up:

- `qwen38-flash-next.service` remained `active (running)` from `2026-10-05 00:31:27 KST` and had been running for approximately 10 hours at verification time;
- the service log records `health-ready`, `model-list-validated`, `Runtime transition committed`, `runtime-attestation-written`, and `Qwen API is ready` at `2026-10-05 00:45:28 KST` (`elapsed=841s`);
- `scripts/wait-ready.sh --container qwen38-flash-next` returned `READY after 0s`;
- `/health` succeeded;
- `/v1/models` returned the exact restored served identity `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` with `max_model_len=262144`.

Therefore **managed-service restoration is CLOSED / PASS**. The immediate post-run health disconnect was only the normal startup interval after cleanup restarted the managed runtime; it is not an unresolved recovery defect and does not affect the R24 candidate classification.

The later unprivileged `journalctl -k` invocation printed the standard permission warning that the user could not see all system/kernel messages. Its empty filtered output is therefore **not** treated as proof that no later RM messages existed. This does not alter R24 because the measured candidate kernel window already contains the strict RM OOM used for classification.

## Next engineering direction

Do not repeat H6 merely to search for a different outcome, and do not return to broad VM, UVM, scheduler, generic page-allocation, function-graph, or all-driver tracing.

The next discriminator should target a variable capable of changing the *source or shape of the approximately 75 GiB RM demand*, while preserving the strict host-stability gate and matched-control discipline.

In particular, R24 shows that changing the H6 ModelOpt W4A16 loader/config representation alone is insufficient. Any R25 candidate should be justified by an explicit mechanism for reducing/eliminating the RM 64 KiB system-memory allocation episode, not only by a different checkpoint label or quantization metadata.

A high-information R25 direction is to test the model weight/materialization path directly. The current v0.29 serving path uses `--load-format safetensors`, and the observed 64 KiB RM activity (`77,405.938 MiB`) is numerically close to the runtime's documented approximately `77.5 GiB` weights + non-torch + activation + graph footprint. This similarity is a hypothesis generator, not causal proof. R25 should therefore align the smallest practical userspace weight-load/materialization boundary with the already-closed `nv_alloc_pages` / `nv_alloc_system_pages` episode before attempting another checkpoint/config-only mitigation.

PR #244 remains intentionally open. No merge is implied by this result.