# Installer / Profile Manager Plan

This document is the canonical implementation plan and option-inventory snapshot for the installer/profile-manager work. It records current product behavior, known parity debt, safety boundaries, and the order in which the remaining work should be completed without introducing a second lifecycle manager.

The baseline inspected at the start of this work was `main` at `aab3cd48ba0af20446d18fe85ac7d4cf0dfbc38f`. That SHA is an observation, not a permanent pin; each phase starts from the then-current `main`.

## Product contract

The managed product has one lifecycle. `install.sh`, the installation manifest, cumulative asset ownership, profile-switch/runtime/update/settings transaction helpers, immutable releases, and the managed systemd service remain authoritative. A profile switch is **not** uninstall + reinstall.

The target UX contract is:

- every Wizard setting has a CLI representation;
- every supported user-facing CLI setting is selectable in the Wizard;
- Wizard and CLI normalize into the same internal values and final plan;
- informational/control-only CLI commands may remain CLI-only when they are not settings;
- developer/internal environment variables are outside the user-facing parity contract;
- fresh install, interrupted resume, completed-install management, and profile switch are distinct applicability contexts and must not be conflated;
- preview paths are non-mutating, while live changes must preserve transaction/recovery and ownership semantics.

`tests/test_installer_option_parity.py` freezes the CLI inventory and prevents user-facing setting parity debt from silently returning.

## Existing lifecycle reused by this work

The following existing contracts are reused rather than reimplemented:

- `scripts/model/model-profiles.sh` — model/profile registry and pinned model metadata;
- `scripts/manage-models.sh` — local model/image inventory, retirement, migration, and root relocation operations;
- `scripts/lifecycle/profile-switch-transition.sh` — persisted managed profile replacement;
- `scripts/runtime/runtime-transition.sh` — candidate/rollback runtime replacement;
- `scripts/lifecycle/settings-transition.sh` — recoverable completed-install settings-only mutation;
- update transition helpers — immutable release cutover;
- `scripts/lib/state_file.py` — strict state-file parsing;
- `scripts/lib/asset_ownership.py` — cumulative asset ownership/fingerprints;
- `qwen38-flash-next.service` / managed service helpers — runtime ownership and health gate.

No parallel profile database, supervisor, state parser, or model-purge switch mechanism should be introduced.

## Profile state vocabulary

The UI and documentation must keep these meanings distinct:

| Term | Meaning |
| --- | --- |
| available | known by the registry |
| installable | installer can prepare it |
| installed | managed checkpoint/generated asset has a managed manifest with `status=complete` |
| incomplete | managed checkpoint path has a managed manifest that is not complete |
| unmanaged | expected local checkpoint path exists without a managed manifest |
| active | current managed runtime profile |
| functional | functional validation passed |
| host-stable | strict RM host-stability rule passed |
| qualified / stable | promoted for normal default use |

Current profile intent remains:

| Profile | Registry state | Installable | Qualification note |
| --- | --- | ---: | --- |
| `orcarouter` | stable / default | yes | primary managed profile |
| `nvidia` | experimental | yes | comparison/compatibility path |
| `mazinb` | experimental | yes | do not imply host-stability qualification |
| `orcarouter-hybrid` | experimental / generated | yes | functional pass; strict host-stability fail |
| `lychee888` | planned | no | must not appear as selectable |

A valid measured `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` event remains a strict HOST-STABILITY FAIL even if fallback later reaches READY. Memory-monitor firing is a safety heuristic, not equivalent host-stability evidence.

## CLI ↔ Wizard inventory

“Both” means a Wizard field exists somewhere. Completed-install management covers the persisted runtime/API/service surface, including preview/live apply and immediate/deferred runtime restart.

