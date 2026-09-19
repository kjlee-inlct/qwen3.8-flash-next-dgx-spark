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

## Operator model inventory and cleanup

The stable top-level `scripts/manage-models.sh` command inventories locally managed checkpoints by their `.qwen38-model-manifest.json` files. It reports the active model separately and refuses to delete it. Active-model removal remains an uninstall lifecycle operation via `./uninstall.sh --purge-model`.

Examples:

```bash
./scripts/manage-models.sh list
./scripts/manage-models.sh remove "$HOME/models/old-qwen38" --dry-run
./scripts/manage-models.sh remove "$HOME/models/old-qwen38"
```

Deletion is intentionally limited to managed model manifests under `$HOME/models` or this repository's `./model` directory.
