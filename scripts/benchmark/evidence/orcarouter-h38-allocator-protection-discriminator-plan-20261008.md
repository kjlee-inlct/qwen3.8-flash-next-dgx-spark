# H38 production-shape allocator/protection trajectory discriminator — 2026-10-08

Status: **STATIC CI PASS (37711658336, 592/592); LIVE NOT YET EXECUTED — REQUIRES HOST PREFLIGHT**

## Question and provenance

Managed H38 MTP startup discriminator attempt 04 was a valid `SPEC=none` protected stop, with exact identity attested, `rm_oom_count=0`, and `protected_stop=1`. That rejects MTP removal as sufficient to clear the startup protection boundary but does **not** prove the protection is a false positive. Attempt 03's strict RM failures remain harness-invalid diagnostics.

The R9–R32 closure is unchanged. This plan tests whether read-only node0 Normal order-4+ buddy and Unmovable/Movable page-type reservoir trajectories before a protected stop differ from valid strict-RM failure trajectories. Do not reopen broad allocation ownership tracing.

## Isolation contract

- Repository branch: `feat/h38-managed-integration`; PR #259 remains Draft.
- Exact clean checkout SHA required. Verify remote HEAD before live use.
- Lifecycle idle; managed systemd service inactive; exact predecessor stopped with `OOMKilled=false`.
- Preserved current immutable release/manifest; no install, systemd change, release update, or profile switch.
- H38 image `vllm-orcarouter-v029-h38-decoder-scope:v1`, label `qwen38.h38scope=decoder-v1`.
- Exact OrcaRouter alias/checkpoint, PLE mmap, exact QSA, Marlin decoder canonical order; CPU PLE offload forbidden.
- Production shape: **SPEC=mtp, k=2**, 16 GiB pinned KV, max model length 262144, max sequences 3, GPU utilization 0.80, batch tokens 8192, prefix-cache/autotune/async off, chunked prefill on, executor mp.
- Use `scripts/benchmark/collect-linux-allocator-state.py` without changing its implementation: 1 second fast buddyinfo/meminfo/vmstat/PSI; 5 seconds slow pagetypeinfo/zoneinfo; event-triggered full snapshot.
- Preserve the exact current protection monitor: 6 GiB warning available, 2 GiB free, 10 GiB free-gate available, 8 GiB SwapFree, 256 MiB swap-growth, 5 samples, 2s interval, `--protect`.
- The isolated candidate sets its internal monitor disabled **only to prevent a second independent monitor**; the existing external monitor runs in full protect mode and is not bypassed.
- Absolutely no memory protection threshold, sysctl, reclaim, compaction, drop-caches, host tuning, or lifecycle mutation.

## Instrumentation, evidence, and analysis

Runner: `scripts/benchmark/run-h38-allocator-protection-discriminator.sh`

Analyzer: `scripts/benchmark/analyze-h38-allocator-protection-trajectory.py`

Tests: `tests/test_h38_allocator_protection_discriminator.py`

Evidence directory is generated automatically under `/tmp/orcarouter-h38-allocator-protection-<UTC>` or the explicit new `H38_ALLOCATOR_DISCRIMINATOR_OUT`. Capture exact target SHA, starting identities, collector log, fast/slow samples, full event snapshots, candidate inspect/command/env and startup phase, kernel window with return code, monitor trigger, summary and upload-summary.

The analyzer emits `allocator-trajectory.csv` and `allocator-analysis.txt`, preserves absolute UTC timestamps and sample-to-event offsets, and reports T-60/T-30/T-10/T-5/T-1/T0 **at-or-before-target samples only** with explicit coverage markers. Samples after the RM/protection event are never backfilled into a pre-event T0 value: previous R21/R22 strict-RM results established that page rollback can replenish the post-failure reservoir. If no sufficiently recent pre-target sample exists, coverage is `MISSING` instead of interpolation or a post-event substitute. It uses 4 KiB pages and node0 Normal order-4+ calculations as in R21/R22. `--reference /path/to/preserved-strict-RM-evidence` optionally adds a read-only reference trajectory. Do not invent historical evidence paths or compare against an invalid run as a formal reference. The monitor prints host-local time; use the default Asia/Seoul timezone only when that is the host's configured timezone, otherwise pass the correct `--monitor-timezone` during offline reanalysis.

