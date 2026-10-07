# OrcaRouter H38 managed-service integration plan — 2026-10-07

Status: ATOMIC TRANSACTION STATIC/CI PASS / DGX LIVE QUALIFICATION PENDING

## Provenance

- base main: `a7c563705edba780747bf815278f6b77c8a41b08`
- branch: `feat/h38-managed-integration`
- checkpoint: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`
- pinned checkpoint revision: `c1209bda15a6bbc4c68b585e93d40c0d85f50306`
- candidate image: `vllm-orcarouter-v029-h38-decoder-scope:v1`
- required image label: `qwen38.h38scope=decoder-v1`
- managed KV resilience setting remains 16 GiB.

Historical H38 experiment results are not rewritten by this plan.

## Change boundary

This integration promotes the already-qualified decoder-only H38 runtime implementation
into the existing installer profile named `orcarouter`; it does not create a new
checkpoint profile and it does not change the `orcarouter-hybrid` H6 checkpoint.

The implementation must keep these boundaries:

- clean-host local image construction follows v0.29 -> H9 -> H10 -> H11 -> H12 -> H38;
- existing supported pre-H38 OrcaRouter stock/skinny manifests remain valid as the
  source state for a one-step atomic cross-release migration;
- a new immutable release must not start the persisted legacy CPU-offload runtime as
  an intermediate acceptance state;
- H38 runtime controls activate only when the atomic refresh activates the qualified
  target release and H38 target manifest together;
- H38 uses PLE mmap, exact QSA, canonical Marlin order with decoder scope, isolated
  compile cache, MTP k=2, max model length 262144, max sequences 3, prefix cache off,
  and the retained 16 GiB managed KV setting;
- preflight and doctor verify H38 image provenance once the H38 image is selected;
- the outer release-profile refresh transaction is the sole recovery owner for the
  release pointer + canonical manifest boundary;
- runtime replacement keeps the previous rollback container until the outer
  release-profile transaction commits, so interruption recovery can restore an exact
  release + manifest + runtime tuple;
- failed-candidate service teardown must not stop a newly restored predecessor
  container: service stop is bound to the attested container ID;
- a running restored predecessor is reattached by one-shot exact-identity adoption
  rather than replaced, while a safety-stopped predecessor remains stopped;
- monitor protection and strict NVIDIA RM classification are not weakened.

## Static acceptance — passed on implementation head `398697be4a92b15e312d90101b706821075b7ae8`

Recorded in `orcarouter-h38-managed-integration-static-result-20261007.md`.
The required static gates were:

1. shell syntax and ShellCheck pass;
2. Python compilation and the full unit-test suite pass;
3. dry-run remains side-effect free;
4. tests cover H38 registry selection, clean-host image chain, installer image
   preparation, legacy-image migration compatibility, H38 runtime env, doctor/preflight
   provenance, asset inventory, and managed benchmark aliasing;
5. documentation states that managed promotion is not complete until live qualification.

Atomic cross-release redesign revalidation:

- implementation/docs head: `d44e3ddd53896c7d87b533f5db315a168e65dd59`
- GitHub Actions CI run: `37604211474`
- shell syntax: PASS
- ShellCheck: PASS
- Python compile: PASS
- unit tests: **567/567 PASS**
- whitespace: PASS

Rollback/service-ownership hardening was revalidated on
`40cf5f8a2d13d3b30b6ae0f71cffb4fdfdd3512b`, GitHub Actions run
`37616889537`. The complete atomic-refresh + rollback-monitor + guarded-follow-up
surface was then revalidated on
`acb69b83e28b593e434d2e5e51b7f9b4584b6aad`, GitHub Actions run
`37622310894`: shell syntax, ShellCheck, Python compilation, **581/581 unit tests**,
and whitespace all passed.

This closes the static/CI gate for the implementation surface. It does not advance any
live DGX acceptance classification.

## Live DGX acceptance

Pin the exact PR head and require a clean checkout before mutation. Preserve any local
operator edits; do not reset or overwrite a dirty host.

The old two-stage sequence is retired. Do **not** first update the code release and wait
for a legacy CPU-offload READY state. The matched base-main control proved that
intermediate is not a valid H38 discriminator.

Use the guarded migration gate:

```bash
H38_MANAGED_TARGET_SHA=<exact-final-PR-head> \
  bash scripts/benchmark/run-h38-managed-migration-gate.sh
