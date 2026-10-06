# Installer / Profile Manager Plan

This document is the canonical implementation plan and option-inventory snapshot for the
installer/profile-manager work. It records current product behavior, known parity debt, safety
boundaries, and the order in which the remaining work should be completed without introducing a
second lifecycle manager.

The baseline inspected at the start of this work was `main` at
`aab3cd48ba0af20446d18fe85ac7d4cf0dfbc38f`. That SHA is an observation, not a permanent pin;
each phase starts from the then-current `main`.

## Product contract

The managed product has one lifecycle. `install.sh`, the installation manifest, cumulative asset
ownership, profile-switch/runtime/update transaction helpers, immutable releases, and the managed
systemd service remain authoritative. A profile switch is **not** uninstall + reinstall.

The target UX contract is:

- every Wizard setting has a CLI representation;
- every supported user-facing CLI setting is selectable in the Wizard;
- Wizard and CLI normalize into the same internal values and final plan;
- informational/control-only CLI commands may remain CLI-only when they are not settings;
- developer/internal environment variables are outside the user-facing parity contract;
- fresh install, interrupted resume, completed-install management, and profile switch are
  distinct applicability contexts and must not be conflated;
- preview paths are non-mutating, while live changes must preserve transaction/recovery and
  ownership semantics.

`tests/test_installer_option_parity.py` freezes the CLI inventory and bounds known Wizard parity
debt so new flags cannot silently escape the inventory.

## Existing lifecycle reused by this work

The following existing contracts are reused rather than reimplemented:

- `scripts/model/model-profiles.sh` — model/profile registry and pinned model metadata;
- `scripts/manage-models.sh` — local model/image inventory, retirement, migration, and root
  relocation operations;
- `scripts/lifecycle/profile-switch-transition.sh` — persisted managed profile replacement;
- `scripts/runtime/runtime-transition.sh` — candidate/rollback runtime replacement;
- update transition helpers — immutable release cutover;
- `scripts/lib/state_file.py` — strict state-file parsing;
- `scripts/lib/asset_ownership.py` — cumulative asset ownership/fingerprints;
- `qwen38-flash-next.service` / managed service helpers — runtime ownership and health gate.

No parallel profile database, supervisor, state parser, or model-purge switch mechanism should be
introduced.

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

A valid measured `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` event remains a strict
HOST-STABILITY FAIL even if fallback later reaches READY. Memory-monitor firing is a safety
heuristic, not equivalent host-stability evidence.

## CLI ↔ Wizard inventory

“Both” means a Wizard field exists somewhere. A completed-install settings preview now covers the
persisted runtime/API/service surface, but live apply remains intentionally closed until cleanup
semantics are transactional.

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

The parser supports the full monitor-threshold CLI surface. `usage()` must list those flags; the
parity regression test prevents help/inventory drift from returning.

## Wizard inventory

### Fresh install

The flow remains:

1. language;
2. model/profile;
3. model storage;
4. runtime/config/monitor settings;
5. API/service;
6. normalized final plan and confirmation.

### Interrupted install

An incomplete manifest continues the existing resume path. It must **not** expose completed-install
management or a profile switch while an install is mid-phase. Resume/recovery semantics stay
fail-closed.

### Completed managed install

A complete managed install enters an installed-setup management menu before the existing profile
selector. The menu currently offers:

1. select/switch model profile;
2. preview runtime/API/service settings;
3. refresh current profile defaults;
4. cancel.

Profile selection still shows the four installable profiles, marks the active profile, defaults to
the current profile, and enters the existing transactional profile-switch core only when the target
changes. `lychee888` remains non-selectable.

The settings editor stages config override, monitor/protection thresholds, API access/ports, and
service enablement in memory. Staged values are applied immediately before the shared `[6/6]`
normalized-plan boundary, after manifest parsing and CLI override resolution. This means the
existing parser/validation/plan path remains authoritative rather than being duplicated in the UI.

The settings action is deliberately **preview-only** in the current slice. It forces the existing
dry-run exit and therefore does not write the manifest or change proxy/service/runtime resources.

## Priority classification after completed-settings preview slice

