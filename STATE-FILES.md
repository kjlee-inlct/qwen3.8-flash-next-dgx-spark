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

Four operational consumers now use strict views from `scripts/state_file.py`:

- `service-runner.sh` uses `install-runtime`, validating and emitting only runtime configuration fields;
- `manage-service.sh` uses `install-service`, validating and emitting only service installation/readiness fields;
- `doctor.sh` uses `install-doctor`, validating and emitting only model pinning, runtime drift, monitor, swap, and API-access diagnostic fields;
- `uninstall.sh` uses `install-uninstall`, validating and emitting only resource paths, ownership flags, container name, configuration path, and UI language needed to decide cleanup actions.

All install-manifest views:

- accept only the closed schema 3/4 installer key set;
- decode ordinary `printf %q` backslash quoting without invoking a shell, including paths containing whitespace;
- reject unknown and duplicate keys;
- reject ANSI-C/control-character quoting;
- validate consumer-required fields before emitting them over the NUL-delimited interface.

`install-doctor` preserves diagnostic compatibility with older schema-3 manifests: when the newer `API_*` fields are absent, it derives the read-only API view from legacy `PROXY_ENABLED` and `PROXY_PORT` fields. It does not require `PHASE=complete`; doctor still reports incomplete installation phase as a diagnostic condition instead of failing parsing solely for that reason.

`install-uninstall` intentionally exposes only values that can affect cleanup scope. Ownership flags are constrained to `0`/`1`, destructive paths must be absolute, and the managed container name is fixed to `qwen38-flash-next`. The uninstaller retains its existing deletion guards in addition to strict parsing. Full purge also removes `runtime-commit.env` and its temporary file together with the other transient lifecycle state.

`manage-service.sh` uses the parser from the invoking source checkout to validate the installer manifest, then uses the parser from the resolved immutable runtime release for runtime-commit attestation validation. This keeps source/maintenance policy separate from the release being attested.

The remaining installer consumer (`install.sh` resume/migration) still sources the mode-600 installer-owned manifest for compatibility. It should be migrated separately because it both reads and rewrites older schemas and therefore has the broadest compatibility surface.

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