| Setting / command | CLI | Wizard | Current applicability / classification |
| --- | --- | --- | --- |
| language | `--lang` | yes | fresh selection; saved language reused on existing install |
| profile | `--model` | yes | fresh and completed-install profile selection |
| model root | `--model-root` | yes | fresh install; profile switch retains existing root by design |
| config override | `--config-override` / `--no-config-override` | yes | fresh path and completed-install settings editor; explicit CLI clearing is representable, while profile-required compatibility falls back to its automatic managed config |
| list profiles | `--list-models` | no field | informational CLI command; now renders the same registry-backed profile/inventory view used by the Wizard |
| list backends | `--list-backends` | no field | informational CLI command |
| monitor enable/disable | `--monitor` / `--no-monitor` | yes | fresh and completed-install settings editor |
| protection | `--protect` | yes | fresh and completed-install settings editor |
| MemAvailable threshold | `--monitor-min-available-gib` | yes | fresh and completed-install settings editor |
| MemFree threshold | `--monitor-min-free-gib` | yes | fresh and completed-install settings editor |
| MemAvailable gate | `--monitor-free-gate-gib` | yes | fresh and completed-install settings editor |
| SwapFree threshold | `--monitor-min-swap-free-gib` | yes | fresh and completed-install settings editor |
| consecutive samples | `--monitor-consecutive` | yes | fresh and completed-install settings editor |
| monitor heartbeat | `--monitor-heartbeat` | yes | fresh and completed-install settings editor |
| API access mode | `--api-access` | yes | fresh and completed-install settings editor |
| Docker API port | `--api-docker-port` | yes | fresh and completed-install settings editor |
| LAN address | `--api-lan-address` | yes | fresh and completed-install settings editor |
| LAN port | `--api-lan-port` | yes | fresh and completed-install settings editor |
| service enabled/disabled | `--service` / `--no-service` | yes | fresh and completed-install settings editor |
| start policy | default / `--no-start` | yes | completed-install editor asks restart now vs defer |
| refresh profile defaults | `--refresh-profile-defaults` | yes | completed-install management action; existing core reused |
| dry-run | `--dry-run` | yes | completed-install editor defaults to preview and requires explicit live apply |
| non-interactive confirmation | `--yes` | n/a | execution control; no Wizard field required |
| manifest migration | `--migrate-manifest` | n/a | maintenance command; no normal Wizard field required |
| help | `--help` / `-h` | n/a | informational control |

The parser supports the full monitor-threshold CLI surface. `usage()` must list those flags; the parity regression test prevents help/inventory drift from returning.

## Wizard inventory

### Fresh install

The flow remains: language → model/profile → model storage → runtime/config/monitor settings → API/service → normalized final plan and confirmation.

### Interrupted install

An incomplete manifest continues the existing resume path. It must **not** expose completed-install management or a profile switch while an install is mid-phase. Resume/recovery semantics stay fail-closed.

### Completed managed install

A complete managed install enters an installed-setup management menu before the existing profile selector. The menu offers profile selection/switch, runtime/API/service settings edit, current-profile default refresh, or cancel.

Profile selection is derived from `list_model_profiles` rather than hardcoded profile cases. It marks the active profile, derives the default from registry metadata/current state, computes the cancel index from the registry length, and enters the existing transactional profile-switch core only when the target changes. Registry candidates such as `lychee888` are visible as planned/not-installable but remain non-selectable.

The settings editor stages config override, monitor/protection thresholds, API access/ports, and service enablement in memory. Staged values are applied immediately before the shared `[6/6]` normalized-plan boundary, after manifest parsing and CLI override resolution. This keeps the existing parser/validation/plan path authoritative rather than duplicating it in the UI.

Preview remains the default. Without CLI `--dry-run`, the editor explicitly asks whether to apply after final-plan review; choosing live apply then asks whether runtime changes should restart now or be deferred. CLI `--dry-run` always forces preview. Live mutation begins only after the existing final `Continue?` / `계속 진행합니까?` approval.

Profiles that require a compatibility override, currently `orcarouter`, do not expose “clear override” in completed-install settings. An existing installer-owned compatibility config stays owned when retained; replacing it with an external custom config transfers the manifest to unowned custom-config semantics only after transaction commit.

## Priority classification after transactional completed-settings slice

### P0 — product contract / operator correctness