### P0 — product contract / operator correctness

- **Implemented:** completed-install Wizard profile selection/switch reuses the transactional CLI
  core.
- **Implemented:** CLI and Wizard converge on one normalized final-plan snapshot before
  review/execution.
- **Implemented:** completed-install management menu and runtime/API/service settings editor feed
  the normalized plan.
- **Implemented:** current-profile default refresh is reachable from the Wizard through the existing
  `REFRESH_PROFILE_DEFAULTS` path.
- **Pending:** live settings apply with transactional/recoverable cleanup of owned proxy and managed
  service resources.
- **Pending:** normal Wizard controls for dry-run and start/restart policy.

### P1 — architecture / drift prevention

- Move user-facing option metadata (id, flag, type, default, choices, labels, applicability,
  validation, destructive classification) to one source of truth instead of keeping parser/help/UI
  metadata independently.
- Move Wizard profile display/status metadata out of hard-coded menu text and derive it from the
  profile registry. Extend the registry with qualification/source/known-limit fields only where
  there is a clear consumer.
- Add a profile-manager view that combines registry availability with local asset inventory from
  `manage-models.sh`: installable, installed/partial/generated, active/inactive.
- Resolve remaining contextual parity for language/model-root/execution controls without weakening
  lifecycle guards.
- Show the equivalent CLI invocation in the final plan once normalized configuration is fully
  authoritative.

### P2 — operator polish

- Consolidate list/current/status presentation without replacing existing entry points.
- Improve localized profile labels/help text after metadata ownership is centralized.
- Keep planned backend work (`sglang`) independent from checkpoint-profile selection.

## Safety rules

Profile selection does not duplicate switch logic. The existing code remains responsible for:

- strict manifest parsing;
- transaction-idle checks;
- shadow candidate manifest preparation;
- retained model-root selection;
- cumulative asset ownership preservation;
- managed systemd ownership/startup requirements;
- runtime health/model-identity/attestation checks;
- profile-switch commit/rollback/recovery.

Dry-run must remain non-mutating: no transaction state, manifest change, download, swap, release,
service, proxy, container, or asset-ownership mutation.

### Settings apply safety gap

Live settings apply is intentionally closed in the current slice because the existing resume path
is not symmetric for two destructive changes:

- changing managed API access from Docker/LAN to `local` does not currently remove the owned proxy
  resources;
- changing from managed systemd service to no-service does not currently remove the owned unit.

Allowing live settings apply before those cleanup paths are transactional/recoverable could leave
`install.env` claiming one configuration while old host resources remain active. The settings UI
therefore forces dry-run until this gap is closed.

## Regression coverage

The profile-manager work keeps or adds coverage for:

- fresh selection of every installable profile;
- planned/not-installable rejection;
- completed-install management menu and cancel path;
- same-profile default without a switch;
- completed-install profile-switch dry-run;
- completed-install settings plan preview and manifest preservation;
- completed-install profile-default refresh preview;
- interrupted-install resume without completed-management prompt;
- semantic CLI ↔ Wizard plan parity for fresh install and profile switch;
- same model-root reuse during switch;
- dry-run manifest/state preservation;
- profile-switch/runtime/update transaction contracts;
- option inventory/help/Wizard parity debt;
- ownership preservation and generated Hybrid reuse;
- documentation current-state guards.

## DGX acceptance — completed-install selector — 2026-10-06

Guarded acceptance was performed on the single DGX Spark before merging the completed-install
selector slice. The installed manifest was initially at `PHASE=service_ready`, so the installer
correctly remained on the interrupted-install resume path and did not expose profile selection.
Before changing that phase, the existing runtime was proven against strict state parsers, managed
systemd ownership, immutable `current` release, runtime-commit attestation, live container
ID/image, `/model` mount, served-model command line, and `/v1/models` identity.

Only after those checks passed was `PHASE=service_ready` atomically recovered to `PHASE=complete`.
That recovery was runtime-neutral: service remained active, container ID and `StartedAt` were
unchanged, and `runtime-commit.env` was unchanged.

