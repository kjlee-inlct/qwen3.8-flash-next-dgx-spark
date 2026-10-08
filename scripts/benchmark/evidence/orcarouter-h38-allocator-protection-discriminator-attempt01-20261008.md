# H38 production-shape allocator/protection discriminator — live attempt 01 — 2026-10-08

Status: **VALID PROTECTED_STOP / FUNCTIONAL NOT_REACHED / HOST-STABILITY INCONCLUSIVE**

## Scope and provenance

First real DGX Spark execution of the observability-only, protected H38
production-shape startup following static qualification. It uses
`scripts/benchmark/run-h38-allocator-protection-discriminator.sh`, with
read-only `collect-linux-allocator-state.py` and the pre-event-only
`analyze-h38-allocator-protection-trajectory.py`. This was *not* the
managed migration gate and did not authorize a release/profile change.

The operator supplied the terminal transcript including the final
`upload-summary.txt` and `allocator-analysis.txt`, with no underlying raw
`fast-state.txt`/`slow-state.txt` or all-row `allocator-trajectory.csv`
uploaded for independent full-history recomputation.

- Branch: `feat/h38-managed-integration`
- Exact executed checkout: `2e7aff15b03ffa49cb9aafd8cf688c140891c1e7`
- Observability implementation CI: `37713396361` PASS, 595/595 tests
- Document synchronization CI: `37713578855` PASS, 595/595 tests
- Host: one NVIDIA DGX Spark GB10; exact candidate identity attested by runner
- Timestamp for protected stop: `2026-10-08 11:06:47 KST` / `02:06:47Z`
- Host evidence path: `/tmp/orcarouter-h38-allocator-protection-20261008T015824Z`
- Current release: `ff67bab3c94d6992f61b9535836df97f03b9c022`
- Stopped predecessor ID: `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
- Candidate image: `vllm-orcarouter-v029-h38-decoder-scope:v1`
- Exact workload: `SPEC=mtp`, `k=2`, 16 GiB pinned KV (`17179869184` bytes);
  candidate stdout confirms `executor=mp`, `PLE=mmap`,
  `qsa_det_topk=0`, `qsa_exact_topk=1`, `maxlen=262144`, `util=0.80`
- Managed predecessor remains in its stopped post-protection state.

## Runner and formal result

```text
target_sha=2e7aff15b03ffa49cb9aafd8cf688c140891c1e7
spec=mtp_k2
kv_bytes=17179869184
start_rc=0
wait_ready_rc=1
api_ready=0
oom_killed=false
functional=NOT_REACHED
host_stability=INCONCLUSIVE
kernel_window_rc=0
rm_oom_count=0
protected_stop=1
identity_validated=1
run_completed=1
collector_rc=0
collector_healthy=1
analysis_rc=0
result=PROTECTED_STOP
fail_reason=none
script_rc=1
runner_rc=1
```

The overall runner exit 1 expresses an intentional protected-stop result,
**not harness invalidity**. Exact identity, valid strict kernel measurement
window and completed allocator read-only collection support a formally valid
`PROTECTED_STOP` classification. A zero strict RM count under early
protection is **not** HOST-STABILITY PASS, and protected-stop intervention
must not be reclassified as strict RM failure.

`kernel-errors.txt` was empty in the supplied upload summary.
`collector.log` was also empty; the runner health and analyzer completion
fields, not an assumed independent re-run, support the collector status.

## Startup phase and protection sequence

External monitor started at `10:58:26 KST`. Candidate startup reported
18 safetensors shards; the supplied phase log reached **15/18** at
`11:06:47 KST` before the monitor stopped the candidate. API READY was
not reached. The checkpoint was reported as 170.88 GiB and the worker's
initial Available RAM as 40.78 GiB; auto-prefetch was disabled on EXT4.
The shard-progress line is a coarse startup-phase indicator, not exact
allocation ownership or proof that shard 15 caused the protection event.

The original external monitor policy was unchanged:
- MemAvailable warning 6 GiB;
- non-CMA free 2 GiB, applicable free gate 10 GiB;
- SwapFree gate 8 GiB and observed swap-growth gate 256 MiB;
- five consecutive samples at two-second interval;
- `--protect` active.

```text
KST         non-CMA-free MiB   Swap-growth MiB   protect
11:06:37              1817              195       0/5
11:06:39              1467              266       1/5
11:06:41              1385              343       2/5
11:06:43              1342              487       3/5
11:06:45              1304              559       4/5
11:06:47              1365              717       5/5 -> PROTECT
```

At the final monitor sample: `available=39271 MiB`,
`noncma_available=39204 MiB`, `free=1433 MiB`,
`noncmafree=1365 MiB`, `swapfree=145761 MiB`.
Thus the protected-stop sequence is tied directly to **low non-CMA
immediately free memory plus swap growth**, not to aggregate
MemAvailable or exhausted SwapFree. The memory quantities alone cannot
establish that the monitor would be safe to relax.

## H38 pre-protection allocator trajectory

These are the analyzer's **last samples at or before each requested
relative time**. Their actual UTC offsets are recorded, and the fast
and slow streams are not perfectly synchronized. Values are MiB.

| Target | Fast actual offset | Normal order-4 | Normal order-4+ | MemAvailable | MemFree | SwapFree | PSI some/full avg10 |
|---|---:|---:|---:|---:|---:|---:|---|
| T-60 | -60.803 s | 19.125 | 214.000 | 38952.398 | 1425.766 | 146465.797 | 0.000 / 0.000 |
| T-30 | -30.804 s | 12.375 | 171.375 | 38784.812 | 1161.723 | 146461.156 | 0.000 / 0.000 |
| T-10 | -10.804 s | 274.000 | 698.000 | 39985.676 | 1875.492 | 146354.840 | 0.000 / 0.000 |
| T-5 | -5.804 s | 13.625 | 251.500 | 39839.305 | 1437.387 | 146135.746 | 0.000 / 0.000 |
| T-1 | -1.803 s | 12.188 | 181.812 | 39432.527 | 1367.590 | 145919.016 | 0.140 / 0.140 |
| T0 | -0.804 s | 25.938 | 139.938 | 39374.039 | 1371.000 | 145836.551 | 0.140 / 0.140 |

| Target | Slow actual offset | Normal Unmovable order-4+ | Normal Movable order-4+ |
|---|---:|---:|---:|
| T-60 | -61.803 s | 24.250 | 230.625 |
| T-30 | -31.803 s | 60.188 | 128.188 |
| T-10 | -11.803 s | 23.062 | 1028.875 |
| T-5 | -6.803 s | 21.125 | 269.250 |
| T-1 | -1.802 s | 24.000 | 157.062 |
| T0 | -1.802 s | 24.000 | 157.062 |

At the final *pre-protection* fast sample, Normal order-4+ was
139.938 MiB and order-4 alone was 25.938 MiB. The last pre-protection
slow sample had only 24.000 MiB of Unmovable order-4+. Aggregate free
order-4+ was therefore already severely depleted by this late loading
window, while higher MemAvailable (roughly 39 GiB) did not prevent
the protection sequence.

Observations are dynamic, including an increase in Normal order-4+
from 171.375 MiB at T-30 to 698.000 MiB at T-10 before falling again.
Do not impose a monotonic depletion assumption or infer a causal
allocator owner from these totals. **Do not sum fast and slow order-4+
rows** as if they were simultaneous snapshots. The full trajectory is
needed to locate the onset relative to checkpoint loading.

## R21 / R22 comparison boundary

Previously established valid strict-RM reference **event snapshots**:

| Evidence | Event type and timing | Normal order-4+ | Unmovable order-4+ |
|---|---|---:|---:|
| R21 | strict RM, post-failure | 146.125 MiB | 0.562 MiB |
| R22 | strict RM, post-failure | 3112.125 MiB | 1530.688 MiB |
| H38 attempt 01 | protected-stop, **pre-stop** | 139.938 MiB (-0.804 s) | 24.000 MiB (-1.802 s) |

These are *not* matched pre-failure windows and do not justify a
capacity threshold. R11 established that the RM order-4 allocation
may roll back previously allocated pages after failure, inflating the
post-failure snapshot. R21/R22 also used explicit post-stop memory
conditioning absent from this protected H38 path. Therefore both
event semantics and preparation differ. H38’s reported reservoir scale
is suggestive of high-order scarcity at the protected stop; this is
not proof a strict RM OOM would have happened without intervention,
nor proof the intervention is unnecessary.

## Evidence presentation consistency issue

The terminal printed `script_rc=0` in the first success-path summary
and then `script_rc=1` in the final upload summary, while the shell's
actual `runner_rc=1`. Inspection of the exact executed runner shows
a success-path `write_summary 0` followed by deliberate `exit 1`
for `PROTECTED_STOP`; the `EXIT` trap then rewrites the evidence
summary with the true nonzero exit code.

This is a double-finalization **output/exit-code consistency bug**,
not evidence of a second run, a changed RM count or altered host
protection. A subsequent runner-only correction persists the result
exit code once and bypasses summary re-finalization while preserving
cleanup of sudo keepalive. Do not retroactively rewrite the actual
operator transcript or call the first intermediate `script_rc=0`
a clean run.

## Conclusion and next action

- **VALID** production-shaped `SPEC=mtp k=2` H38 protected-stop
  observation with complete read-only allocator instrumentation.
- Candidate did not reach API READY; migration FUNCTIONAL qualification
  remains blocked; HOST-STABILITY remains **INCONCLUSIVE**.
- Protection intervened on recurring low immediately free pages and
  swap growth; high-order reserves were depleted well before READY,
  while strict RM events were not observed.
- Do **not** weaken protection, tune system VM settings, restart the
  predecessor automatically, repeat unchanged MTP startup, or merge PR #259.
- **Next step: read-only analysis of the preserved**
  `/tmp/orcarouter-h38-allocator-protection-20261008T015824Z/allocator-trajectory.csv`
  to characterize early order-4+ collapse and align its timing with
  shard-phase markers; optionally ingest historical R21/R22 raw
  trajectories only if exact source paths are independently verified.
  Record an offline finding rather than launching another costly run.
