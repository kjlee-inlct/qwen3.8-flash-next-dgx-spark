# DGX A5 — immediate wizard-only physical-host validation (2026-10-13)

**Run this now on the user's one DGX Spark after the exact source commit's
GitHub CI passes.** Operator availability is not a blocker: one Spark,
one human owner, any testing time. This is **not** a plan for H38 startup,
new image downloads, destructive uninstall or a container restart.

## What this tests on actual DGX

`scripts/diagnostics/check-wizard-dgx-readonly.sh` checks a clean
exact-SHA checkout, queries current inventory and selected profile,
then previews (with `--dry-run --no-start --yes`) all four **currently
installable** model targets: `orcarouter`, `nvidia`, `mazinb`,
`orcarouter-hybrid`. It previews both default and `--purge-all`
**uninstall plans** with `--dry-run` still set. It runs a few wizard
fixture unit tests with disposable HOME/XDG roots and checks the
operator's real manifest/ownership file SHA256 and immutable current
symlink before/after. It must refuse an unexpected SHA, dirty checkout,
unexpected symlinks, a changed state hash, or a changed checkout.

A5 `PREVIEW_AND_FIXTURES_PASS` proves the **preview and synthetic
tests actually ran on the DGX CPU**; it does not prove actual model
switching, live vLLM readiness, strict NVIDIA RM memory stability,
uninstaller deletion or a new real model installation. An offline
stopped service need not pass an unrelated live health check.

## Operator command — separate detached source worktree

On the DGX terminal, use the existing repository as a Git object source
without switching its worktree or changing the installed immutable release.
The commands **create a separate source worktree only**, which is not
a Docker resource, model storage root or service. Do not delete or
overwrite an existing worktree; stop on any failed assertion.

```bash
set -Eeuo pipefail
SOURCE="$HOME/Workspace/llm/qwen3.8-flash-next-dgx-spark"
cd "$SOURCE"
git status --short
test -z "$(git status --porcelain=v1 --untracked-files=all)"
git fetch origin feat/h38-managed-integration

# Replace the value with the exact most recent 40-hex commit with SUCCESS CI.
TARGET='__PINNED_CI_SUCCESS_SHA__'
test "$(git rev-parse FETCH_HEAD)" = "$TARGET"

AUDIT="$HOME/Workspace/llm/qwen38-wizard-a5-audit"
test ! -e "$AUDIT"
git worktree add --detach "$AUDIT" "$TARGET"
cd "$AUDIT"
test "$(git rev-parse HEAD)" = "$TARGET"
test -z "$(git status --porcelain=v1 --untracked-files=all)"

LOG="$HOME/dgx-wizard-a5-$(date +%Y%m%d-%H%M%S).log"
QWEN38_WIZARD_AUDIT_TARGET_SHA="$TARGET" \
  bash scripts/diagnostics/check-wizard-dgx-readonly.sh 2>&1 | tee "$LOG"
printf 'A5_LOG=%s\n' "$LOG"
```

**Important:** `__PINNED_CI_SUCCESS_SHA__` is a required placeholder;
replace it with the committed 40-hex GitHub branch HEAD whose CI has
already completed SUCCESS. Never substitute the old checkout SHA,
a GitHub PR number, or a short commit. The command intentionally does
not `git reset`, `git clean`, `sudo`, change the active worktree,
install packages, restart services, pull Docker images, or run purge.

A5 uses the true operator HOME and existing manifest. Synthetic tests
create and remove their own temporary fixture directories only. Save
and share redacted command output including `CHECKOUT_SHA`,
the names/return codes of each `WIZARD_CHECK`, all three final state
fingerprints, and the final `WIZARD_DGX_READONLY` sentinel.
Do not share tokens or an unredacted full install manifest.

## Actual DGX acceptance and next test

| Boundary | Proof required | Classification |
|---|---|---|
| A5 | Exact SHA + SUCCESS CI + `PREVIEW_AND_FIXTURES_PASS`; matching pre/post manifest, asset registry and current link | `ACTUAL_DGX_DRY_RUN_PASS`, not live E2E |
| Legacy baseline M1 | Separate exact **installed immutable** release review; owner decision about legacy Docker ID loss; no stale transitions; monitor/protect ON; safe recover/stop; bounded strict NVIDIA RM trace | **Not automatically permitted by A5** |
| M3 real model switches | Per-profile host readiness and safe service replacement/recovery; separate functional+strict RM verdict | Not qualified |
| lychee888 L0 | Actual pinned HF revision plus config/index JSON result; no weights downloaded | Metadata-only, independent of A5 |
| M2/D1–D5 | Independently disposable host and exclusive owned resources | Not granted |

The earlier actual DGX immutable release `ff67bab3...` has a service
runner that may delete the old stopped Docker container object after
successful managed replacement, or restart it on some rollback paths.
The user is the only human user, but that does **not** make the exact
container ID replaceable by default. Before an M1 live trial, explicitly
choose (a) permitted loss of that **container object ID** and a reviewed
managed lifecycle procedure, or (b) a proven isolated non-overwriting
test strategy. The previous B4 preflight is a point-in-time snapshot
and must be repeated near an actual launch. Do not use raw
`docker start`, blind `systemctl restart`, or relax protection.
H38/M4 remains blocked.

**As of document creation:** this script was committed and was not
run on the user's actual DGX. Actual DGX A5 evidence is `NOT_RUN`
until operator terminal output confirms it. GitHub-only CI must never
be relabeled as actual-host A5.