- **Implemented:** completed-install Wizard profile selection/switch reuses the transactional CLI core.
- **Implemented:** CLI and Wizard converge on one normalized final-plan snapshot before review/execution.
- **Implemented:** completed-install management menu and runtime/API/service settings editor feed the normalized plan.
- **Implemented:** current-profile default refresh is reachable from the Wizard through the existing `REFRESH_PROFILE_DEFAULTS` path.
- **Implemented:** live settings apply has transactional/recoverable cleanup and creation of owned proxy and managed service resources.
- **Implemented:** completed-install Wizard exposes preview/live choice and immediate/deferred runtime restart; the option-parity test has no remaining user-facing setting debt.
- **Accepted on DGX:** final implementation was exercised through guarded dry-run, real no-op live commit, and explicit deferred-runtime rollback with byte/runtime invariants.

### P1 — architecture / drift prevention

- **Implemented and DGX accepted:** centralize user-facing installer option metadata in one registry used by generated help and parity tests;
- **Implemented and DGX accepted:** derive Wizard profile display/status/installability/default metadata from the profile registry;
- **Implemented and DGX accepted:** one read-only profile-manager view combines registry availability with managed local checkpoint/image inventory and powers both the Wizard and `--list-models`;
- resolve remaining contextual presentation differences for language/model-root/execution controls without creating duplicate state;
- **Implemented and DGX accepted:** render a shell-safe equivalent CLI preview from the canonical normalized plan, with forced `--yes --dry-run` replay safety.

### P2 — operator polish

- consolidate list/current/status presentation without replacing existing entry points;
- improve localized profile labels/help text after metadata ownership is centralized;
- keep planned backend work (`sglang`) independent from checkpoint-profile selection.

## Safety rules

Profile selection does not duplicate switch logic. Existing strict manifest parsing, transaction-idle checks, shadow candidate manifest preparation, cumulative asset ownership, managed systemd ownership, runtime health/model-identity/attestation, and commit/rollback/recovery remain authoritative.

Dry-run must remain non-mutating: no transaction state, manifest change, download, swap, release, service, proxy, container, or asset-ownership mutation.

### Settings apply transaction

`scripts/lifecycle/settings-transition.sh` is the settings-only lifecycle boundary. It does not add a new state parser or supervisor: both the live and candidate manifests are parsed through `state_file.py install-maintenance`, and runtime restart continues to reuse the existing managed service or `scripts/runtime/runtime-transition.sh` path.

The transaction rejects model/runtime identity changes such as profile, repository/revision, model directory, image, served name, and swap identity. Target API/service ownership must match the target settings, a settings transaction cannot overlap profile/update/runtime transitions, and the shared operation lock blocks unrelated lifecycle mutators while interrupted settings state exists.

The persisted transaction keeps fixed backup/target manifests, their digests, start policy, previous runtime activity markers, and a bounded phase. The apply phases are:

1. `preparing` — backup/target are validated and persisted while the live manifest remains unchanged;
2. `activation-guarded` — an existing owned service is boot-disabled before target-manifest activation, so a reboot cannot automatically launch an uncommitted target through systemd;
3. `activated` — the target manifest is live while owned proxy/service/runtime resources are being moved;
4. `resources-applied` — target resources are verified, with service boot-enable still deferred;
5. `committing` — the target service is boot-enabled when requested, final resources are verified, released installer-owned config is cleaned safely, and transaction artifacts are removed.

Rollback/recovery restores the backup manifest and symmetrically recreates/removes owned proxy and service resources. Recovery trusts only resource ownership proven by the backup or target manifest, preventing an interruption immediately after activation from misclassifying the previous owned resources as unmanaged. If restart was explicitly deferred and service enablement did not change, rollback preserves the existing runtime and verifies the pre-transaction service/container activity markers instead of recreating the service. If the previous runtime was not running, rollback also prevents an accidentally started target runtime from being left behind.

An interrupted settings transaction intentionally blocks other lifecycle mutation until explicit recovery. The operator recovery entry point is:

```bash
bash scripts/lifecycle/settings-transition.sh recover
```

This is a fail-closed recovery contract, not a claim that every incomplete transaction is automatically completed on host boot.

Installer-owned `config.vllm.json` is not silently orphaned. A settings candidate may not invent new config ownership; an owned managed config may only retain its existing ownership/path, and when a committed change releases that owned config in favor of an allowed unowned configuration, the old managed file is removed only at commit. Rollback leaves it intact.

## Common normalized plan — 2026-10-06

