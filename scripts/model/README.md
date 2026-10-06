# Model helpers

This directory contains canonical model-profile, checkpoint-inspection, and configuration-preparation helpers.

## Responsibilities

- Define supported model profiles and their static defaults.
- Inspect checkpoint metadata/layout without loading the full model.
- Validate that every shard referenced by a safetensors index is present and non-empty.
- Prepare validated model-specific configuration overrides.
- Define the safety boundary used by the top-level model inventory/removal operator command.

## Dependencies

- May use small shared utilities from `../lib/` when needed.
- May be called by installation/runtime orchestration.
- Should remain independent of lifecycle transaction state and service management.

## Non-responsibilities

- Do not own release qualification or update transactions.
- Do not start/stop the managed runtime.
- Do not own runtime health monitoring, diagnostics, or benchmarking.

## Canonical files

- `model-profiles.sh`
- `inspect_model.py`
- `checkpoint_integrity.py`
- `migrate_orcarouter.py`
- `relocate_model_root.py`
- `prepare_config.py`

Top-level `scripts/model-profiles.sh`, `scripts/inspect-model.py`, and `scripts/prepare-config.py` are compatibility entry points.

## Installer model status

`model-profiles.sh` is the source of truth for which checkpoint profiles
`install.sh` may select:

| Profile | Status | Installable |
|---|---|---:|
| `orcarouter` | stable/default; 16 GiB managed KV resilience default | yes |
| `nvidia` | experimental | yes |
| `mazinb` | experimental; live managed activation exercised; current 16 GiB managed KV reaches functional readiness but strict RM host-stability remains FAIL | yes |
| `orcarouter-hybrid` | experimental, generated H6; warm/reuse + round-trip functional PASS; R23–R32 allocator/localization closure complete; strict host-stability FAIL remains | yes |
| `lychee888` | planned | no |

A profile is not made installable merely because checkpoint metadata exists.
The registry must also have a defined preparation/runtime path and the managed
lifecycle must accept the profile. However, `installable=yes` is an implementation
state, not proof that the full DGX managed-service qualification has passed.