The completed-install Wizard dry-run then selected NVIDIA and produced `profile: nvidia` and
`orcarouter -> nvidia`, while retaining the existing model root, monitor/protection, API/LAN, and
managed-service settings. `install.env`, service/container identity, and `StartedAt` remained
unchanged and no runtime/update/profile-switch transaction was created.

This accepted the non-mutating selector boundary only; it was not a live NVIDIA replacement or a
host-stability qualification result.

## Common normalized plan — 2026-10-06

`scripts/lib/install-plan.sh` is the installer-only normalized plan boundary. It runs immediately
before `[6/6]`, reuses existing monitor/API validators, canonicalizes relevant paths, snapshots
profile/model/image/config/monitor/API/service/switch/start/dry-run values into versioned `PLAN_*`
fields, and reapplies that snapshot before the existing renderer/lifecycle code continues.

Regression coverage compares equivalent CLI and Wizard plans for fresh install and completed
profile switch, plus direct helper normalization/reapplication behavior.

### DGX acceptance — normalized plan

Implementation head `d528f4f2f4b4d270e81edec3cf47d2218f74b886` passed guarded acceptance
after CI #1218 had passed all 493 tests. The Wizard selected NVIDIA and passed through `[6/6]`
with `profile: nvidia` and `orcarouter -> nvidia` while preserving existing operational settings.

The dry-run was non-mutating: `install.env` SHA-256 and `runtime-commit.env` SHA-256 were unchanged,
service remained active, live container ID and `StartedAt` remained unchanged, and no
runtime/update/profile-switch transaction file was created.

## Completed-install settings management — preview slice — 2026-10-06

`scripts/lib/install-completed-manager.sh` adds the installed-setup management UI without adding a
new execution engine. It is sourced only for `install.sh`; uninstall and other Wizard consumers do
not inherit installer-specific state.

The management UI stages settings in memory, lets the existing manifest/CLI resolution complete,
and reapplies staged values immediately before `install_plan_finalize`. Current-profile default
refresh reuses the existing `REFRESH_PROFILE_DEFAULTS` implementation. Settings preview explicitly
forces dry-run and has no `write_state`, proxy/service mutation, or lifecycle-transition call.

Guarded DGX acceptance on implementation head `603aa0391d436eb2a6bd459d924ddcff2d0f5a5c`
passed after CI #1228 passed 499 tests. The settings action retained `orcarouter`, staged monitor
values `7/3/11/9 GiB`, 6 consecutive samples and a 30-second heartbeat, normalized the current
LAN configuration to `local only: 127.0.0.1:8888`, and staged service disable as `Docker container
via immutable current release`. The command line intentionally omitted `--dry-run`; the settings
manager itself forced the existing `DRY-RUN complete` path.

Post-run checks proved the preview was non-mutating: `install.env` and `runtime-commit.env` digests
were unchanged, the managed service remained active, container ID and `StartedAt` were unchanged,
no runtime/update/profile-switch transaction file was created, and the live proxy listeners
remained present at the Docker bridge and LAN addresses. The first acceptance wrapper had one
harness-only false negative because it grepped `This PC only` while the canonical renderer emits
`local only`; the corrected invariant check passed without rerunning the installer.

This slice therefore accepts the settings editor only as a normalized non-mutating preview. The
next P0 slice must close the proxy/service cleanup gap and provide a recoverable live settings
transaction before the settings editor may apply changes to a real managed host.

## Phase sequence

1. **Inventory/parity foundation** — implemented.
2. **Completed-install selector** — implemented and DGX dry-run accepted.
3. **Common normalized plan** — implemented; CI and guarded DGX dry-run accepted.
4. **Completed-install settings management** — preview/action UI implemented and DGX accepted;
   live settings transaction, dry-run control, and start/restart policy remain.
5. **Registry/profile-manager metadata** — derive profile UI from registry and combine it with
   `manage-models.sh` inventory; centralize option metadata.
6. **Acceptance/docs** — all CI green, guarded DGX preview for material UI changes, then live
   transaction validation only when a phase explicitly requires it.

Do not reopen R23–R32 allocator localization, merge the separate M1 mitigation line, or claim H38
as the current transactional managed OrcaRouter profile as part of this work.
