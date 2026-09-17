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

## Lifecycle operation lock

Mutating release/update operations use one advisory `flock` at `~/.local/state/qwen38-spark/operation.lock`. The lock is held for the full outer operation so release pointer and update-transition mutations cannot overlap with another release/update mutation.

The first locking scope covers:

- `scripts/update-release.sh` for non-dry-run cutover;
- `scripts/lifecycle/update-transition.sh` actions `prepare`, `commit`, `rollback`, and `recover`;
- `scripts/release-manager.sh` actions `stage`, `activate`, `discard`, and `rollback`;
- `scripts/lifecycle/bootstrap-release.sh`.

Nested lifecycle helpers reuse an inherited lock only when the advertised lock file is actually locked and the recorded outer owner PID is an ancestor of the current process. A forged inherited marker therefore does not bypass serialization. Read-only `status`/`verify` paths and update dry-runs remain unlocked.

This first scope intentionally does not yet cover installer, managed-service, or uninstaller mutation entry points; those cross the sudo/service boundary and are connected in a follow-up change after the release/update locking layer is validated independently.

## Installation manifest boundary

`~/.local/state/qwen38-spark/install.env` is written by `install.sh` using Bash `printf %q` encoding and mode 600. All supported consumers now treat it as data and use strict views from `scripts/state_file.py` rather than evaluating it as shell code:

- `service-runner.sh` uses `install-runtime`, validating and emitting only runtime configuration fields;
- `manage-service.sh` uses `install-service`, validating and emitting only service installation/readiness fields;
- `doctor.sh` uses `install-doctor`, validating and emitting only model pinning, runtime drift, monitor, swap, and API-access diagnostic fields;
- `uninstall.sh` uses `install-uninstall`, validating and emitting only resource paths, ownership flags, container name, configuration path, and UI language needed to decide cleanup actions;
- `install.sh` resume/migration uses `install-maintenance`, validating the closed installer field set while preserving schema-2/3/4 compatibility and emitting only keys actually present in the existing manifest.

All install-manifest views:

- accept only the closed installer key set;
- decode ordinary `printf %q` backslash quoting without invoking a shell, including paths containing whitespace;
- accept the historical empty `KEY=` representation used by older manifests;
- reject unknown and duplicate keys;
- reject ANSI-C/control-character quoting;
- validate consumer-required fields before emitting them over the NUL-delimited interface.

`install-doctor` preserves diagnostic compatibility with older schema-3 manifests: when the newer `API_*` fields are absent, it derives the read-only API view from legacy `PROXY_ENABLED` and `PROXY_PORT` fields. It does not require `PHASE=complete`; doctor still reports incomplete installation phase as a diagnostic condition instead of failing parsing solely for that reason.

`install-uninstall` intentionally exposes only values that can affect cleanup scope. Ownership flags are constrained to `0`/`1`, destructive paths must be absolute, and the managed container name is fixed to `qwen38-flash-next`. The uninstaller retains its existing deletion guards in addition to strict parsing. Full purge also removes `runtime-commit.env` and its temporary file together with the other transient lifecycle state.

`install-maintenance` supports schema 2, 3, and 4. It validates every field that is present, requires the fields expected for the declared schema generation, and leaves newer fields absent on older schemas so the installer's existing migration defaults remain authoritative. `--migrate-manifest --dry-run` validates and previews migration without rewriting the manifest.

`manage-service.sh` uses the parser from the invoking source checkout to validate the installer manifest, then uses the parser from the resolved immutable runtime release for runtime-commit attestation validation. This keeps source/maintenance policy separate from the release being attested.

## Operator rule

Do not edit lifecycle state files manually to recover an interrupted operation. Use the supported recovery commands:

```bash
bash ./scripts/update-transition.sh status
bash ./scripts/update-transition.sh recover
bash ./scripts/update-transition.sh rollback
bash ./scripts/runtime-transition.sh status
bash ./scripts/runtime-transition.sh recover
```

Malformed lifecycle or installation state is treated as an error rather than executed or silently ignored.
