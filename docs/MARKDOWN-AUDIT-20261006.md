# Markdown audit closure — 2026-10-06

Status: **CURRENT-FACING DOCUMENTATION AUDITED — HISTORICAL EVIDENCE PRESERVED**

This document records the repository-wide Markdown audit boundary after PR #248 and the
follow-up root-README/lifecycle-documentation synchronization.

## Audit rule

Repository Markdown is split into two semantic classes:

1. **current-facing documentation** — must describe the repository as it works now;
2. **dated experiment/evidence history** — preserves what was measured, believed, pending,
   or planned at the time of that run.

Historical evidence is not rewritten merely because later experiments supersede its
interpretation. When old execution instructions could be mistaken for current instructions,
add an explicit historical/superseded annotation instead.

The canonical current-state entry point is `docs/CURRENT-STATUS.md`. The canonical
host-stability/evidence index is `scripts/benchmark/evidence/README.md`.

## Current-facing files reviewed

The audit explicitly reviewed the active documentation surfaces:

- `README.md`
- `OPERATIONS.md`
- `STATE-FILES.md`
- `bench/README.md`
- `docs/ARCHITECTURE.md`
- `docs/CURRENT-STATUS.md`
- `docs/H38-DETERMINISM.md`
- `scripts/README.md`
- `scripts/WAITERS.md`
- `scripts/diagnostics/README.md`
- `scripts/lib/README.md`
- `scripts/lifecycle/README.md`
- `scripts/model/README.md`
- `scripts/runtime/README.md`
- `scripts/benchmark/evidence/README.md`

The large `scripts/benchmark/README.md` is a cumulative experiment ledger rather than a
current-state runbook. Its dated experiment chronology is intentionally preserved; current
interpretation is supplied by `docs/CURRENT-STATUS.md`, `docs/H38-DETERMINISM.md`, and the
evidence index.

## Corrections closed by this audit

The audit corrected or explicitly scoped the following stale statements and omissions:

- mazinb is experimental/installable and has been exercised through live managed
  activation; it is no longer described as dry-run-only or activation-pending;
- the managed resilience KV value is 16 GiB where documented for OrcaRouter/mazinb;
  24 GiB remains historical control evidence, not the current default;
- `orcarouter-hybrid` historical functional/monitor passes are not promoted to current
  host-stability PASS; the current strict classification is
  **FUNCTIONAL PASS / HOST-STABILITY FAIL**;
- any valid confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` remains
  HOST-STABILITY FAIL even when fallback reaches READY;
- the monitor's swap-growth protection arm is documented as a safety heuristic with a
  known cold-load false-positive, not an RM host-stability classifier;
- PR #244 and its branch-closure records are described as merged rather than pending;
- superseded R28 execution instructions and the R9-era NVIDIA report draft are explicitly
  historical;
- root `README.md` now distinguishes the transactional managed installer path from the
  historical/manual NVIDIA `scripts/serve.sh` path;
- H38 decoder-only qualification remains explicitly separate from managed-service
  promotion;
- `STATE-FILES.md` now includes `runtime-transition.env` in the strict-parser boundary and
  documents its dedicated `runtime-transition` schema;
- `scripts/lifecycle/README.md` and `scripts/README.md` now include the persisted
  `profile-switch-transition.sh` lifecycle surface;
- installable mazinb download examples use the normal registry path without implying that
  `--candidate` is required. The compatibility flag remains documented for tracked
  non-installable download profiles;
- root `README.md` now scopes the `MTP k=2` result to the earlier Inferact checkpoint so it
  cannot be confused with the later official NVIDIA checkpoint whose measured optimum was
  `k=3`;
- root `README.md` no longer carries the stale claim that nothing was profiled or that the
  PLE CPU→GPU round trip remains the leading decode suspect. The same document already
  records a ~117-step GPU profile and a PLE-sync ablation showing only a 0.6% step-rate
  effect, so current interpretation points instead to the measured GEMM/kernel gap.

## Historical preservation boundary

Files under `scripts/benchmark/evidence/` remain immutable in measured meaning. Invalid,
partial, failed, and superseded runs stay visible because they are part of the engineering
record. Dated words such as `next`, `pending`, or `current` are read in that document's
historical context unless the file is explicitly a current index or closure.

`scripts/benchmark/README.md` is likewise retained as experiment chronology. Bulk rewriting
it to make every historical sentence read as present-day prose would destroy the temporal
meaning of the ledger and is not part of this audit.

## Regression guard

`tests/test_documentation_current_state.py` protects the volatile current-state and
structure claims, including:

- current 16 GiB managed KV wording;
- mazinb installability/managed activation status;
- Hybrid strict host-stability classification;
- post-merge PR #244/#248 synchronization;
- monitor heuristic wording;
- explicit historical scoping of superseded evidence;
- root README synchronization with `docs/CURRENT-STATUS.md`;
- strict parsing of `runtime-transition.env`;
- the profile-switch lifecycle helper in the canonical/stable script maps;
- normal mazinb download examples without a required `--candidate` flag;
- historical Inferact-vs-official NVIDIA MTP scope and the profiler/PLE-ablation decode
  interpretation in the root README.

Future changes that alter these facts should update implementation, canonical current-state
documentation, and the regression guard together rather than allowing the documents to drift.