```

The migration gate must:

1. prove exact checkout SHA, clean worktree, complete legacy OrcaRouter manifest,
   exact immutable current release, healthy non-OOM predecessor container, matching
   runtime attestation, and all lifecycle transactions idle;
2. collect a fresh matched 384-token x5 legacy decode baseline before mutation;
3. stage/qualify the exact target release and execute only
   `scripts/update-release.sh RELEASE_ID --refresh-profile-defaults`;
4. build/reuse and verify the v0.29 -> H9 -> H10 -> H11 -> H12 -> H38 chain without
   starting a new-code + legacy-image intermediate runtime;
5. activate the target release and H38 `service_ready` manifest under one persisted
   transaction, preserve the previous runtime rollback container through target
   readiness/attestation, and commit it only when the outer transaction commits;
   on failure, require identity-safe predecessor restoration without an unconditional
   legacy cold restart;
6. require exact target release, exact target install root, H38 image/label, model ID,
   H38 env, 16 GiB KV flag, running container, `OOMKilled=false`, runtime attestation,
   lifecycle idle state, and `doctor.sh --strict`;
7. capture the measured migration kernel window and classify any
   `_memdescAllocInternal` or `NV_ERR_NO_MEMORY` as **HOST-STABILITY FAIL**;
8. classify a memory-protection stop as a safety intervention / incomplete functional
   gate, not as HOST-STABILITY PASS and not as confirmed RM OOM;
9. preserve one upload-oriented evidence summary plus the full run log.

Only after the atomic migration gate is FUNCTIONAL PASS and its measured migration
window is free of strict RM failures may the remaining managed gates proceed.

Use the guarded follow-up runner and point it at the **same migration evidence
directory** so the performance comparison is bound to the fresh predecessor baseline:

```bash
H38_MANAGED_TARGET_SHA=<exact-final-PR-head> \
H38_MANAGED_MIGRATION_EVIDENCE=<passing-migration-evidence-dir> \
  bash scripts/run-h38-managed-followup-gates.sh
```

The follow-up runner holds the lifecycle operation lock for the full measured window,
reuses the canonical determinism benchmark, performs the supported managed-service
replacement/restart, and records one upload-oriented evidence bundle. It automates the
following acceptance requirements:

1. Run the canonical managed H38 determinism matrix with
   `H38_GATE_MODEL=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`. Require 1K/128
   x20 and 32K/128 x10 `unique_hashes=1`, plus forward/reverse QSA sweeps with
   `unique_hashes=1` and `first_failure_tokens=null`.
2. Run a candidate 384-token x5 decode benchmark and compare its median against the
   fresh baseline recorded by the migration gate. Candidate median must be at least
   90% of that baseline; below 90% blocks promotion.
3. Restart `qwen38-flash-next.service` through the supported managed path. Require
   exact model READY, `doctor.sh --strict`, matching runtime attestation, exact H38
   image/env, `OOMKilled=false`, and all lifecycle transactions idle.
4. Preserve explicit kernel evidence for the follow-up measured windows. Any confirmed
   `_memdescAllocInternal` or `NV_ERR_NO_MEMORY` in any valid acceptance window is
   HOST-STABILITY FAIL regardless of functional/determinism/performance/restart success.

Record FUNCTIONAL, DETERMINISM, PERFORMANCE, RESTART/ATTESTATION, and HOST-STABILITY
independently. Historical dedicated-H38 success does not satisfy these managed gates.

## Promotion rule

Do not merge this runtime-impacting change on CI alone. Promotion requires:

- CI PASS;
- managed FUNCTIONAL PASS;
- H38 determinism PASS on the managed served alias;
- performance gate PASS or an explicit reviewed disposition;
- strict HOST-STABILITY PASS for the measured window;
- managed restart/attestation PASS;
- canonical result/closure documentation.

If a valid measured run contains NVIDIA RM no-memory evidence, preserve the result as
HOST-STABILITY FAIL and do not rewrite it after a later successful retry.