Current managed KV values are resilience settings, not host-stability certificates.
Any confirmed NVIDIA RM `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid
measurement remains HOST-STABILITY FAIL even when fallback recovers and the runtime
reaches READY.

`orcarouter-hybrid` uses the H3 -> H4-all -> H5 -> H6 preparation chain and has
passed warm/reuse managed operation and the Hybrid -> OrcaRouter -> Hybrid
transactional round trip functionally. The 2026-09-29 CMA-aware repair gate also
passed its then-defined repeated-validation criteria, but later live switch/restart
runs and the R8–R32 investigation reproduced recoverable NVIDIA RM
`NV_ERR_NO_MEMORY`. The current strict classification is therefore
**FUNCTIONAL PASS / HOST-STABILITY FAIL**.

The allocator investigation is no longer open at the R9 boundary. The canonical
closure indexed under `../benchmark/evidence/README.md` now establishes:

- node0 Normal-zone Unmovable order-4 demand, Movable fallback/pageblock stealing,
  failed high-order acquisition, rollback, and immediate order-0 retry;
- a common early roughly 75 GiB physical-page burst separated from later PLE/swap
  pressure;
- direct NVIDIA RM system-memory allocation through `nv_alloc_pages` /
  `nv_alloc_system_pages` as the measured driver-level endpoint;
- no structural-burst mitigation from the H6 W4A16/16 GiB candidate;
- first model construction / Qwen4Exp decoder construction as the dominant userspace
  timing boundary;
- exact ownership of the repeated 400 MiB family by packed `w13_weight` construction;
- a paired 800 MiB family that occurs before ModelOpt-MoE create-weights and spans
  mixed userspace placements, supporting a lower/global backing-growth event rather
  than direct ownership by a single model-prefix marker.

The optional narrow recoverable-RM warning exception remains documented separately
and is not implicitly enabled.

The genuinely clean-host source-download/build/service lifecycle is still pending,
so Hybrid remains experimental. `lychee888` remains blocked.

### OrcaRouter hybrid installer profile

`orcarouter-hybrid` is generated locally rather than downloaded directly.
`install.sh` prepares the pinned OrcaRouter and mazinb source checkpoints,
builds/reuses H3 quant-layout, H4 `orca-all`, H5 neutral input scale, and the
final H6 ModelOpt `W4A16_NVFP4` checkpoint.

The final H6 checkpoint retains the validated parent-link layout. Runtime
validation therefore requires the OrcaRouter base, H3, H4-all, H5, and H6
directories; mazinb is a build-time input and is not a final runtime mount.

When an existing H3 manifest proves the pinned OrcaRouter base revision, the pinned
mazinb revision prefix `f2c21eb`, and the expected H3 tensor/provenance counts, the
installer may reuse that H3 without retaining or re-downloading the mazinb source
checkpoint. This is fail-closed: an absent, stale, mismatched, or incomplete H3 falls
back to the normal source-download path. A genuinely clean host has no H3, so it still
downloads both pinned source checkpoints before building H3 -> H6.

The canonical orchestration/validation helpers are:

```text
scripts/model/prepare-orcarouter-hybrid.sh
scripts/model/validate-orcarouter-hybrid.py
```

### mazinb installer promotion status

The installer exposes mazinb as an experimental/installable profile. It has moved
beyond preflight-only status, but it still does **not** have a clean strict
HOST-STABILITY qualification.

Verified DGX Spark evidence includes:

- `./install.sh --list-models` exposes `mazinb` as
  `experimental / installable=1`;
- the pinned source ref `f2c21eb` resolved to full SHA
  `f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f`;
- the complete checkpoint was staged under the managed model root and all required
  files were verified before the project model manifest was marked `complete`;
- the read-only Hybrid -> mazinb preflight and installer wizard dry-run passed;
- the original managed 24 GiB activation failed the strict RM host-stability gate;
- a controlled temporary 16 GiB comparison could pass under one allocator state, so
  reduced KV remained useful resilience evidence but not a deterministic fix;
- the managed profile was promoted to the 16 GiB resilience value and subsequently
  reached functional readiness, but a valid managed run still contained confirmed RM
  `NV_ERR_NO_MEMORY`, leaving the result **FUNCTIONAL PASS / HOST-STABILITY FAIL**.

The current profile description therefore means exactly this: mazinb is an implemented
and selectable experimental profile with a 16 GiB managed KV resilience value. It is
not yet qualified as host-stable, and READY/runtime-commit success does not override
strict RM kernel evidence.

Clean-host managed activation, post-commit doctor/restart, uninstall preservation,
managed API behavior, correctness/performance, and repeated host-stability qualification
remain required before promotion beyond experimental status.

## Installer ownership vs model inventory

The installer now keeps cumulative destructive authority in
`~/.local/state/qwen38-spark/asset-ownership.json`. This is intentionally
separate from model discovery. A valid `.qwen38-model-manifest.json` or
`.qwen38-hybrid-manifest.json` proves that a directory is structurally managed;
it does **not** prove that the installer created it.

During install/profile switching, existing checkpoints are observed as unowned
and reused without adoption. Newly absent checkpoints are claimed before
creation and finalized with the managed-manifest SHA-256 after completion.
Hybrid H3/H4/H5/H6 dependencies are recorded by exact path so full uninstall can
remove H6 → H5 → H4 → H3 → base and refuse deletion when a retained unowned
dependent still needs an owned parent.

`scripts/manage-models.sh` remains the operator inventory/retirement interface
for managed checkpoints. The ownership registry serves a narrower purpose:
deciding what `uninstall.sh --purge-model`, `--purge-image`, and
`--purge-all` are authorized to destroy.

## Operator model inventory and cleanup

The stable top-level `scripts/manage-models.sh` command inventories locally managed checkpoints by their `.qwen38-model-manifest.json` files. It reports the active model separately and refuses to delete it. Active-model removal remains an uninstall lifecycle operation via `./uninstall.sh --purge-model`.

Examples:

```bash
./scripts/manage-models.sh list
./scripts/manage-models.sh remove "$HOME/models/old-qwen38" --dry-run
./scripts/manage-models.sh remove "$HOME/models/old-qwen38"
./scripts/manage-models.sh migrate-orcarouter --dry-run
./scripts/manage-models.sh migrate-orcarouter --yes
./scripts/manage-models.sh relocate-root --dry-run
./scripts/manage-models.sh relocate-root --yes
```

Deletion is intentionally limited to managed model manifests under `$HOME/models`,
the repository-local `./models` store, or the historical `./model` compatibility
path. New clean installs default to `./models`; an existing complete `$HOME/models`
store is reused automatically, and `QWEN38_MODEL_ROOT` / `--model-root` can select
another root.

The OrcaRouter migration action is for installations that predate the current
configurable model-root layout and still have a real repository-local `./model`
directory. It accepts only a complete checkpoint for
`orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` at revision
`c1209bda15a6bbc4c68b585e93d40c0d85f50306`, verifies every shard referenced by
the safetensors index, and uses a same-filesystem rename. A matching interrupted
canonical download is preserved as `.partial-backup*`; complete conflicts, unexpected
symlinks, running-container mounts, and cross-filesystem migrations are rejected.
After migration, `./model` is retained as a compatibility symlink and rerunning the
command is idempotent.

### Managed model-root relocation

`relocate-root` is the supported way to consolidate existing managed assets from
`$HOME/models` into the repository-local `./models` root introduced by the installer.
It performs a same-filesystem atomic rename and is intentionally fail-closed:

- every top-level source entry must be a managed model/hybrid directory with
  `status=complete`;
- ordinary downloaded model checkpoints must resolve every safetensors shard to a
  non-empty local file;
- linked hybrid H3/H4/H5/H6 stages are validated with the canonical
  `validate-orcarouter-hybrid.py --runtime-only` provenance/parent/config chain rather
  than treating container mount targets such as `/base-model` as host-local shard paths;
- running Docker mounts and an active `qwen38-flash-next.service` block the move;
- a held lifecycle operation lock, cross-filesystem destination, existing destination,
  or unexpected `./model` symlink blocks the move;
- unrelated/unmanaged top-level entries under `$HOME/models` block whole-root relocation.

After a successful move, the physical data lives under `./models`.
`$HOME/models` becomes a compatibility symlink to that directory, so retained lifecycle
manifests or older scripts that still contain `$HOME/models/...` continue to resolve.
The historical repository `./model` symlink is refreshed to the relocated OrcaRouter
checkpoint. The command is idempotent and should always be previewed with `--dry-run`.
