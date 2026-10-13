# D0 offline disposable-host policy preflight — GitHub CI result (2026-10-12)

## Exact source and evidence classification

- Branch: `feat/h38-managed-integration`
- Source commit: `7acd15cc5a2d8f5603bdb82b08b1cee49da7d18a`
- GitHub CI: [#38217170909](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38217170909), **COMPLETED / SUCCESS**
- Full Python unittest discovery: **812/812 PASS** (previous 803 + 9 new D0 test methods).
- Existing seven-module exact-SHA bounded synthetic allowlist: **77/77 PASS**; **the nine new D0 tests are in the full suite, not the current DGX-local allowlist**.
- Bash syntax, ShellCheck, Python compilation, whitespace checks: **PASS**.
- Actual DGX latest prior locally tested source: `1283b1a9252f1ff53d51659049ca42f9449e5ccd`, **77/77 isolated fixture tests**. The new D0 source has **NOT** been run on the DGX.

## New source implementation

`disposable-d0-preflight.py` is a Python stdlib-only, read-only **offline evidence evaluator**, not a host probe and not an E2E runner. It takes `--policy` and `--inventory` JSON paths. It does not execute subprocesses, ask for privileges, access the real Docker daemon, query systemd, run host diagnostics, open model weights, or write out approval artifacts.

It checks schema versions, full exact SHA and repository origin, clean-checkout assertion, protected machine SHA-256 denyset, Docker daemon denyset, explicit owner disposable declaration and restore point, non-default isolated Docker context with no external users, lexically safe/nonoverlapping work/model/log roots excluding declared protected roots and basic system roots, bounded owned synthetic fixture, isolated D0-only service name, and no pending transactions.

JSON evidence remains **operator asserted and unauthenticated**. Passing the offline policy comparison emits:
```text
D0_STATIC_REVIEW=READY_FOR_INDEPENDENT_REVIEW
D0_ADMISSION=NOT_GRANTED
D0_REAL_HOST_VERIFICATION=NOT_PERFORMED
D0_LIVE_E2E=NOT_AUTHORIZED
```

A mismatch or malformed/unsafe JSON fails closed with exit code 2, `D0_STATIC_REVIEW=REFUSED`, a bounded refusal code, and `D0_ADMISSION=NOT_GRANTED`. The good-path exit code 0 means **only that static assertions were internally consistent**, not that any operator has approved D1–D5.

## New synthetic regression coverage

The new nine `test_disposable_d0_preflight.py` methods cover:

1. Matching synthetic evidence still cannot claim live D0 admission.
2. Known protected machine-ID and Docker-daemon identity refusal.
3. Missing protected-host denyset or owner disposable declaration refusal.
4. Dirty checkout, wrong origin and wrong SHA.
5. Overlap with protected roots, traversal, nested work/model roots and system paths.
6. Shared Docker context, external Docker users and production service names.
7. Production fixture, excessive model fixture size and pending transactions.
8. Symlinked, duplicated-key or oversized evidence file refusal.
9. Unknown schema fields and boolean schema-version refusal.

All tests use disposable local text/JSON fixtures; they do not invoke Docker/systemd, contact host services or mutate the DGX.

## Known limitations and independent admission barrier

- Policy and inventory can be inaccurate or forged. **No cryptographic attestation or trusted collector** is implemented.
- JSON path comparisons are lexical only; actual mount tables, symlink targets, parent filesystems and bind mounts are **not inspected**.
- Docker daemon/context data, machine ID, service list, restore point, host owner consent and cleanup boundaries are not checked against real independent-host state.
- CI with fixture evidence is **not** actual independent host D0 acceptance; no D1–D5 command, Docker/systemd mutation, checkpoint download, swap operation, rollback or physical power-interruption E2E was run.
- A future independent test host needs a human-approved trust policy, actual read-only inventory checks, real isolation proof, bounded rollback/snapshot, explicit disposable dataset and separate permission to mutate. Never execute D1–D5 on the sole protected DGX.

```text
D0_OFFLINE_POLICY_SOURCE=IMPLEMENTED
D0_OFFLINE_POLICY_CI=PASS_9_OF_9
D0_INDEPENDENT_HOST_ATTESTATION=NOT_RUN
D0_LIVE_ADMISSION=NOT_GRANTED
D1_D5=NOT_RUN
M1_HOST_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
HOST_STABILITY=INCONCLUSIVE
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN_UNMERGED
MERGE=BLOCKED
```

This source result is tied to CI #38217170909. The documentation commit that introduces this evidence is newer and requires its own CI.