`scripts/lib/install-plan.sh` is the installer-only normalized plan boundary. It runs immediately before `[6/6]`, reuses existing monitor/API validators, canonicalizes relevant paths, snapshots profile/model/image/config/monitor/API/service/switch/start/dry-run values into versioned `PLAN_*` fields, and reapplies that snapshot before the existing renderer/lifecycle code continues.

The normalized-plan DGX dry-run was accepted on implementation head `d528f4f2f4b4d270e81edec3cf47d2218f74b886` after CI #1218 passed all 493 tests. `install.env`, `runtime-commit.env`, service/container identity, `StartedAt`, and lifecycle transaction state remained unchanged.

## Completed-install settings management — preview slice — 2026-10-06

`scripts/lib/install-completed-manager.sh` added the installed-setup management UI without adding a new execution engine. It is sourced only for `install.sh`; uninstall and other Wizard consumers do not inherit installer-specific state.

The management UI stages settings in memory, lets the existing manifest/CLI resolution complete, and reapplies staged values immediately before `install_plan_finalize`. Current-profile default refresh reuses the existing `REFRESH_PROFILE_DEFAULTS` implementation.

Guarded DGX acceptance on implementation head `603aa0391d436eb2a6bd459d924ddcff2d0f5a5c` passed after CI #1228 passed 499 tests. The settings action retained `orcarouter`, staged monitor values `7/3/11/9 GiB`, 6 consecutive samples and a 30-second heartbeat, normalized the current LAN configuration to `local only: 127.0.0.1:8888`, and staged service disable as `Docker container via immutable current release`. The command line intentionally omitted `--dry-run`; that preview slice forced the existing `DRY-RUN complete` path.

Post-run checks proved the preview was non-mutating: `install.env` and `runtime-commit.env` digests were unchanged, the managed service remained active, container ID and `StartedAt` were unchanged, no runtime/update/profile-switch transaction file was created, and the live proxy listeners remained present at the Docker bridge and LAN addresses. The first acceptance wrapper had one harness-only false negative because it grepped `This PC only` while the canonical renderer emits `local only`; the corrected invariant check passed without rerunning the installer.

That preview acceptance remains valid evidence for the editor and normalized plan, but it is not evidence for the live transaction or host stability.

## Completed-install settings management — transactional apply slice — 2026-10-07

The accepted implementation code head is `33a7f16e282672b5aa256cc662c026637e5b7afb`, validated by CI #1264. The branch adds the recoverable settings transaction, service boot-enable deferral, symmetric proxy/service rollback, config-ownership cleanup, commit-failure propagation, and rootless resource integration coverage.

The rootless transaction tests cover both directions of the destructive resource boundary: local/no-service → Docker proxy + managed service proves the service is installed but boot-disabled until commit and enabled only at commit; Docker/service → local/no-service proves removal during apply and restoration of proxy/service ownership during rollback. Additional tests cover activation interruption, activation-guard recovery, immutable identity rejection, operation-lock exclusion, config ownership claims, committed cleanup, rollback preservation, manager commit failure followed by recovery, no-op preservation of existing service/proxy units, and deferred rollback that preserves an already-running runtime.

Final-head dry-run acceptance first passed on `56088213776c70546f96266c626c006644f3f019`: current `orcarouter` / LAN / managed-service settings were rendered through completed-install management with CLI `--dry-run`, while `install.env`, `runtime-commit.env`, service/proxy state, container ID, `StartedAt`, lifecycle artifacts, and worktree state remained unchanged.

The first live no-op transaction then exposed an implementation defect: a retained managed service was unnecessarily recreated when restart was deferred. The host remained safe—the regenerated unit's `WorkingDirectory` and `ExecStart` matched both the attested runtime root and the current immutable release—but the unit SHA changed, so acceptance correctly failed. A subsequent review found the same no-op churn pattern in managed proxy recreation. Both were fixed so semantically unchanged retained resources remain byte-identical.

DGX no-op live acceptance passed on `7a7f3457b9f94e72acb0c84c6aadbdc427006902` after CI #1262. A real `prepare -> apply -> commit` executed with restart deferred; `install.env`, `runtime-commit.env`, the managed service unit, proxy socket unit, proxy service unit, container ID, and `StartedAt` were all unchanged, while the service and LAN proxy remained active/boot-enabled and transaction state returned to idle.

