# Installer / Profile Manager Plan

This document is the canonical implementation plan and option-inventory snapshot for the
installer/profile-manager work. It describes current product behavior, known parity debt,
and the order in which the debt should be removed without introducing a second lifecycle
manager.

The baseline inspected at the start of this work was `main` at
`aab3cd48ba0af20446d18fe85ac7d4cf0dfbc38f`. That SHA is an observation, not a permanent
pin; future work must always start from the then-current `main`.

## Product contract

The managed product has one lifecycle. `install.sh`, the installation manifest, cumulative
asset ownership, the profile-switch/runtime/update transaction helpers, and the systemd
service remain authoritative. A profile switch is **not** uninstall + reinstall.

The target UX contract is:

- every Wizard setting has a CLI representation;
- every supported user-facing CLI setting is selectable in the Wizard;
- Wizard and CLI normalize into the same internal values and final plan;
- information/control-only CLI commands may remain CLI-only when they are not settings;
- developer/internal environment variables are outside the user-facing parity contract;
- fresh install, interrupted resume, completed-install management, and profile switch are
  distinct applicability contexts and must not be conflated.

`tests/test_installer_option_parity.py` freezes the current CLI inventory and bounds known
Wizard parity debt so newly added flags cannot silently escape the inventory.

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

No parallel profile database, supervisor, state parser, or model-purge switch mechanism
should be introduced.

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

The matrix below reflects `install.sh` after the first existing-install selector slice.
“Both” means a Wizard field exists somewhere; “context gap” means CLI and Wizard are not yet
available in the same lifecycle contexts.

| Setting / command | CLI | Wizard | Current applicability / classification |
| --- | --- | --- | --- |
| language | `--lang` | yes | Both; fresh selection, saved language on existing install; context gap remains |
| profile | `--model` | yes | Both; fresh and completed-install profile selection |
| model root | `--model-root` | yes | Both on fresh install; switch Wizard intentionally retains existing root; context gap |
| config override | `--config-override` | yes | Both; existing-install settings editor still missing |
| list profiles | `--list-models` | no field | informational CLI command; profile-manager status UX is P1 |
| list backends | `--list-backends` | no field | informational CLI command |
| monitor enable | `--monitor` | yes | Both on fresh; existing-install settings editor missing |
| monitor disable | `--no-monitor` | yes | Both on fresh; existing-install settings editor missing |
| protection | `--protect` | yes | Both on fresh; existing-install settings editor missing |
| MemAvailable threshold | `--monitor-min-available-gib` | yes | Both on fresh; existing-install settings editor missing |
| MemFree threshold | `--monitor-min-free-gib` | yes | Both on fresh; existing-install settings editor missing |
| MemAvailable gate | `--monitor-free-gate-gib` | yes | Both on fresh; existing-install settings editor missing |
| SwapFree threshold | `--monitor-min-swap-free-gib` | yes | Both on fresh; existing-install settings editor missing |
| consecutive samples | `--monitor-consecutive` | yes | Both on fresh; existing-install settings editor missing |
| monitor heartbeat | `--monitor-heartbeat` | yes | Both on fresh; existing-install settings editor missing |
| API access mode | `--api-access` | yes | Both on fresh; existing-install settings editor missing |
| Docker API port | `--api-docker-port` | yes | Both on fresh; existing-install settings editor missing |
| LAN address | `--api-lan-address` | yes | Both on fresh; existing-install settings editor missing |
| LAN port | `--api-lan-port` | yes | Both on fresh; existing-install settings editor missing |
| service enabled | `--service` | yes | Both on fresh; existing-install settings editor missing |
| service disabled | `--no-service` | yes | Both on fresh; existing-install settings editor missing |
| start policy | default / `--no-start` | no | user-facing Wizard debt |
| refresh profile defaults | `--refresh-profile-defaults` | no | user-facing Wizard debt |
| dry-run | `--dry-run` | no | user-facing Wizard debt |
| non-interactive confirmation | `--yes` | n/a | execution control; no Wizard field required |
| manifest migration | `--migrate-manifest` | n/a | maintenance command; no normal Wizard field required |
| help | `--help` / `-h` | n/a | informational control |

The parser also supports the full monitor-threshold CLI surface. `usage()` must list those
flags; the parity regression test enforces that help/inventory drift does not return.

## Wizard inventory

### Fresh install

Current flow remains:

1. language;
2. model/profile;
3. model storage;
4. runtime/config/monitor settings;
5. API/service;
6. final plan and confirmation.

### Interrupted install

An incomplete manifest continues the existing resume path. It must **not** expose a profile
switch while an install is mid-phase. Resume/recovery semantics stay fail-closed.

### Completed managed install

The first implemented profile-manager slice changes the old “resume only” behavior:

1. show the current profile;
2. show the four installable profiles with the current one marked `Active`;
3. default to the current profile;
4. allow selecting another installable profile or cancelling;
5. when another profile is selected, populate the same `MODEL_CLI` target used by
   `./install.sh --model <profile>`;
6. reuse the existing transactional switch path and existing model root;
7. preserve existing runtime/API/service settings in this slice instead of silently
   rewriting them;
8. use the normal shared final plan and dry-run boundary.

