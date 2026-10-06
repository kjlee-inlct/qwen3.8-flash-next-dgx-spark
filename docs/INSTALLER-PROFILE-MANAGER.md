# Installer / Profile Manager Plan

This document is the canonical implementation plan and option-inventory snapshot for the installer/profile-manager work. It records current product behavior, known parity debt, safety boundaries, and the order in which the remaining work should be completed without introducing a second lifecycle manager.

The baseline inspected at the start of this work was `main` at `aab3cd48ba0af20446d18fe85ac7d4cf0dfbc38f`. That SHA is an observation, not a permanent pin; each phase starts from the then-current `main`.

## Product contract

The managed product has one lifecycle. `install.sh`, the installation manifest, cumulative asset ownership, profile-switch/runtime/update transaction helpers, immutable releases, and the managed systemd service remain authoritative. A profile switch is **not** uninstall + reinstall.

The target UX contract is:

- every Wizard setting has a CLI representation;
- every supported user-facing CLI setting is selectable in the Wizard;
- Wizard and CLI normalize into the same internal values and final plan;
- informational/control-only CLI commands may remain CLI-only when they are not settings;
- developer/internal environment variables are outside the user-facing parity contract;
- fresh install, interrupted resume, completed-install management, and profile switch are distinct applicability contexts and must not be conflated;
- preview paths are non-mutating, while live changes must preserve transaction/recovery and ownership semantics.

`tests/test_installer_option_parity.py` freezes the CLI inventory and bounds known Wizard parity debt so new flags cannot silently escape the inventory.

## Existing lifecycle reused by this work

The following existing contracts are reused rather than reimplemented:

- `scripts/model/model-profiles.sh` — model/profile registry and pinned model metadata;
- `scripts/manage-models.sh` — local model/image inventory, retirement, migration, and root relocation operations;
- `scripts/lifecycle/profile-switch-transition.sh` — persisted managed profile replacement;
- `scripts/runtime/runtime-transition.sh` — candidate/rollback runtime replacement;
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
| installed | local checkpoint/generated asset exists |
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

“Both” means a Wizard field exists somewhere. A completed-install settings preview now covers the persisted runtime/API/service surface, but live apply remains intentionally closed until cleanup semantics are transactional.

| Setting / command | CLI | Wizard | Current applicability / classification |
| --- | --- | --- | --- |
| language | `--lang` | yes | fresh selection; saved language reused on existing install |
| profile | `--model` | yes | fresh and completed-install profile selection |
| model root | `--model-root` | yes | fresh install; profile switch retains existing root by design |
| config override | `--config-override` | yes | fresh live path; completed-install settings preview |
| list profiles | `--list-models` | no field | informational CLI command; profile-manager inventory view is P1 |
| list backends | `--list-backends` | no field | informational CLI command |
| monitor enable/disable | `--monitor` / `--no-monitor` | yes | fresh live path; completed-install settings preview |
| protection | `--protect` | yes | fresh live path; completed-install settings preview |
| MemAvailable threshold | `--monitor-min-available-gib` | yes | fresh live path; completed-install settings preview |
| MemFree threshold | `--monitor-min-free-gib` | yes | fresh live path; completed-install settings preview |
| MemAvailable gate | `--monitor-free-gate-gib` | yes | fresh live path; completed-install settings preview |
| SwapFree threshold | `--monitor-min-swap-free-gib` | yes | fresh live path; completed-install settings preview |
| consecutive samples | `--monitor-consecutive` | yes | fresh live path; completed-install settings preview |
| monitor heartbeat | `--monitor-heartbeat` | yes | fresh live path; completed-install settings preview |
| API access mode | `--api-access` | yes | fresh live path; completed-install settings preview |
| Docker API port | `--api-docker-port` | yes | fresh live path; completed-install settings preview |
| LAN address | `--api-lan-address` | yes | fresh live path; completed-install settings preview |
| LAN port | `--api-lan-port` | yes | fresh live path; completed-install settings preview |
| service enabled/disabled | `--service` / `--no-service` | yes | fresh live path; completed-install settings preview |
| start policy | default / `--no-start` | no | remaining user-facing Wizard debt |
| refresh profile defaults | `--refresh-profile-defaults` | yes | completed-install management action; existing core reused |
| dry-run | `--dry-run` | no normal field | remaining user-facing Wizard debt; settings editor currently forces it for safety |
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

A complete managed install enters an installed-setup management menu before the existing profile selector. The menu currently offers profile selection/switch, runtime/API/service settings preview, current-profile default refresh, or cancel.

Profile selection still shows the four installable profiles, marks the active profile, defaults to the current profile, and enters the existing transactional profile-switch core only when the target changes. `lychee888` remains non-selectable.

The settings editor stages config override, monitor/protection thresholds, API access/ports, and service enablement in memory. Staged values are applied immediately before the shared `[6/6]` normalized-plan boundary, after manifest parsing and CLI override resolution. This keeps the existing parser/validation/plan path authoritative rather than duplicating it in the UI.

The settings action is deliberately **preview-only** in the current slice. It forces the existing dry-run exit and therefore does not write the manifest or change proxy/service/runtime resources.

## Priority classification after completed-settings preview slice

### P0 — product contract / operator correctness

