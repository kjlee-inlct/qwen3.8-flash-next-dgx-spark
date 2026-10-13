# H38 MTP startup discriminator attempt 01 — 2026-10-08

Status: SETUP INVALID / NO CANDIDATE START / NO CAUSAL CLAIM

## Invocation

- branch: `feat/h38-managed-integration`
- exact checkout: `c1821bbc00a6ffba93efb2a07584b7c3f7ac27dc`
- intended runner: `scripts/benchmark/run-h38-mtp-startup-discriminator.sh`
- intended single runtime delta: production `SPEC=mtp, k=2` -> discriminator
  `SPEC=none`

## Preserved starting state

The operator preflight showed the expected post-protection recovery state:

```text
managed service: inactive
qwen38-flash-next: running=false oom=false image=vllm-skinny-tp1:v1
UPDATE_STATE=idle
TRANSACTION_STATE=idle
PROFILE_SWITCH_STATE=idle
RELEASE_PROFILE_REFRESH_STATE=idle
```

The restored predecessor container ID was
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`.

## Setup failure

The runner stopped before creating the isolated H38 candidate:

```text
H38_MTP_DISCRIMINATOR_ERROR: install root does not match restored current release:
/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark
```

This was a harness invariant defect, not a runtime failure.

The installer writes manifest `INSTALL_ROOT` from its executing repository
`ROOT_DIR`. Immutable runtime identity is separately represented by the verified
`~/.local/share/qwen38-spark/current` release pointer. The failed atomic H38 refresh
correctly restored the exact predecessor manifest, whose `INSTALL_ROOT` is therefore
allowed to remain the operator checkout path.

The attempt did not start `qwen38-h38-mtp-none`, did not mutate the managed
release/profile manifest, and did not change monitor policy.

## Correction

The discriminator baseline now:

1. verifies the current release pointer resolves to the recorded immutable release;
2. runs `release-manager.sh verify` on that immutable release;
3. treats manifest `INSTALL_ROOT` as the restored installer/source repository root,
   requiring it to resolve to a repository-shaped directory but not to equal the
   immutable release directory;
4. records both roots separately in evidence.

This preserves fail-closed immutable-release validation without imposing a false
equivalence between installer provenance and runtime release identity.

## Classification

- candidate start: NOT REACHED
- FUNCTIONAL: NOT REACHED
- HOST-STABILITY: NOT MEASURED
- protection: NOT EXERCISED
- strict RM window: NOT STARTED
- causal MTP claim: NONE

A corrected live attempt is required before interpreting MTP startup behavior.
