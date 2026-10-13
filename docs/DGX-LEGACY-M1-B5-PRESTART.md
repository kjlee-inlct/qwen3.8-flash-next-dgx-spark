# B5 — read-only prestart gate for the installed legacy OrcaRouter (2026-10-13)

**Operator may execute now on the single DGX Spark, after current exact-SHA
GitHub CI SUCCESS. This is a read-only identity/safety audit, not the
managed service start.** B4 earlier recorded the correct immutable
release and old Docker predecessor, but those are dated observations;
B5 must recheck them before any live M1 decision.

## Why a separate B5 gate is necessary

The installed immutable source release is
`ff67bab3c94d6992f61b9535836df97f03b9c022`, and the older
Docker container object is the stopped
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
(`qwen38-flash-next`, `vllm-skinny-tp1:v1`).
The **installed** `scripts/runtime/service-runner.sh`
performs preflight, runtime-transition recover/prepare, launches
a *new* candidate and, on healthy commit, executes
`runtime-transition.sh commit`. That code **deletes the
rollback/previous Docker container object**. Its generic rollback
and recovery logic can start a predecessor that was deliberately
stopped; the protected-stop path instead restores it stopped.

Therefore a blind `systemctl restart` is **not** an in-place,
exact-object-preserving test. Any consent to test on a quiet,
single-user DGX must **also** resolve the old-ID ownership/loss
boundary. Neither A5 PASS nor green CI implies that consent.

## B5 tool and exact source-worktree command

The `scripts/diagnostics/check-legacy-orcarouter-b5-readonly.sh`
helper checks the source's 40-hex SHA, clean checkout, exact
installed immutable release, exact 64-hex predecessor ID, stopped
container/unit, unchanged legacy image, `OOMKilled=false`,
rollback name absent, `PHASE=complete`, monitor/protect=1,
active `/swap-ple.img` and point-in-time memory/swap/disk.
It records `systemctl show` including immutable service command,
and compares manifest/ownership/current/source identities
before/after. It does **not** invoke any live operation.

Run using a **new detached source worktree** to avoid modifying
the user's existing original checkout or the previously created
A5 worktree:

```bash
set -Eeuo pipefail
SOURCE="$HOME/Workspace/llm/qwen3.8-flash-next-dgx-spark"
cd "$SOURCE"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
git fetch origin feat/h38-managed-integration

# Replace with the newest exact 40-hex GitHub HEAD whose CI is SUCCESS.
TARGET='__LATEST_VERIFIED_CI_SHA__'
test "$(git rev-parse FETCH_HEAD)" = "$TARGET"
AUDIT="$HOME/Workspace/llm/qwen38-b5-$TARGET"
test ! -e "$AUDIT"
git worktree add --detach "$AUDIT" "$TARGET"
cd "$AUDIT"
test "$(git rev-parse HEAD)" = "$TARGET"
test -z "$(git status --porcelain=v1 --untracked-files=all)"

LOG="$HOME/dgx-orcarouter-b5-$(date +%Y%m%d-%H%M%S).log"
QWEN38_B5_TARGET_SHA="$TARGET" \
QWEN38_B5_RELEASE_SHA=ff67bab3c94d6992f61b9535836df97f03b9c022 \
QWEN38_B5_PREVIOUS_CONTAINER_ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24 \
  bash scripts/diagnostics/check-legacy-orcarouter-b5-readonly.sh \
  2>&1 | tee "$LOG"
printf 'B5_LOG=%s\n' "$LOG"
```

This creates **only a detached Git source worktree and one operator
log file**, not an installed model, runtime image or service.
Any unexpected `INVALID` or `PARTIAL_CHECK_FAILURE` requires
analysis; do not force recovery or reset. Never paste actual
credentials or secret manifest fields.

### B5 outcome and next decision

A positive read-only B5 result is:
```text
B5_READONLY=COLLECTED_READ_ONLY
M1_LIVE=BLOCKED_PENDING_CONTAINER_ID_DECISION_AND_ROLLBACK_PLAN
OLD_DOCKER_ID_SURVIVAL=NOT_GUARANTEED_BY_INSTALLED_SERVICE_RUNNER
H38_LIVE=BLOCKED
```

This is **B5_PRESTART_READONLY_COLLECTED**, not M1 pass or
a start authorization. The actual transition remains STOP until
one of the following is explicitly authorized and source-tested:
(a) owner accepts replacing/deleting the exact stopped predecessor
container object via the reviewed old managed runner,
or (b) a separate isolation strategy that preserves that object
with independent names/ports and a proven safe stop procedure.
One idle human user does not waive the memory/RM or container
identity requirements.

Any subsequent approved live M1 must additionally revalidate
the exact manifest and SWAP_FILE identity, Docker name/port
exclusivity, active operation locks and transition markers,
monitor thresholds and known old release-specific policy,
strict NVIDIA RM/kernel log baseline and timestamp window,
health endpoint and expected `/v1/models`, committed runtime
attestation, and tested stop/recovery. Monitor/protect stays 1.
A protected-stop is **not** a host-stability PASS.
The already recorded B4 memory reserve is point-in-time only,
not guaranteed runtime-peak capacity. H38 remains blocked and
true uninstall/purge needs independently disposable admission.

**At this commit:** no B5 operator output has been provided.
A5 physical dry-run and lychee888 actual L0 JSON have passed
separately; see the [scoped evidence](../scripts/benchmark/evidence/dgx-a5-wizard-and-lychee-l0-result-20261013.md).


## Physical B5 return (2026-10-13)

The operator executed this exact read-only runner on the sole DGX
at `c2a73179...`, reporting **15/15 B5_CHECK PASS** and
`B5_READONLY=COLLECTED_READ_ONLY`. Docker old ID/release,
monitor, unit and state preservation matched, without model start.
[Permanent scoped B5 output](../scripts/benchmark/evidence/dgx-b5-legacy-orcarouter-prestart-readonly-20261013.md).
This **supersedes the pre-run NOT_RUN publication status** earlier
in this file, but not the M1 blocked exact-ID and STOP conditions.