- **Implemented:** completed-install Wizard profile selection/switch reuses the transactional CLI core.
- **Implemented:** CLI and Wizard converge on one normalized final-plan snapshot before review/execution.
- **Implemented:** completed-install management menu and runtime/API/service settings editor feed the normalized plan.
- **Implemented:** current-profile default refresh is reachable from the Wizard through the existing `REFRESH_PROFILE_DEFAULTS` path.
- **Pending:** live settings apply with transactional/recoverable cleanup of owned proxy and managed service resources.
- **Pending:** normal Wizard controls for dry-run and start/restart policy.

### P1 — architecture / drift prevention

- centralize user-facing option metadata;
- derive Wizard profile display/status metadata from the profile registry;
- add a profile-manager view combining registry availability with local asset inventory;
- resolve remaining contextual parity for language/model-root/execution controls;
- show the equivalent CLI invocation in the final plan once normalized configuration is fully authoritative.

### P2 — operator polish

- consolidate list/current/status presentation without replacing existing entry points;
- improve localized profile labels/help text after metadata ownership is centralized;
- keep planned backend work (`sglang`) independent from checkpoint-profile selection.

## Safety rules

Profile selection does not duplicate switch logic. Existing strict manifest parsing, transaction-idle checks, shadow candidate manifest preparation, cumulative asset ownership, managed systemd ownership, runtime health/model-identity/attestation, and commit/rollback/recovery remain authoritative.

Dry-run must remain non-mutating: no transaction state, manifest change, download, swap, release, service, proxy, container, or asset-ownership mutation.

### Settings apply safety gap

Live settings apply is intentionally closed in the current slice because the existing resume path is not symmetric for two destructive changes:

- changing managed API access from Docker/LAN to `local` does not currently remove the owned proxy resources;
- changing from managed systemd service to no-service does not currently remove the owned unit.

Allowing live settings apply before those cleanup paths are transactional/recoverable could leave `install.env` claiming one configuration while old host resources remain active. The settings UI therefore forces dry-run until this gap is closed.

## Common normalized plan — 2026-10-06

`scripts/lib/install-plan.sh` is the installer-only normalized plan boundary. It runs immediately before `[6/6]`, reuses existing monitor/API validators, canonicalizes relevant paths, snapshots profile/model/image/config/monitor/API/service/switch/start/dry-run values into versioned `PLAN_*` fields, and reapplies that snapshot before the existing renderer/lifecycle code continues.

The normalized-plan DGX dry-run was accepted on implementation head `d528f4f2f4b4d270e81edec3cf47d2218f74b886` after CI #1218 passed all 493 tests. `install.env`, `runtime-commit.env`, service/container identity, `StartedAt`, and lifecycle transaction state remained unchanged.

## Completed-install settings management — preview slice — 2026-10-06

`scripts/lib/install-completed-manager.sh` adds the installed-setup management UI without adding a new execution engine. It is sourced only for `install.sh`; uninstall and other Wizard consumers do not inherit installer-specific state.

The management UI stages settings in memory, lets the existing manifest/CLI resolution complete, and reapplies staged values immediately before `install_plan_finalize`. Current-profile default refresh reuses the existing `REFRESH_PROFILE_DEFAULTS` implementation. Settings preview explicitly forces dry-run and has no `write_state`, proxy/service mutation, or lifecycle-transition call.

Guarded DGX acceptance on implementation head `603aa0391d436eb2a6bd459d924ddcff2d0f5a5c` passed after CI #1228 passed 499 tests. The settings action retained `orcarouter`, staged monitor values `7/3/11/9 GiB`, 6 consecutive samples and a 30-second heartbeat, normalized the current LAN configuration to `local only: 127.0.0.1:8888`, and staged service disable as `Docker container via immutable current release`. The command line intentionally omitted `--dry-run`; the settings manager itself forced the existing `DRY-RUN complete` path.

Post-run checks proved the preview was non-mutating: `install.env` and `runtime-commit.env` digests were unchanged, the managed service remained active, container ID and `StartedAt` were unchanged, no runtime/update/profile-switch transaction file was created, and the live proxy listeners remained present at the Docker bridge and LAN addresses. The first acceptance wrapper had one harness-only false negative because it grepped `This PC only` while the canonical renderer emits `local only`; the corrected invariant check passed without rerunning the installer.

This slice therefore accepts the settings editor only as a normalized non-mutating preview. The next P0 slice must close the proxy/service cleanup gap and provide a recoverable live settings transaction before the settings editor may apply changes to a real managed host.

## Phase sequence

1. **Inventory/parity foundation** — implemented.
2. **Completed-install selector** — implemented and DGX dry-run accepted.
3. **Common normalized plan** — implemented and DGX dry-run accepted.
4. **Completed-install settings management** — preview/action UI implemented and DGX accepted; live settings transaction, dry-run control, and start/restart policy remain.
5. **Registry/profile-manager metadata** — derive profile UI from registry and combine it with `manage-models.sh` inventory; centralize option metadata.
6. **Acceptance/docs** — all CI green, guarded DGX preview for material UI changes, then live transaction validation only when a phase explicitly requires it.

Do not reopen R23–R32 allocator localization, merge the separate M1 mitigation line, or claim H38 as the current transactional managed OrcaRouter profile as part of this work.
