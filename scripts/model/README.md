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

`model-profiles.sh` is also the source of truth for which checkpoint profiles
`install.sh` may select:

| Profile | Status | Installable |
|---|---|---:|
| `orcarouter` | stable/default, qualified | yes |
| `nvidia` | experimental | yes |
| `mazinb` | experimental, managed E2E pending | yes |
| `orcarouter-hybrid` | experimental, generated H6, managed E2E pending | yes |
| `lychee888` | planned | no |

A profile is not made installable merely because checkpoint metadata exists.
The registry must also have a defined preparation/runtime path and the managed
lifecycle must accept the profile. However, `installable=yes` is an implementation
state, not proof that the full DGX managed-service qualification has passed.
`orcarouter-hybrid` now uses the H3 -> H4-all -> H5 -> H6 preparation chain;
`lychee888` remains blocked.


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

The installer promotion was merged after two concrete checks on DGX Spark:

- `./install.sh --list-models` exposed `mazinb` as
  `experimental / installable=1`;
- `./install.sh --model mazinb --lang en --yes --no-start --dry-run`
  produced the expected model, revision `f2c21eb`, model directory, and local
  `vllm-orcarouter-v029:v1` image plan without mutating the host.

The full managed lifecycle validation has **not yet been run** for mazinb.
Actual checkpoint download, local image build, systemd readiness, doctor, restart,
uninstall preservation, API behavior, determinism/correctness, and performance are
still pending. Keeping mazinb selectable means only that the installer path exists;
it is not a qualification result.

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
- any safetensors index present must resolve to non-empty local shards;
- running Docker mounts and an active `qwen38-flash-next.service` block the move;
- a held lifecycle operation lock, cross-filesystem destination, existing destination,
  or unexpected `./model` symlink blocks the move;
- unrelated/unmanaged top-level entries under `$HOME/models` block whole-root relocation.

After a successful move, the physical data lives under `./models`.
`$HOME/models` becomes a compatibility symlink to that directory, so retained lifecycle
manifests or older scripts that still contain `$HOME/models/...` continue to resolve.
The historical repository `./model` symlink is refreshed to the relocated OrcaRouter
checkpoint. The command is idempotent and should always be previewed with `--dry-run`.
