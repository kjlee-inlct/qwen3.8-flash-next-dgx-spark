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
- For DGX operator read-only status only: `./install.sh --list-models`, `./install.sh --list-backends`, `bash scripts/profile-switch-transition.sh status`, `bash scripts/runtime-transition.sh status`, `bash scripts/update-transition.sh status`, `bash scripts/release-profile-refresh-transition.sh status`, `./scripts/doctor.sh`. These must **not** invoke installation or removal. The operator's live output is needed before claiming a healthy state.
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
