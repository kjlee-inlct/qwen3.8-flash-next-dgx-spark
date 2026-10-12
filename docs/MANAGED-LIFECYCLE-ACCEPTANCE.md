# Managed installer, uninstaller, and model-switch acceptance

**Status: implementation and simulation substantially complete; full live E2E NOT QUALIFIED.**

This is the current-facing acceptance checklist for the Qwen3.8 Flash Next single-DGX-Spark managed lifecycle. It separates **implemented**, **CI/synthetic**, **historical operator functional**, and **new live end-to-end** proof. An installable model profile is not automatically host-stable. Use `docs/CURRENT-STATUS.md` and `scripts/benchmark/evidence/README.md` as the authority for exact historical gate outcomes; dated source records are not automatically production approval.

## Current qualification matrix

| Area | Implemented | Evidence available | Outstanding acceptance / classification |
|---|---|---|---|
| Fresh install wizard (ko/en, six steps, registry, model roots, runtime/API/service review) | YES | `tests/test_model_profiles.py`, `tests/test_installer_option_parity.py`, `tests/test_installer_plan_parity.py`, `tests/test_wizard_ui.py` synthetic/dry-run | Truly empty-host download→H38 image→service READY→doctor→restart NOT QUALIFIED |
| Existing-install wizard (active model, switch preview, settings/default refresh, resume) | YES | `tests/test_installer_profile_manager.py`, `tests/test_settings_transition.py`, `tests/test_model_profiles.py` synthetic preview/transaction | Full live supported-profile × configuration matrix NOT QUALIFIED |
| Uninstall bilingual preview (normal, selected purge, all purge) | YES | `tests/test_uninstall_wizard_preview.py` runs real `uninstall.sh --dry-run` against disposable manifests; no live resources touched | Actual destructive default uninstall, preserve/reinstall, selected/full purge in disposable realistic host NOT QUALIFIED |
| Asset ownership and dependent model safety | YES | `tests/test_asset_ownership.py`, `tests/test_lifecycle_integration.py` — ownership/fingerprint, unowned-dependent refusal, Hybrid H6→parent order | All combinations with imported older manifests/external containers during actual deletion NOT QUALIFIED |
| Profile-switch transaction/recover/rollback and operation lock | YES | `tests/test_profile_switch_transition.py`, `tests/test_operation_lock.py`, `tests/test_model_profiles.py` — synthetic crash boundaries and fail-closed invariants | Complete actual profile pairwise matrix and power-interruption recovery NOT QUALIFIED |
| Atomic cross-release same-profile image refresh | YES, candidate | `tests/test_release_profile_refresh_transition.py` and documented actual H38 guarded candidate startup/rollback | H38 managed service acceptance **BLOCKED** until model and strict host-stability gates clear |
| Hybrid H6 → OrcaRouter → Hybrid H6 | YES | Historical managed round-trip: **FUNCTIONAL PASS** | Strict **HOST-STABILITY FAIL** when NVIDIA RM failure present; not production-ready |
| mazinb managed activation | YES | Historical managed readiness/functional operation | **HOST-STABILITY FAIL**, repeated full lifecycle and correctness/performance missing |
| NVIDIA managed profile | YES (experimental) | Registry/dry-run and comparison path | Complete managed live switch/strict host-stability matrix NOT QUALIFIED |
| OrcaRouter H38 managed profile | YES (candidate) | Static CI, exact-image source-only and checkpoint index-only gates, guarded migration rollback | `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`; **GPU/MODEL RERUN BLOCKED** |
| `lychee888` | NO | Visible registry status = planned/non-installable | Not selectable; no production promise |

### Non-negotiable separation of result classes

1. **`CI_PASS`** means the code and disposable-fixture tests passed. It does not imply live DGX E2E pass.
2. **`DRY_RUN_PASS`** means a proposed installer/uninstaller plan/preview executes without applying it. The uninstall preview exits before the destructive path's operation lock and transition checks; it must **not** be used as proof the real action would succeed.
3. **`FUNCTIONAL_PASS`** means the specified historical model/transaction function passed during that run. It does not imply host stability.
4. **`HOST_STABILITY_PASS`** requires a strict monitored window and no recorded NVIDIA RM `NV_ERR_NO_MEMORY`. READY / monitor rollback alone is never proof of host stability.
5. **`PRODUCTION_READY`** requires the particular profile's clean-host, runtime, rollback, maintenance, and stability gates; no such blanket claim is made here.

