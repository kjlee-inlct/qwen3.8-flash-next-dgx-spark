# D0 Git/Systemd environment and Docker socket trust boundary — source-only CI (2026-10-13)

## Immutable evidence classification

- Repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`; integration branch: `feat/h38-managed-integration`
- Source commit: `f4e83d2ae3f17d82c5f7702497138c3431072358`
- [Exact-source GitHub Actions CI #38315552300](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38315552300): **COMPLETED SUCCESS**
- **834/834** full Python unit methods passed, up from 829. New **5/5** D0 trust-boundary methods passed. The D0 on-host read-only module has **22** fixture test methods in the full CI suite.
- **77/77** existing allowlisted synthetic test methods passed, including 17 profile-switch methods. The D0 fixture module is **not included** in the 77-method DGX-oriented verifier.
- Bash syntax, ShellCheck, Python compile, whitespace: **PASS** in GitHub Actions.
- **Last actually observed protected DGX local synthetic:** source `1283b1a9252f1ff53d51659049ca42f9449e5ccd`, **77/77 PASS**; local ShellCheck was SKIPPED_NOT_INSTALLED.
- **New source not run** on the protected DGX or any independent disposable host; GitHub CI used mocked host command readers only.

## Issue 1 — redirected host observation via inherited environment

Even read-only `git rev-parse`, `git remote`, and `git status` can observe a different repository when inherited Git environment such as `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE` or `GIT_CONFIG_GLOBAL` redirects the command. Systemd/DBus environment selectors can redirect a service-status query. Before any host commands, the collector now refuses populated `GIT_*` (except specifically `GIT_OPTIONAL_LOCKS=0`), populated `SYSTEMD_*`, and populated `DBUS_SYSTEM_BUS_ADDRESS` / `DBUS_SESSION_BUS_ADDRESS`. Subprocesses use the reviewed environment snapshot plus enforced `GIT_OPTIONAL_LOCKS=0`.

Tests inject each selector and assert fail-closed **before any Git, Docker or Systemd subprocess call**. A legitimate `GIT_OPTIONAL_LOCKS=0` remains accepted.

## Issue 2 — unnecessary unbound Docker commands and environment overrides

The generic subprocess command allowlist previously still permitted `docker info` and `docker ps` **without** an explicit `--context`, even though production checking had already been changed to pin a verified context. Those unbound forms are now refused, with a regression confirming no subprocess call occurs.

The Docker environment check now refuses **all nonempty `DOCKER_*` keys**, not only the original list of six. A regression using `DOCKER_CLI_PLUGIN_EXTRA_DIRS` verifies it cannot silently alter Docker CLI execution. The pinned context endpoint, nondefault dedicated Unix-socket constraints and daemon/container checks remain in place.

## Issue 3 — socket path protected-root and mount provenance

The prior context endpoint guard checked for local Unix socket type, symlink aliases and the usual shared/default Docker socket names, but a socket whose path fell **inside a configured protected root** could still pass until daemon comparison. The collector now refuses it before context-bound Docker commands.

The collector also rejects a socket path that sits **on or underneath any non-root mountpoint**, e.g. a bind mount supplying `/srv/d0-docker`, to avoid accepting a superficially private pathname backed by an external filesystem. The fixture tests validate those refusals.

## Meaning of success and remaining limitations

These controls narrow accidental re-targeting and unsafe admission but do not provide cryptographic host identity attestation, independent Docker daemon ownership proof, immutable binary provenance, host owner consent, snapshot restore proof or complete mount namespace/source verification. The collector has no authorization workflow to perform D1–D5 and still emits:

```text
scope=ON_HOST_READ_ONLY_ASSERTION_CROSSCHECK
independence=NOT_ATTESTED
d0_admission=NOT_GRANTED
d1_d5=NOT_AUTHORIZED
live_host_e2e=NOT_QUALIFIED
```

Policy and inventory inputs remain operator assertions; a malicious host may fake command outputs or hide other users. Subprocess environment review is **not** an operating-system no-write sandbox.

```text
GITHUB_SOURCE_HEAD=f4e83d2ae3f17d82c5f7702497138c3431072358
GITHUB_CI_38315552300=SUCCESS_834_FULL_77_SELECTED
D0_HOST_CROSSCHECK_FIXTURES=PASS_22_OF_22
ACTUAL_DGX_LAST_SYNTHETIC=PASS_77_AT_1283B1A
ACTUAL_INDEPENDENT_DISPOSABLE_HOST_CROSSCHECK=NOT_RUN
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
READY_FOR_REVIEW=BLOCKED
MERGE=BLOCKED
```

The documentation commit adding this evidence has a different HEAD and must be tested separately. Do not retroactively claim new-source DGX acceptance or live host qualification.
