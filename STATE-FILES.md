# Lifecycle state-file safety

Qwen38 uses small state files to coordinate release/update/runtime recovery. These files are data, not shell programs.

## Strictly parsed lifecycle files

The following files are parsed by `scripts/state_file.py` and are never evaluated as shell code:

- `~/.local/state/qwen38-spark/update-transition.env`
- `~/.local/state/qwen38-spark/runtime-stop.env`
- `~/.local/state/qwen38-spark/runtime-commit.env`
- `~/.local/share/qwen38-spark/qualified/<release>.env`

The parser uses a schema-specific key whitelist and rejects:

- unknown keys;
- duplicate keys;
- missing required keys;
- malformed values;
- shell quoting/escaping or command syntax such as `$()`, backticks, backslashes, and semicolons.

The only legacy shell-escaped value accepted by lifecycle schemas is `''` for an empty value. Existing transition files written by earlier versions remain compatible because all other lifecycle fields were already restricted to simple release IDs, enum values, container IDs, and UTC timestamps.

Bash consumers receive validated key/value pairs through a NUL-delimited stream and assign only whitelisted variable names with `printf -v`. They do not use `source` or `eval` for these lifecycle files.

## Runtime commit attestation

`runtime-commit.env` is a short-lived proof that the managed service runner finished the runtime transition commit for the currently running replacement container. It is written atomically only after the runtime health/model checks and `runtime-transition.sh commit` succeed.

The attestation binds:

- the physical immutable runtime root after symlink resolution;
- the expected runtime container name;
- the exact Docker container ID;
- the UTC commit timestamp.

`manage-service.sh create --start` removes any stale attestation before starting the service and does not report readiness until a new container is healthy **and** a matching attestation exists. This prevents an API health response from being mistaken for a durably committed runtime transition. The service runner removes the attestation when the container exits.

## Installation manifest boundary

`~/.local/state/qwen38-spark/install.env` is written by `install.sh` using Bash `printf %q` encoding and mode 600. Because it contains a wider compatibility surface than the transient lifecycle files, migration is incremental.

The managed `service-runner.sh` no longer sources this manifest. It invokes the `install-runtime` schema in `scripts/state_file.py`, which:

- accepts only the closed set of installer keys used by schema 3/4 manifests;
- decodes ordinary `printf %q` backslash quoting without invoking a shell, including paths containing whitespace;
- rejects unknown and duplicate keys;
- rejects ANSI-C/control-character quoting;
- validates the runtime-required fields and emits only those fields through the NUL-delimited interface.

This removes executable shell input from the long-lived runtime service boundary while preserving existing installer-manifest compatibility.

Other installer/maintenance consumers (`install.sh`, `manage-service.sh`, `doctor.sh`, and `uninstall.sh`) still source the mode-600 installer-owned manifest for compatibility. Moving those consumers to the same strict parser should be done in follow-up changes so each operational path can be tested independently.

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
