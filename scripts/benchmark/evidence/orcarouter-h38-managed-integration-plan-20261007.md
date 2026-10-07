# OrcaRouter H38 managed-service integration plan — 2026-10-07

Status: IMPLEMENTED ON FEATURE BRANCH / STATIC AND LIVE QUALIFICATION PENDING

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
- existing supported pre-H38 OrcaRouter stock/skinny manifests remain bootable after immutable code update;
- H38 runtime controls activate only after explicit `--refresh-profile-defaults`
  changes the manifest image to the H38 tag;
- H38 uses PLE mmap, exact QSA, canonical Marlin order with decoder scope, isolated
  compile cache, MTP k=2, max model length 262144, max sequences 3, prefix cache off,
  and the retained 16 GiB managed KV setting;
- preflight and doctor verify H38 image provenance once the H38 image is selected;
- runtime/profile/update transaction semantics remain unchanged.

## Static acceptance

Required before live DGX work:

1. shell syntax and ShellCheck pass;
2. Python compilation and the full unit-test suite pass;
3. dry-run remains side-effect free;
4. tests cover H38 registry selection, clean-host image chain, installer image
   preparation, legacy-image migration compatibility, H38 runtime env, doctor/preflight
   provenance, asset inventory, and managed benchmark aliasing;
5. documentation states that managed promotion is not complete until live qualification.

## Live DGX acceptance

Pin the exact PR head and require a clean checkout before mutation. Preserve any local
operator edits, especially `scripts/model-assets.sh`; do not overwrite a dirty host.

The live sequence is deliberately two-stage for an existing installation:

1. Capture current managed service, container/image, manifest, immutable release,
   runtime commit, and a decode-performance baseline.
2. Stage, qualify, and transactionally update the immutable release to the PR head.
   The currently installed supported legacy stock/skinny manifest must still reach READY
   using the legacy OrcaRouter controls. This proves code-update compatibility before
   data migration.
3. Run `./install.sh --model orcarouter --refresh-profile-defaults --lang en --yes`.
   The installer must build/reuse the complete H38 image chain, replace the runtime
   transactionally, and commit the H38 manifest only after READY and served-model
   identity validation.
4. Run `scripts/doctor.sh --strict` and verify the runtime-commit attestation,
   H38 image label, decoder scope, exact QSA, PLE mmap, H38 cache namespace, model
   identity, service state, and container image.
5. Run the canonical H38 determinism matrix against the managed served alias by setting
   `H38_GATE_MODEL=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`. Require:
   1K/128 x20 `unique_hashes=1`; 32K/128 x10 `unique_hashes=1`; forward and
   reverse QSA sweeps all `unique_hashes=1` with `first_failure_tokens=null`.
6. Run the same 384-token, five-repeat decode benchmark as the baseline. Record median
   decode tokens/s. A candidate below 90% of the baseline blocks promotion pending
   explicit performance review; do not silently waive the regression.
7. Restart the managed service through the supported service path, wait for READY,
   rerun doctor strict, and verify the H38 image/env/attestation remain stable.
8. Inspect kernel evidence for the full measured window. Any confirmed
   `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` makes HOST-STABILITY FAIL even
   if READY, inference, determinism, and soak all pass.
9. Confirm Docker did not report OOMKilled and that runtime/update/profile-switch
   transactions are idle.

Record FUNCTIONAL and HOST-STABILITY separately.

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