## Milestones, acceptance ownership, and stop criteria

### M1 — Release-safe, non-destructive lifecycle coverage (do now)

- Keep `install.sh` and `uninstall.sh` wizard tests on **disposable synthetic `HOME`/`XDG_STATE_HOME`/`XDG_DATA_HOME`** fixture roots in CI; never run real `--purge-all` on the active DGX.
- Confirm Korean/English full uninstall dry-run, normal preserve, explicit purge flags, and cumulative purge preview leave model, release, and install manifest bytes untouched. Use the output of `tests/test_uninstall_wizard_preview.py` as a synthetic-only gate.
- Confirm tests for selector inventory; completed-install settings, profile default refresh, cancel/resume, wizard/CLI plan parity, ownership protection, transitions/locks, and rollback.
- For DGX operator read-only status only, run the exact-SHA guarded `scripts/lifecycle/inspect-readonly-lifecycle.sh` with `QWEN38_LIFECYCLE_AUDIT_TARGET_SHA` set to the CI-qualified checkout. It invokes **only** `install.sh --list-models`, `install.sh --list-backends`, four transaction `status` commands and `scripts/doctor.sh`. It performs no download, installation, uninstall, profile switch, service action or GPU/model launch. Its `COLLECTED_READ_ONLY` means only that inventory/status collection succeeded; **not** a complete live E2E or host-stability PASS. A `PARTIAL_CHECK_FAILURE` requires reviewing the captured per-command exit codes and details, not coercing the host.
- Milestone may become **`M1_SIMULATED_PASS`** after qualifying CI and a read-only DGX inventory/status snapshot. Without that snapshot, classify only **`M1_CI_ONLY`**.

### M2 — Rehearse destructive lifecycle safely (dedicated disposable host only)

Use an independent clean host or disposable VM compatible with the installer to run: clean install→health/model identity→stop/restart→normal uninstall with model retained→reinstall using retained model→targeted purge→ownership-dependent full purge. Capture before/after manifests, release pointers, recorded resource fingerprints, protected user files, exit codes and explicit deletion lists. The single production DGX Spark must **never** be used as the disposable host.

**No host/machine is currently qualified as a disposable environment**, so M2 = NOT RUN. Mock tests alone do not close it.

### M3 — Managed profile switch acceptance (only safe/qualified profiles)

Exercise every allowed pair and crash boundary with reversible controls and stable-host metrics, without deleting model assets. Existing Hybrid↔OrcaRouter historical functional proof is **not** an all-pairs matrix. Reject live attempts involving unsafe H38, and separately flag mazinb/Hybrid strict RM failures. In case of ambiguous rollback state, **fail closed, preserve manifests/attestation, stop** rather than guessing.

M3 = PARTIAL HISTORICAL EVIDENCE / NO ALL-PAIR QUALIFICATION.

### M4 — H38 managed rollout (blocked independent workstream)

The recent actual fixed-image checks establish CT eight-parameter source registration, input-scale postload consumer and possible counted-numel target inclusion, and a complete 221,184-name checkpoint index key grid. They do **not** prove actual initialized input-global-scale values, loader callbacks, unique destination writes, counted-numel correctness or shard buffer lifetime. The strict metadata order gate remains FAIL.

No H38 model/GPU launch, image rebuild, checkpoint tensor payload scan, managed service mutation, host-protection relaxation, CT meta patch, PR Ready or Merge until a separate qualified safety/production acceptance gate permits it. This blocker does **not** prevent M1 synthetic/live-read-only lifecycle validation.

## Go/no-go for this phase

The objective is **operator-lifecycle correctness**, not indefinite H38 loader archaeology. Close the present lifecycle phase when the independent M1 synthetic gate passes, operator read-only state/inventory is attached as evidence, and all remaining M2/M3/M4 live or destructive actions are clearly marked **NOT QUALIFIED/BLOCKED**. Do not label the full installer/uninstaller/model-switch product complete on M1 alone.

See `OPERATIONS.md` for supported commands, `docs/CURRENT-STATUS.md` for H38/RM safety, and `scripts/benchmark/evidence/README.md` for immutable dated observations.

