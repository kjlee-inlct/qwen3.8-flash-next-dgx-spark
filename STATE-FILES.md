# Lifecycle state-file safety

Qwen38 uses small state files to coordinate release/update/runtime recovery. These files are data, not shell programs.

## Strictly parsed lifecycle files

The following files are parsed by `scripts/state_file.py` and are never evaluated as shell code:

- `~/.local/state/qwen38-spark/update-transition.env`
- `~/.local/state/qwen38-spark/runtime-stop.env`
- `~/.local/share/qwen38-spark/qualified/<release>.env`

The parser uses a schema-specific key whitelist and rejects:

- unknown keys;
- duplicate keys;
- missing required keys;
- malformed values;
- shell quoting/escaping or command syntax such as `$()`, backticks, backslashes, and semicolons.

The only legacy shell-escaped value accepted is `''` for an empty value. Existing transition files written by earlier versions remain compatible because all other lifecycle fields were already restricted to simple release IDs, enum values, container IDs, and UTC timestamps.

Bash consumers receive validated key/value pairs through a NUL-delimited stream and assign only whitelisted variable names with `printf -v`. They do not use `source` or `eval` for these lifecycle files.

## Installation manifest boundary

`~/.local/state/qwen38-spark/install.env` is still written and read as an installer-owned, mode-600 shell-escaped manifest. It contains a wider compatibility surface, including filesystem paths and installer configuration, and is intentionally not migrated in the same change as transient lifecycle state.

Migration of `install.env` to a strict data parser should be handled as a separate compatibility-focused change with explicit tests for paths containing whitespace and existing schema-3 manifests.

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