No initial healthy/collapsed threshold is assumed. `RESERVOIR_CLASSIFICATION=UNDETERMINED` is intentional until matched controlled evidence exists.

## Classification contract

- A valid strict `_memdescAllocInternal` or `NV_ERR_NO_MEMORY` measured event: **HOST-STABILITY FAIL**, even after recovery or READY.
- Exact-identity protected stop with valid kernel window and zero strict RM: **FUNCTIONAL NOT_REACHED / HOST-STABILITY INCONCLUSIVE**.
- Valid no-RM READY: candidate functionally reachable; this alone does not qualify managed service or justify promotion.
- Collector error, missing samples, failed identity attestation, invalid kernel window, incomplete runner or unsupported environment: **INVALID**, no causal claim. Partial RM diagnostics may still be preserved as non-gating evidence.
- Docker OOMKilled is a failure; never classify it as clean.
- Repeat only if the next experiment adds new information; do not re-run unchanged startup repeatedly.

## Before live execution

Static gates: shell syntax, ShellCheck, Python compile, unit tests, whitespace, script executable bit and CI PASS. Then separately verify the DGX host's actual clean exact checkout, lifecycle idle, stopped predecessor, available sudo access, current release, H38 image label and kernel journal access. The runner performs the guarded preflight itself. **Do not execute the command just because this plan exists.**

After a successful static gate and a freshly verified SHA, run on DGX Spark:

```bash
cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark
git fetch --prune origin
git switch feat/h38-managed-integration
git pull --ff-only origin feat/h38-managed-integration
git status --short
sudo -v
H38_ALLOCATOR_DISCRIMINATOR_TARGET_SHA="$(git rev-parse HEAD)" bash scripts/benchmark/run-h38-allocator-protection-discriminator.sh
```

Do not substitute a placeholder evidence path. Copy the emitted `upload_summary`, `allocator-analysis.txt`, and (when needed) the CSV and raw allocator-state sample/event files. Record all invalid attempts and valid results in new dated evidence documents and synchronize `docs/CURRENT-STATUS.md`, the evidence index, and PR #259. Managed follow-up determinism/performance/restart remains unauthorized pending migration FUNCTIONAL and HOST-STABILITY PASS.

## Static validation result — 2026-10-08

- implementation commit: `1f8adbd90e0ba04f0beb990f41f0e7c78ed462df`
- GitHub Actions CI `37711658336`: SUCCESS
- shell syntax, ShellCheck, Python compile, 592/592 unit tests and whitespace: PASS
- This does **not** qualify live host stability, managed migration, or promotion.
- Existing monitor policy and canonical old evidence are unchanged.

## Analyzer pre-event alignment hardening — 2026-10-08

- The first implementation's symmetric nearest-sample rule could select T0 data taken **after** a strict RM allocation error, thereby observing allocator pages released by RM rollback.
- New rule: select only samples at or before each target offset; require <=2.5 s age for fast and <=7.5 s age for slow records. Preserve missing coverage rather than inferring a pre-event reservoir.
- Reject missing fast PSI and short/unparseable pagetype order-4 rows instead of misreporting zero capacity.
- The historical post-RM R21/R22 event snapshots are intentionally retained as post-event evidence, not promoted to instantaneous pre-failure values.

## Final pre-event static qualification — 2026-10-08

- hardening commit: `75dfe1cd983e84b78093d1383770c82c968d8a82`
- GitHub Actions run `37713396361`: **SUCCESS**
- shell syntax, ShellCheck, Python compile, **595/595 unit tests**, whitespace: PASS
- T0 pre-event sample rule, PSI and pagetype incomplete-data errors, and runner usage correction are included.
- This is a static gate only. Live H38 allocator evidence is not yet available, strict host stability is not qualified, and the protected predecessor must not be auto-started.