## M1 actual DGX inventory/status snapshot — PARTIAL, do not call healthy (2026-10-12)

**Actual operator execution** at pinned clean HEAD `bbeceaf16c0c4bba4385c38cfead32e5dc243769` collected all seven non-mutating inventory/status/Doctor commands. Model inventory (active OrcaRouter, installed mazinb and Hybrid H6, absent NVIDIA, non-installable lychee888) and backend registry `rc=0`; all **four lifecycle transitions idle**, each `rc=0`. But Doctor `rc=1`: **5 FAIL** (runtime commit attestation missing/unsafe, exited container, no published API port, missing memory-protection monitor PID file, dead health endpoint) and **2 WARN** (legacy runtime image, inactive systemd service). Overall `MANAGED_LIFECYCLE_READONLY=PARTIAL_CHECK_FAILURE`, `lifecycle_audit_rc=3`; **M1 LIVE HOST HEALTH = NOT QUALIFIED**, even though 748 CI tests passed.

[Actual DGX evidence](../scripts/benchmark/evidence/managed-lifecycle-readonly-attempt01-doctor-partial-20261012.md) preserves the state and strict blockers without claiming independent causes. Doctor observed verified immutable current+previous releases, ownership, model 18-shard checkpoint, installed API sockets, healthy point-in-time memory/swap/disk margins, and valid model/container manifest identity. No actual model ran. In particular, Docker `docker port` on the **exited** runtime reported no published port; a wrong port binding is **not established**. Missing monitor PID or runtime-commit attestation is not permission to alter or regenerate them.

**New M1.1 safe offline follow-up**: `scripts/lifecycle/inspect-readonly-runtime-offline.sh` needs an exact clean checked-out SHA and reads only Docker container state/exit/OOM flags/declared port binding, systemd service result and existence/type/mtime of `runtime-commit.env`, `runtime-stop.env`, `monitor.pid`. No service start/restart, cleanup, model/GPU execution, checkpoint loading, or host protection edits; `COLLECTED_READ_ONLY` qualifies **data collection only**. Source guard: `tests/test_managed_runtime_offline_readonly.py`. The next operator evidence must distinguish intentional stopped state from service/runtime failure where feasible; absent logs or ambiguous states remain UNKNOWN.

Until this follow-up resolves the cause and separate live acceptance exists, **do not promote M1 to fully healthy or declare installation, uninstallation, and model switching completely validated**. M2 destructive E2E requires an isolated disposable host. M3 profile all-pairs are unqualified; M4 H38 model is still BLOCKED; the strict RM stability outcome cannot be inferred from temporary healthy memory numbers or absence of an active model process.

## Actual M1.1 offline metadata — status collection PASS, host acceptance still BLOCKED (2026-10-12)

Actual DGX operator ran the offline no-restart inspector at clean `6ce45561640f4069d534cbe04f5064a39095a88a`: `MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY`, `offline_diagnostic_rc=0`. The managed OrcaRouter container is **exited**, `exit_code=0`, `oom_killed=false`, Docker `state_error=""`. It began 2026-10-07 **16:35:45 KST** and ended **22:08:34 KST**. The declared Docker `HostConfig.PortBindings` map is **correct** `8888/tcp → 127.0.0.1:8888`; actual network port map is empty in the exited state. The prior Doctor's `docker port` failure is a **current-runtime readiness** failure, not proof of an erroneous configured binding.

Systemd `Result=success`, `ExecMainCode=1` (systemd process-exit class, **not exit status one**), `ExecMainStatus=0`, but service **inactive/dead**. ActiveEnterTimestamp **22:08:29 KST**, InactiveEnterTimestamp **22:18:17 KST**. Files `runtime-commit.env`, `runtime-stop.env`, and `monitor.pid` were all **ABSENT** at audit time. These point-in-time fields do **not** prove whether operator/protection/managed-transition stop occurred; stopped reason remains `NOT_YET_PROVEN`. The earlier Doctor **5 FAIL / 2 WARN** and M1 full-live-health **NOT_QUALIFIED** classifications are unchanged. [Canonical operator evidence](../scripts/benchmark/evidence/managed-runtime-offline-attempt01-exit0-no-oom-20261012.md).

