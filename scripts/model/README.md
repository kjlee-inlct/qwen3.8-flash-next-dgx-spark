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
- `prepare_config.py`

Top-level `scripts/model-profiles.sh`, `scripts/inspect-model.py`, and `scripts/prepare-config.py` are compatibility entry points.


## Installer model status

`model-profiles.sh` is also the source of truth for which checkpoint profiles
`install.sh` may select:

| Profile | Status | Installable |
|---|---|---:|
| `orcarouter` | stable/default, confirmed | yes |
| `nvidia` | experimental, confirmed | yes |
| `mazinb` | experimental, confirmed | yes |
| `orcarouter-hybrid` | experimental, generated H6 | yes |
| `lychee888` | planned | no |

A profile is not made installable merely because checkpoint metadata exists.
The registry must also have a defined preparation/runtime path and the managed
lifecycle must accept the profile. `orcarouter-hybrid` now uses the proven
H3 -> H4-all -> H5 -> H6 preparation chain; `lychee888` remains blocked.


### OrcaRouter hybrid installer profile

`orcarouter-hybrid` is generated locally rather than downloaded directly.
`install.sh` prepares the pinned OrcaRouter and mazinb source checkpoints,
builds/reuses H3 quant-layout, H4 `orca-all`, H5 neutral input scale, and the
final H6 ModelOpt `W4A16_NVFP4` checkpoint.

The final H6 checkpoint retains the validated parent-link layout. Runtime
validation therefore requires the OrcaRouter base, H3, H4-all, H5, and H6
directories; mazinb is a build-time input and is not a final runtime mount.

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

The full managed lifecycle validation (actual image build/start, systemd
readiness, doctor, restart, and uninstall preservation) is intentionally
deferred. Treat that as a follow-up qualification task, not as a prerequisite
for keeping mazinb selectable in the registry.

## Operator model inventory and cleanup

The stable top-level `scripts/manage-models.sh` command inventories locally managed checkpoints by their `.qwen38-model-manifest.json` files. It reports the active model separately and refuses to delete it. Active-model removal remains an uninstall lifecycle operation via `./uninstall.sh --purge-model`.

Examples:

```bash
./scripts/manage-models.sh list
./scripts/manage-models.sh remove "$HOME/models/old-qwen38" --dry-run
./scripts/manage-models.sh remove "$HOME/models/old-qwen38"
```

Deletion is intentionally limited to managed model manifests under `$HOME/models` or this repository's `./model` directory.
