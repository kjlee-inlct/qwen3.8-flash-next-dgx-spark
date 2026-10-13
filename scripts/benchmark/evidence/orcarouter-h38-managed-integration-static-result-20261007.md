# OrcaRouter H38 managed-service static qualification result — 2026-10-07

Status: STATIC/CI PASS — DGX LIVE QUALIFICATION PENDING

## Provenance

- repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- branch: `feat/h38-managed-integration`
- runtime-impacting implementation head: `398697be4a92b15e312d90101b706821075b7ae8`
- base main: `a7c563705edba780747bf815278f6b77c8a41b08`
- draft PR: `#259`
- GitHub Actions run: `37566546432`
- workflow conclusion: `success`

## Static gate result

The repository CI completed successfully for the implementation head above.

Validated by the workflow:

- shell syntax: PASS;
- ShellCheck at error severity: PASS;
- Python compile: PASS;
- full unit-test suite: PASS — 536 tests;
- whitespace/error check: PASS.

The unit-test run ended with:

```text
Ran 536 tests in 39.387s
OK
```

## Review findings closed before this pass

Static review found and corrected two integration issues before this gate:

1. clean-host H38 construction can create the v0.29/H9/H10/H11/H12 parent images,
   so installer ownership now tracks the entire created image chain rather than only
   the final H38 tag;
2. immutable code cutover must not strand an older supported OrcaRouter install, so
   both the historical stock image and the later skinny image remain bootable with
   legacy controls until an explicit `--refresh-profile-defaults` migration selects
   H38.

The H6 `orcarouter-hybrid` case remains isolated from H38 decoder-only runtime
environment controls.

## Qualification boundary

This result proves repository/static consistency only. It does **not** prove that the
managed H38 candidate is production-qualified on DGX Spark.

PR #259 remains draft and must not be merged until the live acceptance plan passes:

- two-stage immutable-release + profile-default migration;
- managed readiness, served-model identity and runtime attestation;
- doctor strict;
- managed-alias H38 determinism matrix;
- performance regression gate;
- managed restart/re-attestation;
- strict NVIDIA RM host-stability gate;
- Docker OOM/lifecycle-state checks;
- canonical live result/closure documentation.

Any confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` during a valid measured
live run remains HOST-STABILITY FAIL regardless of functional readiness.
