# Modular DGX Spark Wizard: architecture and migration ledger

**Latest decision: 2026-10-14.** The future operator entry point is `./wizard.sh`.
`install.sh` must ultimately install/resume only, `uninstall.sh` must own
removal, and model/runtime/API-service/benchmark/storage controllers must have
separate boundaries. This is an incremental high-safety migration.

## Phase 1 implemented (source only)

The new `wizard.sh` loads specialized modules under `scripts/wizard/`:
`status.sh`, `menus.sh`, `model-menu.sh`, `runtime-menu.sh`,
`benchmark-menu.sh`, `storage-menu.sh`.

| Menu | Supported phase-1 action | Mutations |
| --- | --- | --- |
| Install | Call existing installer or resume with default-NO handoff | Only within the existing installer and its own final approval |
| Uninstall | Call existing uninstaller with default-NO handoff | Only within existing uninstaller's safety gates |
| Models | List registry/assets, switch dry-run preview | No switch is executed |
| Runtime/API/service | Read-only service status, Doctor, manifest summary | None |
| Benchmark | mazinb preflight, historical A/B status and evidence (1=A, 2=B, 3=both), read-only new B admission (blocked while historical B exists), report tools | No candidate start; no performance measurement |
| Storage | Status, recommendations, prune **plan** | No prune, model deletion, or evidence cleanup |
| Advanced | A/B status and evidence index | No A/B trials started |
| Diagnostics | Existing read-only Doctor | None |

A strict Python state parser reads `install.env` without shell evaluation.
`Installed` is not inferred from Docker image presence, and neither a
manifest nor a service unit is evidence of READY. Runtime is explicitly
`NOT_PROBED` until the requested runtime/doctor check. Unknown menu choices
retry; EOF is terminal cancellation (exit 2); opening install/uninstall
defaults to NO. There is no `--yes` shortcut in `wizard.sh`.

## Not yet implemented — no premature completion claims

**The legacy `install.sh` remains mixed-responsibility.** Its installer-only
plan/completed-manager imports are now explicit at the installer entry; the
shared `wizard-ui.sh` no longer imports these modules for its callers.
Its optional completed-manager callback hooks still need extraction and
full installed-management relocation before the install-only requirement is met.
It retains installed-state management, profile switching, settings UI,
`scripts/lib/install-completed-manager.sh` and a conditional load from
`scripts/lib/wizard-ui.sh`. Phase 1 does **not** satisfy the final
install-only objective. These old paths remain for compatibility because
moving their lifecycle transaction boundaries without equivalent regression
proof could cause managed Docker replacement or rollback defects.

**Next phases:**

1. Record a complete old/new option, settings, action and hook coverage
   matrix. Make `wizard-ui.sh` presentation-only while extracting the
   completed-install UI and management actions into their respective
   controllers. Preserve CLI contracts with explicit deprecation handling.
2. Move profile-switch and settings live execution to dedicated lifecycle
   orchestration, with exact Docker-ID attestation, immutable release
   proof, operation-lock ownership, commit/rollback/interrupted recovery.
   The new Wizard must not call `install.sh` for live switching.
3. Reduce `install.sh` to fresh install/resume, including pinned model/image,
   storage selection, PLE swap, safe default monitor, review and explicit
   approval. All former options must have an owner and regression tests.
4. Add protected isolated benchmark orchestration: read-only preflight,
   exact predecessor ID, watchdog before start, READY and served-model
   identity, llama-benchy workload, host RM window, JSON/Markdown/SHA256,
   off-host backup, and safely identified stop. No metrics without real run.
5. Add dependency-aware storage cleanup only after backup verification,
   H6 full reinstall test and precise user approval. Never allow default
   `prune` to erase A/B evidence.
6. Run and report distinct SOURCE_REVIEW, LOCAL_SYNTHETIC, GITHUB_CI,
   ACTUAL_DGX_READ_ONLY, ACTUAL_DGX_FUNCTIONAL, HOST_STABILITY and
   ACTUAL_DGX_BENCHMARK gates.

## Existing safety boundaries

Do not replace/remove the predecessor managed Docker, rewrite
`~/.local/state/qwen38-spark/install.env`, switch immutable release
pointers, delete swap/checkpoints, reduce memory-protection thresholds,
or delete A/B archives as part of a UI refactor. PR #259 stays Draft and
unmerged. Any work on an actual DGX requires independent host evidence;
GitHub CI only establishes synthetic/source qualification.

## Tests and operator usage

```bash
bash -n wizard.sh
shellcheck --severity=error wizard.sh scripts/wizard/*.sh
python3 -m unittest tests.test_modular_wizard -v
./wizard.sh --status
./wizard.sh
```

The new regression tests use disposable HOME/XDG directories and piped
inputs to exercise menu errors, navigation, install cancellation, malformed
manifest, symlink rejection and EOF without modifying a real installation.

Related canonical references: `docs/PROJECT-MISSION-AND-MODEL-SCOPE.md`,
`docs/CURRENT-STATUS.md`, `docs/ARCHITECTURE.md`,
`docs/BENCHMARK-BEFORE-RECLAIM.md`,
`scripts/benchmark/evidence/README.md`.
