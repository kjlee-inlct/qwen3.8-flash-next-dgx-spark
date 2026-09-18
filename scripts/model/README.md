# Model helpers

This directory contains canonical model-profile, checkpoint-inspection, and configuration-preparation helpers.

## Responsibilities

- Define supported model profiles and their static defaults.
- Inspect checkpoint metadata/layout without loading the full model.
- Validate that every shard referenced by a safetensors index is present and non-empty.
- Prepare validated model-specific configuration overrides.

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