Before exercising rollback, review found that deferred rollback could unnecessarily recreate/start an already-running managed service. That path was fixed on `33a7f16e282672b5aa256cc662c026637e5b7afb`, with CI #1264 green. Real DGX rollback acceptance then temporarily changed only `MONITOR_HEARTBEAT=60 -> 61`, prepared/applied with `START=0`, reached `resources-applied` with service boot enable guarded, and invoked explicit rollback instead of commit. Rollback restored `install.env` byte-for-byte and heartbeat 60, kept service/proxy unit SHAs unchanged, preserved runtime attestation/container ID/`StartedAt`, returned the service to active + boot-enabled, and left no lifecycle artifacts.

These acceptances validate installer/settings transaction behavior only. They are not runtime host-stability qualification and do not alter the strict `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` rule.

## Registry-backed profile manager — 2026-10-07

The accepted implementation code head is `46f929d74895699aff7b100ada9d844bcd9270ef`, validated by CI #1278. The slice removes hardcoded profile names/order/case mapping from the Wizard and adds `scripts/model/profile-manager.sh` as a read-only presentation/inventory layer over the existing `scripts/model/model-profiles.sh` registry. No second profile database, state parser, lifecycle engine, or asset-retirement registry was introduced.

User-facing profile display names now live with registry status/installability/default/repository metadata. Wizard ordering and numeric selection come from `list_model_profiles`; the current profile/default choice and cancel index are derived dynamically. Planned registry candidates are presented separately and cannot be selected. Numeric menu input is normalized as decimal so leading-zero values cannot accidentally enter Bash octal arithmetic.

Local inventory is deliberately stricter than path existence. A profile is `installed` only when its managed model/hybrid manifest reports `status=complete`; a managed but unfinished checkpoint is `incomplete`, a path without a managed manifest is `unmanaged`, and a missing checkpoint is `absent`. Docker image presence is read-only inventory. The strict install manifest supplies the active profile and model root, so custom roots are visible; after uninstall, a retained custom-root checkpoint remains visible as installed but is no longer marked active.

The same presentation/inventory helper now powers both completed-install profile selection and `install.sh --list-models`. Existing `manage-models.sh` retirement/migration/dependency semantics remain unchanged; this slice does not replace that operator tool or its asset definitions.

Guarded DGX acceptance on `46f929d74895699aff7b100ada9d844bcd9270ef` passed after CI #1278. The live inventory reported:
- `orcarouter`: stable, installable, installed, active, image present;
- `nvidia`: experimental, installable, absent, image absent;
- `mazinb`: experimental, installable, installed, inactive, image present;
- `orcarouter-hybrid`: experimental, installable, installed, inactive, image present;
- `lychee888`: planned, not installable, not applicable locally, non-selectable.

The completed-install chooser rendered the same registry/inventory view, defaulted to the active `orcarouter`, and retained it without creating a profile switch. The acceptance was non-mutating: `install.env` and `runtime-commit.env` digests, managed service/proxy unit digests and status, container ID, `StartedAt`, and lifecycle-idle state were unchanged, and no transaction artifacts were created.

This acceptance validates profile-manager presentation/inventory behavior only. It does not change functional or host-stability qualification for any model profile.

## Canonical installer option registry — 2026-10-07

The accepted implementation code head is `e6fa3c67601ceddfa5714f9d8e854c6a2639a2c6`, validated by CI #1282. `scripts/lib/install-options.sh` is now the canonical user-facing installer option inventory for logical option identity, classification, Wizard applicability, generated usage fragments, and long-flag membership.

The registry classifies each logical option as `setting`, `informational`, `maintenance`, or `control`. Logical groups such as service mode and monitor mode own all of their flag variants together. `install.sh --help` is generated from this registry rather than a second hardcoded usage string, while the parser implementation itself remains unchanged.

`tests/test_installer_option_parity.py` now sources the same registry instead of maintaining a duplicate expected flag set. The test verifies that parser flags exactly match registry flags, that IDs and long flags are unique, that every setting claims Wizard support and has UI evidence, that non-setting commands do not claim Wizard fields, and that canonical flag lookup is deterministic. Ambiguous grouped lookup intentionally fails unless a variant is named.