**Next minimum gate:** the immutable, exact-SHA `scripts/lifecycle/inspect-readonly-runtime-stop-journal.sh` reads only a bounded 160-line historical unit journal window on **2026-10-07 21:55–22:25 KST**; no runtime launch, restart, purge, attestation reconstruction or protection changes. CI/source-only guard `tests/test_managed_runtime_stop_journal_readonly.py`. Journal contents may have sensitive environment/log details; inspect and redact before public sharing. Source/read-only inspector has **not** yet been run on DGX. If journal entries are absent or ambiguous, preserve STOP_REASON=UNVERIFIED and avoid repeating indefinite read-only probes.

This is a decision boundary: after the bounded journal check (or an inconclusive result) resume focus on lifecycle test coverage, UI acceptance, and off-host destructive rehearsal, while H38 model runtime remains independently blocked. A successful journal data collection cannot upgrade M1 host health, model correctness, RM safety or all-profile live E2E.

## M1.2 actual service journal: candidate aborted by memory protection, previous runtime retained stopped (2026-10-12)

The actual bounded `qwen38-flash-next.service` journal at pinned DGX checkout `efafe36fcc2e477e9d0cd110e4db275ba40dc489` **reclassified the managed stop path from unknown to observed**:

- Earlier **22:06:57–22:08:29 KST** `/health`, `/v1/models` and chat API HTTP 200 requests were logged for the **previous** runtime only.
- **22:08:30** explicit `Stopping current runtime container gracefully`, **22:08:35** runtime transition prepared with previous retained and **new candidate** started. Monitor started `protect=1`.
- Candidate readiness wait remained ongoing up to **540/1800 seconds**.
- **22:18:16** exact `Candidate runtime was stopped by memory protection during startup; leaving managed runtime stopped`; **22:18:17** `Previous runtime container restored but left stopped after memory protection`; `Runtime transition aborted by memory protection (state=idle)`.

The earlier canonical Docker zero exit / no OOM kill reflects a **graceful previous-container transition stop**; the recorded memory-protection intervention applied to the candidate and rollback workflow. Thus the current inactive runtime is an expected **fail-closed result of the logged protection abort**, not evidence of a bad Docker loopback binding. Do not infer that real host memory went OOM: **the particular monitor counter/threshold, possible cold-load false positive, and strict NVIDIA RM stability remain UNVERIFIED**.

[Canonical actual bounded journal evidence](../scripts/benchmark/evidence/managed-runtime-stop-journal-attempt01-protected-abort-20261012.md). The original reporter logfile was not byte-hashed. The helper's literal `RUNTIME_STOP_CAUSE=NOT_YET_CLASSIFIED` is a **static data-collection marker**; human review of explicit journal lines supports only `CANDIDATE_PROTECTION_ABORT_CONFIRMED`, not `MONITOR_TRIGGER_PREDICATE_PROVEN`.

**M1 acceptance remains PARTIAL**: inventory/schema/checkpoint/assets/transition status PASS, Doctor's earlier 5 FAIL and 2 WARN remain, actual live service readiness NOT_QUALIFIED. We will not restart or change monitor thresholds to produce green Doctor/CI. Exactly one final read-only monitor numerical-sample probe (`scripts/lifecycle/inspect-readonly-monitor-trigger.sh`) is staged with fail-closed SHA/file-size/type checks; it reads only structured local Oct07 monitor messages, not arbitrary container logs. Its actual host result is PENDING. If it cannot explain the trigger, stop probing and preserve `UNKNOWN`, returning work to lifecycle install/uninstall/profile-switch verification in synthetic/disposable environments. M2 destructive E2E NOT_RUN, M3 all-profiles E2E NOT_QUALIFIED, M4 H38 managed BLOCKED.

## M1.3 Actual protected-stop numeric threshold RESOLVED — return to lifecycle verification (2026-10-12)

The last bounded read-only monitor numeric probe **ran** on DGX at exact clean `7e4580bdca4054a788715bdf141e006bbb6b3f59`, reporting `MONITOR_TRIGGER_READONLY=COLLECTED_READ_ONLY`, `monitor_audit_rc=0`, **17** structured historical Oct07 messages from a ~2.24MB local monitor log. This operator result **supersedes "monitor probe pending / trigger numeric UNKNOWN" earlier in this document**.