The planned `lychee888` profile is not selectable.

## Priority classification after first slice

### P0 — product contract / operator correctness

- **Implemented in this slice:** completed-install Wizard can select/switch profile by
  entering the existing CLI transactional switch core.
- **Implemented in this slice:** Wizard config-override choice now has a direct
  `--config-override PATH` CLI representation.
- Add a completed-install “settings only” action that edits runtime/monitor/API/service
  values without implying a profile switch.
- Add Wizard controls for `dry-run`, start/restart policy, and profile-default refresh.
- Make Wizard and CLI produce one normalized plan object/representation and semantic parity
  tests for fresh/resume/switch.

### P1 — architecture / drift prevention

- Move user-facing option metadata (id, flag, type, default, choices, labels, applicability,
  validation, destructive classification) to one source of truth rather than keeping
  parser/help/Wizard metadata independently.
- Move Wizard profile display/status metadata out of hard-coded menu text and derive it from
  the profile registry. Extend the registry with qualification/source/known-limit fields
  only where those fields have a clear consumer.
- Add a profile-manager view that combines registry availability with local asset inventory
  from `manage-models.sh`: installable, installed/partial/generated, active/inactive.
- Resolve contextual parity for language/model-root/config/runtime/API/service settings on
  completed installations without weakening lifecycle guards.
- Show the equivalent CLI invocation in the final plan once normalized configuration is
  authoritative.

### P2 — operator polish

- Consolidate list/current/status presentation without replacing existing entry points.
- Improve localized profile labels/help text after metadata ownership is centralized.
- Keep planned backend work (`sglang`) independent from checkpoint-profile selection.

## First-slice safety rules

The completed-install selector deliberately does not duplicate switch logic. Selection only
sets the target profile; the existing code still performs:

- strict manifest parsing;
- transaction-idle checks;
- shadow candidate manifest preparation;
- retained model-root selection;
- cumulative asset ownership preservation;
- managed systemd ownership/startup requirements;
- runtime health/model-identity/attestation checks;
- profile-switch commit/rollback/recovery.

Interactive profile switching also skips the fresh model-storage/runtime/API/service pages in
this slice. That makes an interactive switch semantically match the existing CLI switch:
shared operational settings and the existing model root are retained unless explicit CLI
overrides are supplied.

Dry-run must remain non-mutating: no transaction state, manifest change, download, swap,
release, service, proxy, container, or asset-ownership mutation.

## Regression coverage

The profile-manager work should keep or add coverage for:

- fresh selection of every installable profile;
- planned/not-installable rejection;
- completed-install Wizard same-profile default;
- completed-install Wizard profile-switch dry-run;
- interrupted-install resume without switch prompt;
- CLI direct profile switch;
- same model-root reuse during switch;
- dry-run manifest/state preservation;
- profile-switch transaction and runtime transaction contracts;
- option inventory/help/Wizard parity debt;
- ownership preservation and generated Hybrid reuse;
- documentation current-state guards.

## DGX acceptance — 2026-10-06

Guarded acceptance was performed on the single DGX Spark before merging this slice.
The installed manifest was initially at `PHASE=service_ready`, so the installer correctly
remained on the interrupted-install resume path and did not expose profile selection.
Before changing that phase, the existing runtime was proven against the strict state parsers,
managed systemd ownership, immutable `current` release, runtime-commit attestation, live
container ID/image, `/model` mount, served-model command line, and `/v1/models` identity.

Only after those checks passed was `PHASE=service_ready` atomically recovered to
`PHASE=complete`. That recovery was runtime-neutral: the service remained active, the
container ID and `StartedAt` were unchanged, and `runtime-commit.env` was unchanged.

The completed-install Wizard dry-run then passed with these observations:

- current profile displayed as `orcarouter` and marked `Active`;
- all four installable profiles were offered, while the current profile remained the default;
- selecting NVIDIA produced `profile: nvidia` and `orcarouter -> nvidia` in the shared plan;
- existing model root, monitor/protection, API/LAN, and managed-service settings were retained;
- no fresh model-storage/runtime/API/service Wizard pages were re-entered;
- `install.env` remained unchanged after the dry-run;
- service state, container identity, and `StartedAt` remained unchanged;
- no runtime/update/profile-switch transaction file was created.

This validates the non-mutating completed-install selector and shared profile-switch planning
boundary. It is not a live NVIDIA replacement or a new host-stability qualification result.

## Phase sequence

1. **Inventory/parity foundation** — freeze actual flags and known debt in tests and this
   document.
2. **Completed-install selector** — expose profile selection while delegating to existing
   transactional switch logic.
3. **Common normalized plan** — converge Wizard and CLI configuration construction.
4. **Completed-install settings management** — runtime/API/service/default-refresh/start and
   dry-run actions with the same plan core.
5. **Registry/profile-manager metadata** — derive profile UI from registry and combine it
   with `manage-models.sh` inventory.
6. **Acceptance/docs** — all CI green, guarded DGX dry-run first, then live managed switch
   validation, recovery/restoration verification, and documentation synchronization.

Do not reopen R23–R32 allocator localization, merge the separate M1 mitigation line, or claim
H38 as the current transactional managed OrcaRouter profile as part of this work.
