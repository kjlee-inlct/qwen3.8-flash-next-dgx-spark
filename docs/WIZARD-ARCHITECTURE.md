> **2026-10-14 M1 ACTUAL DGX read-only preflight qualified:**
> Wizard Benchmark 6 plan, 7 status `ABSENT` and 8 preflight
> `M1_PREFLIGHT=PASS_READ_ONLY` executed at SHA `2dfa74d`;
> exact protected Docker, immutable release and M1 image recorded.
> Live model start was explicitly NOT_PERFORMED. Later source hardening
> gives each M1 candidate independent HOME / vLLM / FlashInfer host
> caches; newer commit SHA/CI must be verified before a new launch.
> Detailed evidence in `scripts/benchmark/evidence/dgx-mazinb-m1-physical-readonly-preflight-20261014.md`.

> **2026-10-14 M1 source stage:** Benchmark submenu now delegates
> dedicated `mazinb-m1.py` plan/status/preflight and protected
> explicitly approved new live run. The source uses create-only
> isolated Docker names, exact-ID prearmed detached monitor and
> a shared lifecycle lock throughout supervised operation. Model
> start, CUDA/RM load and llama-benchy have NOT been performed on the
> physical DGX with this controller. See `MAZINB-M1-WIZARD.md`.

> **2026-10-14 ACTUAL_DGX mazinb historical review:** Wizard
> successfully displayed both old A/B evidence. A/24 GiB reached
> `PROTECT stopping` after 5/5 samples; B/16 GiB served health/models
> HTTP 200 followed by the 180s observation and orderly exit. These
> are October 2 historical experiments, not a fresh Wizard live run.
> Both old containers remain intact. M1 needs a new unique name,
> durable pre-start exact-ID watchdog and full model lifecycle ownership.
> See `scripts/benchmark/evidence/dgx-mazinb-kv-ab-wizard-readonly-20261014.md`.

# Modular DGX Spark Wizard: architecture and migration ledger

## Actual DGX background probe outcome (2026-10-14)

- Operator ran P1a plan and probe on source `9df9d08` in the
  original canonical checkout. Admission returned **BLOCKED**:
  `USER_LINGER_NOT_ENABLED_OR_UNKNOWN`; no Docker or service mutation.
- The revision of P1a used on DGX did not distinguish a confirmed
  `no` answer from an unrecognized/failed linger query. New source
  separates `USER_LINGER_DISABLED`, `USER_LINGER_QUERY_FAILED` and
  `USER_LINGER_RESPONSE_UNRECOGNIZED` with explicit status output.
- **Never automatically enable lingering**. Linger changes are
  persistent user-host policy and need separate owner authorization.
- Non-lingering user units may be terminated after the last logout;
  a passing user-manager query while signed in is not enough.
## Background supervisor capability probe — P1a (source only)

- Wizard Benchmark **11** prints a plan and **12** inspects (read-only)
  user-level systemd capability, current user manager and linger policy.
- No background worker, systemd unit, Docker start or linger policy mutation
  is implemented. Existing Foreground Wizard menu 9 remains unchanged.
- The P1a probe is **not** functional/background/host-stability qualification.
  Proceed to worker implementation only with exact-ID, independent stop
  authorization, benchmark-lock and lost-supervisor safety evidence.
## 2026-10-14 observed cleanup result and preserved output

- DGX operator confirmed the three remaining detached temporary worktrees
  were safely removed; only the canonical
  `~/Workspace/llm/qwen3.8-flash-next-dgx-spark` checkout remains.
- The canonical checkout was synced to `2f1cc08`,
  `feature/wizard-modular-phase1-20261014`.
- Independent 36-KiB `~/Workspace/llm/qwen38-m1-bench-results` is **not** a
  worktree and **must remain preserved**. Its three benchmark payloads
  passed `sha256sum -c` against the archived GitHub digests.
- Source-only next stage is a durable Background/Foreground Supervisor,
  **not yet implemented or physically qualified**. Do not replace
  foreground live safety gates with shell-level detachment.
- [Physical evidence ledger](../scripts/benchmark/evidence/dgx-mazinb-m1-journal-reconcile-physical-20261014.md).
## Single canonical working directory; bounded Git worktrees (2026-10-14)

- Routine operator commands, code edits and Wizard invocation should occur
  in **`~/Workspace/llm/qwen3.8-flash-next-dgx-spark`**, the user's original root.
- Temporary Git worktrees are additional checkouts of the **same** repository;
  they should not be accumulated for serial tests/status checks.
- Use a temporary worktree only if a specific concurrent incompatible branch
  or isolated source experiment justifies it. Record its purpose and removal gate.
- Before any cleanup, inspect `git -C <canonical-root> worktree list --porcelain`
  and `git -C <candidate-path> status --porcelain`. Verify each candidate is
  registered and clean, contains no needed untracked evidence, and is not
  the operator's current shell directory.
- To remove *only* a known clean disposable worktree, first `cd` to the
  canonical root, then run `git -C <canonical-root> worktree remove <exact-path>`.
  Do **not** use `--force`, `rm -rf`, `git clean`, `reset --hard`, or a
  blanket worktree prune. Git refuses dirty worktrees by default.
- Before reusing the canonical root for PR #261, inspect its status and
  current branch. `git switch` can be blocked if that branch belongs to
  another registered worktree; never force a change or discard local edits.
- `~/.local/state/qwen38-spark`, Docker/Checkpoint/PLE swap, releases,
  logs, and benchmark evidence are **not** worktrees and remain protected.
- The operator's physically successful 2026-10-14 reconciliation is
  [permanent evidence](../scripts/benchmark/evidence/dgx-mazinb-m1-journal-reconcile-physical-20261014.md).

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
| Benchmark | old A/B status/evidence, M1 plan/status/read-only preflight, opt-in new isolated M1 live controller, report tools | Live new M1 candidate only after exact-ID typed approval; not qualified on physical DGX |
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