Actual monitor startup threshold settings at **22:08:35 KST**: protect mode, non-CMA free floor **2GiB**, low-available/free gate **10GiB**, swap-growth gate **256MiB**, swapfree floor **8GiB**, and logged protection count `N/5`. At **22:17:33** non-CMA free **2,017 MiB** was marginally below 2GiB but swapgrowth only **17 MiB** and protect remained `0/5`. From **22:17:35** non-CMA free dropped to **1,151 MiB** and swapgrowth jumped to **654 MiB**, beginning `protect=1/5`. At **22:17:37, :39, :41, :43** the counter reached **2/5, 3/5, 4/5, 5/5**. At **22:17:43** a monitor entry says **`PROTECT stopping qwen38-flash-next gracefully to preserve host stability`**. Throughout these five samples non-CMA available was **well over 10GiB** and swapfree was **well over 8GiB**. Consequently the **actual observed branch was non-CMA immediate-free below 2GiB AND swap-growth greater than 256MiB, five consecutive samples**; **not** the low-available or low-swapfree branch. The managed service reported the protected candidate abort and stopped rollback at **22:18:16–22:18:17**.

[Canonical real numeric evidence](../scripts/benchmark/evidence/managed-monitor-trigger-attempt01-low-free-swap-growth-pass-20261012.md) is a grounded operator transcript; original /tmp logfile hash not independently verified. **This does not prove the monitor's heuristic is optimal, nor candidate model correctness, actual NVIDIA RM error or strict host stability.** A true host OOM, harmful vs benign PLE paging, and possible false-positive remain UNVERIFIED. No model was launched for this verification.

**STOP RULE achieved for this line of investigation:** no more DGX runtime/monitor probes for the historical event unless a new independent decision specifically requires them. The operator's primary goal is managed **installer/uninstaller/model/profile switch** completion. Continue existing safe implementation/test acceptance and restrict destructive E2E to an independently disposable host, with real GPU/H38 activation blocked. M1 **CI/synthetic passed**, but M1 **live host Doctor still FAIL_5/WARN_2 and service stopped by fail-closed protection**; M2 destructive live E2E NOT_RUN; M3 model all-pairs NOT_QUALIFIED; M4 H38 BLOCKED. The historic monitor explanation is not an entitlement to restart model, weaken protection, manufacture runtime-commit attestation, mark PR Ready or Merge.


## Early swap-ownership refusal for destructive uninstall (2026-10-12)

**Safety contract:** `uninstall.sh --purge-swap` and `--purge-all` (which implies swap purge) now reject a manifest with `SWAP_OWNED!=1` **after dry-run preview but before** acquiring the operation lock, bootstrapping asset ownership, stopping Docker/systemd, or deleting any installer data. The former check was positioned after teardown and, for full purge, after owned asset removal; an unowned swap could therefore leave a partially uninstalled deployment before refusing. `--dry-run` remains preview-only and does not certify real purge eligibility.

`tests/test_uninstall_wizard_preview.py::test_unowned_swap_purge_fails_before_host_or_fixture_mutation` exercises the real CLI on disposable HOME/XDG state for selected swap and full purge with daemon-command denial stubs and byte-for-byte fixture preservation. This is a **synthetic fail-closed regression**, not an authorized live DGX uninstall. M2 destructive E2E remains NOT_RUN; M1 actual host Doctor remains NOT_QUALIFIED and H38 runtime remains BLOCKED. PR #259 remains Draft/Open, merge blocked.


## Uninstall final-consent cancellation is read-only before lock/bootstrap (2026-10-12)

The real `uninstall.sh` previously ran `asset_bootstrap_install` and destructive-eligibility preflights before asking the operator to enter `DELETE`. A declined confirmation could create/update `asset-ownership.json` despite no authorized uninstall. The `DELETE` consent check is now **before** `acquire_operation_lock` and cumulative-ownership registry writes, but **after** strict manifest parsing and early unowned-swap refusal. EOF is an explicit cancellation error. `--yes` bypasses only interactive consent; post-lock transaction guards and asset preflights remain mandatory. This is not a guarantee of rollback **after** destructive steps begin.