Guarded DGX acceptance on `e6fa3c67601ceddfa5714f9d8e854c6a2639a2c6` passed after CI #1282. The live registry exposed 27 unique long flags; generated `--help` contained every registry usage fragment; single and grouped flag lookup returned the expected canonical spellings; and the existing completed-install current-profile dry-run still produced the same normalized plan without creating a profile switch.

The acceptance was non-mutating: `install.env`, `runtime-commit.env`, managed service/proxy unit digests and status, container ID, `StartedAt`, and lifecycle-idle state were unchanged, and no lifecycle artifacts were created. This slice changes metadata/help/parity ownership only; it does not change CLI parser semantics or lifecycle/runtime behavior.

## Equivalent CLI preview from normalized plan — 2026-10-07

The accepted implementation code head is `f780f9bc25f9eae5a21e370aa56f7da8eb38ead6`, validated by CI #1287. The final `[6/6]` plan now renders an `Equivalent CLI preview (always dry-run)` directly from the already-finalized `PLAN_*` snapshot rather than rebuilding configuration from Wizard state.

All CLI flag spellings come from `scripts/lib/install-options.sh` through `install_option_flag()`. Values are rendered from the normalized plan and shell-quoted with Bash `%q`. The preview always includes `--yes --dry-run`, even when the source plan represents a live execution request, so copying the displayed command cannot mutate the host by accident. Start policy, service mode, monitor/protection mode and thresholds, API access/ports/address, profile/model root, config policy, language, and refresh-defaults state are all represented from the normalized plan.

This slice also adds `--no-config-override`. The prior CLI could supply a custom config path but could not explicitly represent the Wizard action that clears an existing custom override. The new flag closes that representation gap. For a profile such as `orcarouter` that requires an automatic compatibility override, clearing a custom override yields the automatic compatibility config in the normalized plan rather than disabling the required compatibility behavior.

Regression coverage treats the rendered command as executable evidence rather than presentation text. A fresh Wizard plan and a completed-install profile-switch plan are rendered, replayed through `install.sh`, and required to produce an identical normalized plan. Additional coverage verifies shell-safe replay for paths containing spaces, explicit config-clear semantics, canonical flag lookup, and the safety invariant that a source plan with `PLAN_DRY_RUN=0` still renders a command containing `--dry-run`.

Guarded DGX acceptance on `f780f9bc25f9eae5a21e370aa56f7da8eb38ead6` passed after CI #1287. The current managed `orcarouter` Wizard plan rendered a full CLI preview, replaying that command reproduced the same normalized plan field-for-field, and replay rendered the same CLI again (stable fixed point). Explicit `--no-config-override` selected `automatic vLLM compatibility override` as intended.

The acceptance was non-mutating: `install.env`, `runtime-commit.env`, managed service/proxy unit digests and status, container ID, `StartedAt`, and lifecycle-idle state were unchanged, and no transaction artifacts were created. This feature is a read-only plan renderer; it does not alter lifecycle, transaction, or host-stability semantics.

## Phase sequence

1. **Inventory/parity foundation** — implemented.
2. **Completed-install selector** — implemented and DGX dry-run accepted.
3. **Common normalized plan** — implemented and DGX dry-run accepted.
4. **Completed-install settings management** — implemented and accepted on DGX through preview, no-op live commit, and explicit deferred-runtime rollback; final implementation code head `33a7f16e282672b5aa256cc662c026637e5b7afb`, CI #1264.
5. **Registry/profile-manager metadata** — registry-derived profile UI plus read-only local inventory implemented and DGX accepted on `46f929d74895699aff7b100ada9d844bcd9270ef`, CI #1278; canonical installer option metadata registry implemented and DGX accepted on `e6fa3c67601ceddfa5714f9d8e854c6a2639a2c6`, CI #1282; normalized equivalent CLI preview implemented and DGX accepted on `f780f9bc25f9eae5a21e370aa56f7da8eb38ead6`, CI #1287.
6. **Acceptance/docs** — all CI green, guarded DGX preview for material UI changes, then live transaction validation only when the phase explicitly requires it.

Do not reopen R23–R32 allocator localization, merge the separate M1 mitigation line, or claim H38 as the current transactional managed OrcaRouter profile as part of this work.
