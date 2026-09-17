# Lifecycle state-file safety

Qwen38 uses small state files to coordinate release/update/runtime recovery. These files are data, not shell programs.

## Strictly parsed lifecycle files

The following files are parsed by `scripts/state_file.py` and are never evaluated as shell code:

- `~/.local/state/qwen38-spark/update-transition.env`
- `~/.local/state/qwen38-spark/runtime-stop.env`
- `~/.local/state/qwen38-spark/runtime-commit.env`
- `~/.local/share/qwen38-spark/qualified/<release>.env`

The parser uses a schema-specific key whitelist and rejects unknown, duplicate, missing, or malformed keys and values. Bash consumers receive validated key/value pairs through a NUL-delimited stream and assign only whitelisted variable names with `printf -v`.

## Runtime commit attestation

`runtime-commit.env` proves that the managed service runner finished the runtime transition commit for the running replacement container. It binds the physical immutable runtime root, container name, exact Docker container ID, and UTC commit timestamp. `manage-service.sh create --start` requires a matching attestation in addition to health before it reports readiness.

## Installation manifest boundary

`~/.local/state/qwen38-spark/install.env` is written by `install.sh` using Bash `printf %q` encoding and mode 600. Migration away from shell evaluation is incremental because this manifest has a broader compatibility surface than transient lifecycle state.

Two service-critical consumers now use strict views from `scripts/state_file.py`:

- `service-runner.sh` uses `install-runtime`, validating and emitting only runtime configuration fields;
- `manage-service.sh` uses `install-service`, validating and emitting only `SCHEMA_VERSION`, `PHASE`, `INSTALL_ROOT`, `SERVED_NAME`, and `CONTAINER_NAME`.

Both install-manifest views:

- accept only the closed schema 3/4 installer key set;
- decode ordinary `printf %q` backslash quoting without invoking a shell, including paths containing whitespace;
- reject unknown and duplicate keys;
- reject ANSI-C/control-character quoting;
- validate consumer-required fields before emitting them over the NUL-delimited interface.

`manage-service.sh` uses the parser from the invoking source checkout to validate the installer manifest, then uses the parser from the resolved immutable runtime release for runtime-commit attestation validation. This keeps source/maintenance policy separate from the release being attested.

The remaining installer/maintenance consumers (`install.sh`, `doctor.sh`, and `uninstall.sh`) still source the mode-600 installer-owned manifest for compatibility. They should be migrated independently so each operational path can be tested against existing schema-3 and schema-4 manifests.

## Operator rule

Do not edit lifecycle state files manually to recover an interrupted operation. Use the supported recovery commands:

```bash
bash ./scripts/update-transition.sh status
bash ./scripts/update-transition.sh recover
bash ./scripts/update-transition.sh rollback
bash ./scripts/runtime-transition.sh status
bash ./scripts/runtime-transition.sh recover
```

Malformed lifecycle state is treated as an error rather than executed or silently ignored.