New `tests/test_uninstall_wizard_preview.py::test_cancel_or_eof_preserves_ownership_and_install_state` calls the real non-dry-run CLI with a disposable HOME/XDG fixture. English default, Korean selected purge, full purge refusal and full purge EOF must reject before host command execution and preserve fixture bytes without creating `asset-ownership.json` or `operation.lock`. External Docker/systemd/sudo/swapoff commands are denied by PATH stubs. Initial [CI 38186275070](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38186275070) SUCCESS (766/766 synthetic tests) at commit `2e86ed4fa75a28bd585ff932cffdd4c4afab59ef`; final CI for the extended pre-existing-registry fixture tracked in PR #259. No actual DGX state was touched. M1 host NOT_QUALIFIED; M2 destructive E2E NOT_RUN; M3 all-profile E2E NOT_QUALIFIED; M4 H38 BLOCKED; PR #259 Draft/Open, Merge BLOCKED.

Existing cumulative-registry preservation is additionally tested by `test_cancel_preserves_existing_ownership_registry_bytes`: a pre-existing valid `asset-ownership.json` must retain its exact bytes on operator cancellation, with an owned-model manifest that would otherwise trigger legacy bootstrap migration. No host-side daemon calls are allowed. A confirmed, actively executing uninstall still requires independent destructive E2E qualification.


## Preflight-staged ownership registry for approved uninstall (2026-10-12)

The approved real `uninstall.sh` previously bootstrapped the **canonical** cumulative ownership registry before `preflight-one`, `preflight-purge`, external-container references and unowned-service checks. A failure could leave an altered `asset-ownership.json` without any authorized teardown. The revised flow, under the existing operation lock, copies the registry into a private same-filesystem `.uninstall-preflight.*` directory, runs the **existing** legacy bootstrap and eligibility checks against that staged copy, and publishes it only if all checks succeed; on a handled failure, an EXIT trap deletes the staged directory. An unchanged original registry is not needlessly replaced. Symlink/non-regular canonical registry paths are rejected. The operation lock file may remain after refusal. A process killed without running EXIT traps may leave a private staging directory for later inspection; no claim of crash-atomicity is made.

The new `test_approved_purge_preflight_failure_preserves_cumulative_registry` uses the real CLI with `--yes` on disposable HOME/XDG synthetic owned base + retained unowned dependent, exercising both `--purge-model` and `--purge-all`. It asserts blocked deletion, identical canonical registry/manifest/model bytes, no external host mutator calls and no left-behind staging directory. The actual DGX was not touched; this is synthetic failure-preflight coverage, not destructive-install/uninstall E2E or proof of post-teardown recovery. M1 live Doctor still NOT_QUALIFIED; M2 destructive E2E NOT_RUN; M3 all-pairs NOT_QUALIFIED; M4 H38 BLOCKED. PR #259 Draft/Open, merge blocked.


An additional `test_external_container_image_refusal_preserves_registry` exercises a synthetic `IMAGE_OWNED=1` with an external Docker-container reference. Read-only Docker image inspection and `ps` are stubbed; `docker rm`, image deletion, sudo/systemctl/swapoff, real host data access and model load are not allowed. The installer-owned image is refused at the **external-container preflight**, and the canonical registry and fixture bytes remain unchanged. This expands synthetic eligibility refusal coverage without asserting successful destructive uninstall.


### Synthetic approved-uninstall preflight result — CI verified (2026-10-12)

