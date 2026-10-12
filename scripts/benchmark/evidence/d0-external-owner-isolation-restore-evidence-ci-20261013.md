# D0 external owner/isolation/restore assertion chain — source-only CI (2026-10-13)

## Exact source and evidence classification

- Repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- Branch: `feat/h38-managed-integration`
- Source SHA: `a52ae7f2985ce0f415134b848b6caeb6aefec348`
- [GitHub Actions #38317915217](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38317915217): **COMPLETED / SUCCESS**.
- Full Python unit tests **860/860 PASS** (prior 845 + **15** external-evidence methods).
- Prior bounded synthetic operator subset **77/77 PASS**, including profile-switch 17/17. The 15 new methods are **not** part of the 77-case operator synthetic allowlist.
- Bash syntax, ShellCheck, Python compile, whitespace **PASS**.
- Latest **actual protected DGX-local** isolated fixture result remains `1283b1a9252f1ff53d51659049ca42f9449e5ccd`, **77/77 PASS**, local ShellCheck SKIPPED_NOT_INSTALLED. New source has **not** been run on DGX or a separate physical disposable host.
- All new tests use mocked/local temporary files and never access Docker/systemd sockets or invoke host lifecycle changes.

## New offline reviewer and binding contract

`disposable-d0-external-evidence-review.py` (D0 lifecycle category) is a Python standard-library offline-only CLI. It validates the existing exact-byte policy/inventory/crosscheck receipt chain via the previous receipt-review module, parses a strict evidence manifest, then reads and hashes **three separate** bounded, non-symlink local external proof artifacts. All seven inputs stay **outside the repository**.

Manifest version 1 requires exact source SHA, policy SHA-256, inventory SHA-256 and receipt SHA-256. There are three distinct **claimed** reviewer roles:

- **owner:** distinct actor ID, protected-host-excluding machine hash and Docker daemon string matching inventory, `disposable=true`, `permitted_scope=D0_READ_ONLY_REVIEW` and owner artifact SHA-256;
- **isolation:** different claimed reviewer ID, same machine and daemon, `no_external_users=true`, `no_shared_volumes=true`, `no_production_credentials=true` and an independently supplied artifact SHA-256;
- **restore:** third distinct claimed reviewer ID, same host, matching inventoried restore point, `test_data_only=true`, `drill_result=PASS_ASSERTED` and a third artifact SHA-256.

The tool enforces exact schemas, distinct string actor IDs and three different artifact digests, matching policy/inventory/source/receipt, and bounded no-follow reads of evidence blobs (1 MiB maximum each). It refuses missing, empty, symlinked, oversized, altered, duplicated, contradictory or wrongly scoped evidence using safe reason codes without echoing proof contents.

The best possible return is:
```text
D0_EXTERNAL_EVIDENCE_REVIEW=STRUCTURALLY_CONSISTENT_UNTRUSTED
D0_EXTERNAL_ROLES=CLAIMED_DISTINCT_NOT_AUTHENTICATED
D0_EXTERNAL_ARTIFACTS=BYTE_HASHES_MATCH
D0_OWNER_AUTHORIZATION=NOT_AUTHENTICATED
D0_DOCKER_EXCLUSIVITY=NOT_INDEPENDENTLY_VERIFIED
D0_RESTORE_EXECUTION=NOT_INDEPENDENTLY_VERIFIED
D0_EVIDENCE_FRESHNESS=NOT_VERIFIED
D0_ADMISSION=NOT_GRANTED
D1_D5=NOT_AUTHORIZED
```

A zero exit code is **not** an admission token and must never trigger D1–D5 automatically.

## New fixture regressions (15/15)

1. Internally consistent assertions remain `UNTRUSTED` and do not authorize D0 or D1–D5.
2. Altered owner evidence file bytes are refused.
3. Altered isolation or restore evidence file bytes are refused.
4. Altered receipt digest in manifest is refused.
5. Policy/inventory manifest digest drift is refused.
6. Same claimed actor in owner and isolation roles is refused.
7. Host or Docker daemon mismatches are refused.
8. Wrong restore point, `NOT_RUN` drill or non-test-data restore claim is refused.
9. Expanded owner authorization or incomplete isolation claim is refused.
10. Unknown, missing or invalid manifest schema fields are refused.
11. Duplicate JSON fields and symlinked manifest are refused.
12. Empty or symlinked owner proof is refused.
13. Reused identical proof bytes across roles are refused.
14. Forged earlier receipt admission status is refused.
15. Reports do not expose sensitive identifiers and explicitly disclaim authorship/freshness.

## Critical limitations and pending actual D0 review

The three actor IDs are **untrusted strings**. Distinct strings do not authenticate different people. Matching hashes only prove the supplied file bytes match the supplied manifest, not that a human really reviewed them or that an independently trusted owner controls the machine. No digital signatures, trusted certificates, timestamp/notary/freshness protocol, provenance-of-machine measurements, independent Docker-user inspection, shared-volume audit or actual restore drill verification have been implemented.

`PASS_ASSERTED` is an asserted field, **not** an observed restore. No physical independent-host D0 action or destructive E2E has occurred. Independent external assurance requires separately verifiable owner approval, witness identity, true daemon/volume exclusivity and controlled snapshot restoration on a disposable system — along with a separate explicit authorization for any mutation.

```text
D0_EXTERNAL_ASSERTION_REVIEW=SOURCE_IMPLEMENTED
D0_EXTERNAL_ASSERTION_FIXTURES=PASS_15_OF_15
GITHUB_CI_38317915217=SUCCESS_860_FULL_77_SYNTHETIC
D0_INDEPENDENT_HOST_REAL_OBSERVATION=NOT_RUN
D0_OWNER_IDENTITY_AUTHENTICATION=NOT_VERIFIED
D0_DOCKER_EXCLUSIVITY=NOT_INDEPENDENTLY_VERIFIED
D0_RESTORE_EXECUTION=NOT_INDEPENDENTLY_VERIFIED
D0_ADMISSION=NOT_GRANTED
D1_D5=NOT_RUN
ACTUAL_DGX_LAST_SYNTHETIC=PASS_77_AT_1283B1A
M1_HOST_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
HOST_STABILITY=INCONCLUSIVE
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN_UNMERGED
READY_FOR_REVIEW=BLOCKED
MERGE=BLOCKED
```

The later documentation commit embedding this evidence is a **different SHA** and requires its own CI; do not attribute this exact-source CI to new docs without checking them.


## Documentation CI regression and correction record (append-only, 2026-10-13)

- Documentation commit `bc47c3dcc34a9c2fe5379f2688ae456e3f65b5c7`: [CI #38318327651](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38318327651) **FAILED 1/860**, at `test_script_layout.ScriptLayoutTests.test_canonical_category_dependencies_follow_allowed_directions`. The benchmark evidence document contained a literal cross-category code path that violated the benchmark no-dependency layout rule. This failure did **not** invalidate the source-only [CI #38317915217](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38317915217), which remains **SUCCESS 860/860 full and 77/77 selected**.
- Minimal documentation correction `7f1938f91fe8fc02b9b06f4a21b6c94462d3d152`: rephrased one cross-category code path to the bare source file name without changing the executable, 15 added fixtures, original evidence claims or safety gates.
- This note documents failure and remediation; it is **not** a statement that the correction's own CI passed. Verify the eventual documentation HEAD CI independently.

No D0 admission, D1–D5, M1–M4, host protection or PR Ready/Merge gate is promoted by fixing a documentation test.
