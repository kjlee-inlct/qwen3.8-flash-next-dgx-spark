# Managed profile-switch pairwise transaction fault matrix — 2026-10-12

## Scope and evidence

**GitHub CI and disposable fixtures ONLY**, not a hardware live-profile
switch, daemon/service operation, H38 load, managed readiness, or destructive
end-to-end acceptance. Supported state-schema profiles considered:

`orcarouter`, `nvidia`, `mazinb`, `orcarouter-hybrid`.

The matrix covers **4 × 3 = 12 distinct ordered pairs**. Each pair is
exercised by the actual Bash profile-switch transaction entry point, under
a disposable HOME/XDG tree. The Docker `inspect` implementation is a
synthetic PATH-local stub supplying deterministic container ID, image, mount,
and served-model-name. It cannot establish real Docker readiness or host
stability, even though real transaction file operations are performed on
temporary fixture manifests.

## Added coverage

| Scenario | Pair coverage | Observable invariant |
|---|---:|---|
| Activated but not runtime-committed; recover with provable original container identity | 12/12 | Exact source manifest bytes restored; transaction, backup and candidate removed |
| Activated with verified target runtime-commit attestation; mark committed then recover | 12/12 | Target profile remains selected, phase becomes complete, transaction artifacts removed |
| Activated, target has a syntactically valid but incorrect container ID in attestation | 12/12 | Runtime commit rejected, activated transition preserved; after original container proof, exact old manifest restored and artifacts removed |
| Same-profile prepare and wrong-source prepare | 4 source profiles × 2 refusals | Refused before transition-file creation and without changing original manifest |

The first three matrix scenarios are **36 isolated pair/path instances**,
implemented as three `unittest` methods with 12 subtests each; no attempt
is made to report these as 36 standalone tests. The fourth is a separate
method exercising eight source-identity refusal cases.

The original tests for crash-before-state-update, service recovery under
operation lock, rollback proof, and attestation-preserving stop remain in the
same test file. New coverage extends **the profile-switch fixture file from
6 to 10 unittest methods**, not real host run counts. The exact-SHA
`verify-synthetic.sh` allowlist was extended to include that test file;
the runner remains disposable HOME/XDG/TMPDIR + PATH deny stubs, **not an OS
sandbox**. There were **no production runtime implementation changes** in
this matrix patch.

## CI results

- [CI #38204320911](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38204320911):
  **SUCCESS**, 795/795 full Python tests, 69/69 bounded synthetic tests,
  ShellCheck, Bash syntax, Python compile and whitespace PASS (initial two
  pairwise scenarios plus same/wrong-source refusal).
- [CI #38204508012](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38204508012):
  **SUCCESS**, **796/796 full tests**, **70/70 selected synthetic tests**,
  ShellCheck, Bash syntax, Python compile and whitespace PASS, now including
  mismatched-target-ID refusal and rollback for every ordered pair.
- Selected synthetic suite distribution: 19 uninstaller, 7 asset ownership,
  8 operation lock, 14 general lifecycle integration, **10 profile-switch
  transaction**, 8 selected-profile snapshot, 4 read-only lifecycle snapshot
  tests; total **70**.

**Critical distinction:** These are mocked-pair and state-file acceptance
tests, not an all-pairs actual running-service qualification. The latest
operator-supplied **actual DGX local** synthetic evidence remains **60/60
PASS at `02e9c61d90c7f15484b0605dc872bbbb21ec253b`**; the
newer GitHub feature branch has not yet been fast-forwarded or executed on
the DGX. Earlier actual Docker stopped-state and selected `orcarouter`
observations are not requalified by this CI.

## Gate disposition and next work

```text
GITHUB_PAIRWISE_SYNTHETIC=PASS_12_ORDERED_PAIRS_3_BRANCHES
GITHUB_FULL_CI=PASS_796_OF_796
GITHUB_SYNTHETIC_ALLOWLIST=PASS_70_OF_70
DGX_LOCAL_NEW_PAIRWISE_SHA=NOT_RUN
M1_HOST_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
HOST_STABILITY=INCONCLUSIVE
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN
MERGE=BLOCKED
```

Remaining meaningful gaps include independent disposable-host actual
service/Docker ownership handover, release pointer and rollback under
permission loss, power/interruption durability, all profile/model variants
and real M3 health evidence. Follow D0–D5 independent disposable-host
acceptance criteria, not destructive testing on the sole DGX Spark.