Exact tested code HEAD `c332959df7676d3d87a69eb628b94fa5af862e41`: [GitHub Actions CI #38188708849](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38188708849) **SUCCESS, 769/769 Python unit tests**, Bash syntax PASS, ShellCheck PASS, Python compilation PASS, whitespace PASS. Earlier base staging code HEAD `6186294fda78d9fed5d5bac8f35029b52c4a2856`: [CI #38188545527](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38188545527) **SUCCESS, 768/768**. This evidence covers synthetic failure branches for retained dependent model and externally referenced image; it is **not** evidence of successful real deletion or crash-atomicity. No DGX host operations were executed. All M1 host-health, M2 destructive E2E, M3 all-pairs, M4 H38, and PR #259 merge blockers remain.


## Docker removal failure and partial-uninstall retry safety (2026-10-12)

Previously `uninstall.sh` ignored **every** `docker rm -f` failure with `|| true`, risking model/image/release deletion when the Docker daemon or authorization was broken and the managed container could still exist. Now arbitrary Docker errors are **fail-closed before asset purge**; only an exact Docker `No such container: <managed name>` message permits idempotent continuation. `PHASE=complete` remains when service/container removal fails, allowing an operator-directed retry. `asset-ownership.json` may already reflect the successful preflight; the service may already have been disabled or removed. Neither rollback of completed teardown nor crash-atomicity is claimed. Real managed host and H38 model remain untouched. New disposable synthetic fault-injection regressions cover service-remove failure, Docker-remove failure, retry-after-recovery and already-absent Docker container; final CI result to be recorded in PR #259. M1 live host NOT_QUALIFIED, M2 destructive E2E NOT_RUN, M3 profile all-pairs NOT_QUALIFIED, M4 H38 BLOCKED, PR Draft/Open, Merge BLOCKED.


### Post-teardown failure and safe retry: synthetic CI acceptance (2026-10-12)

**Evidence:** [CI #38189466067](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38189466067) **SUCCESS, 771/771** at `09527d81121ad6fe820400382a12eb9a443318b6`; [CI #38189596217](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38189596217) **SUCCESS, 772/772** at `69df950fc4a7f1c6038ab8aff9f5e3ee45dc80b7`, including Bash syntax, ShellCheck, Python compilation and whitespace checks.

A synthetic real-CLI sequence using only disposable HOME/XDG and command denial/stubs shows:
1. Managed service-removal fault => no Docker removal attempt, owned synthetic model intact, manifest `PHASE=complete`.
2. Service removal succeeds, Docker daemon removal fails => script exits nonzero **before** model/image/release purge, records no completed uninstall, owned model and release preserved; published registry retains ownership evidence.
3. After fault clearance, retry completes, removes the **synthetic owned model only**, retains release data and sets `PHASE=uninstalled`.
4. An exact Docker `No such container` diagnostic is idempotent; unowned model and release remain.
5. On `--purge-all`, after **synthetic model and image removal** a simulated swap-remove failure exits nonzero with remaining fake swap and release preserved, manifest still `PHASE=complete` and cumulative registry reflecting completed asset removal. On retry after fault clearance, the script tolerates the already absent owned model/image, removes only the fake swap and synthetic release/manifest, and completes.

This proves bounded **synthetic retry behavior**, NOT rollback of previously removed components, interruption/crash durability, actual systemd/Docker/PLE behavior, independent disposable-host install/remove/reinstall E2E, or single-DGX host qualification. Actual DGX was untouched. M1 actual host NOT_QUALIFIED; M2 destructive E2E NOT_RUN; M3 all-profile E2E NOT_QUALIFIED; M4 H38 BLOCKED. PR #259 remains Draft/Open, Ready/Merge BLOCKED.


## SIGKILL interrupted-uninstall preflight recovery (2026-10-12)

Under the lifecycle operation lock and before creating a staged ownership copy or doing any teardown, `uninstall.sh` now refuses existing `.uninstall-preflight.*` artifacts, including symlinks. A `SIGKILL` or power loss bypasses shell EXIT traps, so these private staging snapshots may survive. Do **not** automatically delete them or treat them as canonical ownership evidence. Inspect each exact stale path, verify ownership and contents, confirm no concurrent lifecycle operation, and handle its removal/quarantine only as a separately authorized maintenance action. No blanket wildcard deletion on the active DGX. This guard is fail-closed: the install manifest and canonical ownership registry remain authoritative, and model/image/swap removal cannot proceed while an unreviewed preflight snapshot exists. Synthetic SIGKILL crash tests and exact GitHub CI evidence are tracked in PR #259; actual power-loss durability is NOT_QUALIFIED. PR remains Draft/Open and merge blocked.


### Interrupted uninstall recovery procedure and validation boundaries (2026-10-12)

**Stop condition:** a `.uninstall-preflight.*` artifact, missing model ownership manifest, drifted registry fingerprint, interrupted model deletion, or a state/host mismatch is **not** permission to resume unattended `uninstall.sh --yes`. Leave all host protection and stopped runtime settings intact.

1. Preserve evidence before any repair: read the canonical `install.env`, `asset-ownership.json`, exact `.uninstall-preflight.*` entries, file owner/mode and applicable logs **without executing the staged file or running host mutators**. The canonical registry is the only ownership authority; staged snapshots are untrusted. Acquire or confirm exclusive lifecycle maintenance ownership before any later mutation.
2. Reconcile actual read-only service/container/swap state with the recorded manifest. `PHASE=complete` after a crash **does not** mean the service is still installed, container still exists, model remains complete or swap is intact. Never infer successful teardown from parent process exit status alone; child deletion commands may outlive a killed parent.
3. For a verified orphan staging directory, document its exact path and integrity, quarantine/clear **only that exact path** after operator review, and rerun preflight before resuming; never use broad `rm -rf` globs or follow symlinks. Unreviewed staging blocks the real uninstaller.
4. For a partially deleted model with a missing/drifted `.qwen38-model-manifest.json` or `.qwen38-hybrid-manifest.json`, keep the original cumulative registry and the surviving model data; **do not invent a marker or weaken preflight**. Recovery requires independent trusted backup/provenance verification, otherwise quarantine and a separately authorized reinstall on an isolated disposable host.
5. If a fully removed owned model is already absent but a dedicated swap/release remains, a repeat purge is eligible **only after** checking the original model path, ownership history, live host state, swap provenance and pending lifecycle artifacts. No automated or live sole-DGX destructive recovery is authorized by the synthetic tests.
6. Preserve an interruption evidence report (files/hashes, timeline, host-command results, whether child process survived, repair decision). Host power-loss filesystem ordering/fsync, SIGKILL of the whole process group, real teardown replay and install→remove→reinstall remain unverified separately.

Synthetic `test_sigkill_during_stage_requires_manual_stale_recovery`, `test_sigkill_partway_through_model_delete_requires_verified_recovery`, and `test_sigkill_at_swap_after_model_purge_can_resume` use the **real** CLI with disposable HOME/XDG, fake owned model/swap and PATH-denied Docker/sudo/systemctl/swapoff. Their SIGKILL is injected from a child stub and the stub must exit immediately rather than completing its own deletion after killing the parent. These tests do not simulate power loss or provide live-host authorization. Previous failing CI attempts due to a child-stub execution bug are retained as historical failures; the corrected commit and its CI outcome are recorded in PR #259. All M1 actual-host/M2 real-destructive/M3 all-profile/H38 gates remain blocked or unqualified; PR #259 remains Draft/Open, Ready/Merge BLOCKED.


## Guarded DGX code synchronization and synthetic-only local verification (2026-10-12)

The previous 775/775 GitHub Actions result was **CI**, not evidence that the operator's single DGX had fetched the latest branch or run any tests locally. To close this handoff gap without touching live host resources, `scripts/lifecycle/verify-synthetic.sh` now validates an explicitly supplied 40-character checkout SHA, clean Git worktree, exact `feat/h38-managed-integration` branch and matching `origin/feat/h38-managed-integration` tracking ref **without any Git mutation**. It then runs bounded Python synthetic lifecycle suites inside a disposable HOME/XDG_STATE_HOME/XDG_DATA_HOME/TMPDIR, with a first-in-PATH deny wrapper for Docker, sudo, systemctl, swapoff/swapon, mount/umount and nvidia-smi. Tests are restricted to installer/uninstaller preview, ownership, operation lock, lifecycle integration and non-mutating lifecycle snapshot tests; no actual install/uninstall, Docker, service change, runtime startup, model download or host Doctor is invoked. The test wrapper is itself exercised on GitHub Actions in `--ci` mode and refuses `--ci` outside `GITHUB_ACTIONS=true`.

**Operator sync procedure, not executed by ChatGPT:** on the actual DGX working checkout, require `git status --porcelain=v1 --untracked-files=all` empty and the expected feature branch already selected; `git fetch --prune origin`; confirm `origin/feat/h38-managed-integration` equals the **exact tested target SHA**; then `git merge --ff-only origin/feat/h38-managed-integration`, confirm HEAD and worktree, and invoke the new verifier with that SHA. No `git reset --hard`, stash/pop, force merge or automatic checkout switching. Sync/test modifies the local Git checkout and disposable test files only; no remote host access or DGX test was performed from ChatGPT. **Report DGX_LOCAL_SYNTHETIC=NOT_RUN until the operator supplies actual local output.** Keep `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, PR #259 Draft/Open; Ready/Merge BLOCKED.
