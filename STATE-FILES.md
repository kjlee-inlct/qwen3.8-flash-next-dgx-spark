# Lifecycle state-file safety

Qwen38 uses small state files to coordinate release/update/runtime/profile-switch recovery. These files are data, not shell programs.

## Strictly parsed lifecycle files

The following files are parsed by the strict state parser (`scripts/lib/state_file.py`, with `scripts/state_file.py` retained as a compatibility entry point) and are never evaluated as shell code:

- `~/.local/state/qwen38-spark/update-transition.env`
- `~/.local/state/qwen38-spark/runtime-transition.env`
- `~/.local/state/qwen38-spark/runtime-stop.env`
- `~/.local/state/qwen38-spark/runtime-commit.env`
- `~/.local/state/qwen38-spark/runtime-adopt.env`
- `~/.local/state/qwen38-spark/profile-switch-transition.env`
- `~/.local/state/qwen38-spark/release-profile-refresh-transition.env`
- `~/.local/share/qwen38-spark/qualified/<release>.env`

The parser uses a schema-specific key whitelist and rejects unknown, duplicate, missing, or malformed keys and values. Bash consumers receive validated key/value pairs through a NUL-delimited stream and assign only whitelisted variable names with `printf -v`.

`runtime-transition.env` is parsed with the dedicated `runtime-transition` schema before rollback/recovery decisions are made. It binds the transaction phase, canonical/rollback container names, whether a previous runtime existed, and the update timestamp. The runtime transition helper never sources this file; malformed state fails closed.

`profile-switch-transition.env` is parsed with the dedicated `profile-switch` schema. It binds the source/target profiles, phase, backup/candidate manifest paths, their recorded digests, and update timestamp. The profile-switch helper never sources this file; malformed or ambiguous state fails closed.

`release-profile-refresh-transition.env` is parsed with the dedicated `release-profile-refresh` schema. It binds the exact target/previous immutable release IDs, qualified release-manifest digest, backup/candidate install-manifest paths and digests, same-profile marker, exact predecessor Docker container ID, old/target image identity, served-model identity, transaction phase, and update timestamp. It is the sole recovery owner for the atomic cross-release OrcaRouter H38 refresh.

## Runtime commit attestation and one-shot adoption

`runtime-commit.env` proves that the managed service runner finished the runtime transition commit for the running replacement container. It binds the physical immutable runtime root, container name, exact Docker container ID, and UTC commit timestamp. `manage-service.sh create --start` requires a matching attestation in addition to health before it reports readiness.

`runtime-adopt.env` is a one-shot recovery marker used only when the atomic cross-release refresh has restored the exact predecessor container and must reattach systemd without replacing or cold-starting it. The strict `runtime-adopt` schema binds the restored immutable runtime root, canonical container name, exact predecessor container ID, expected image, served-model identity, and UTC creation time. The adoption supervisor re-proves container ID, image, model mount, health, served-model identity, and `OOMKilled=false` before writing a fresh runtime commit attestation. A safety-stopped predecessor is left stopped rather than started merely to recover service state.

## Lifecycle operation lock

Mutating maintenance operations use one advisory `flock` at `~/.local/state/qwen38-spark/operation.lock`. The lock is held for the full outer operation so installer state, release pointers, update-transition state, profile-switch state, managed-service mutation, and uninstall cleanup cannot overlap with another covered mutation.

The locking scope covers:

- non-dry-run `install.sh`, including manifest migration and the complete interactive/download/swap/API/release/service/profile-switch flow;
- `scripts/update-release.sh` for non-dry-run cutover;
- `scripts/lifecycle/update-transition.sh` actions `prepare`, `commit`, `rollback`, and `recover`;
- `scripts/lifecycle/profile-switch-transition.sh` actions `prepare`, `activate`, `runtime-committed`, `commit`, `rollback`, `recover`, and service-startup recovery when it is not deferred by an existing outer lock;
- `scripts/lifecycle/release-profile-refresh-transition.sh` atomic apply/recover operations, including target release qualification, H38 asset preparation, release+manifest activation, managed runtime validation, and symmetric rollback;
- `scripts/release-manager.sh` actions `stage`, `activate`, `discard`, and `rollback`;
- `scripts/lifecycle/bootstrap-release.sh`;
- `scripts/manage-service.sh` actions `create` and `remove`;
- pending one-shot runtime adoption is itself a lifecycle guard: unrelated mutations are blocked until `runtime-adopt.env` is consumed or explicitly recovered;
- non-dry-run `uninstall.sh`.

Nested lifecycle helpers reuse an inherited lock only when the advertised lock file is actually locked and the recorded outer owner PID is an ancestor of the current process. The user-owned lock context is passed explicitly across the `sudo` boundary for managed-service calls; root validates the service-user UID/GID before reusing the same lock. A forged inherited marker therefore does not bypass serialization.

When root must create the lifecycle state directory or lock file, it creates them with the resolved service user's UID/GID rather than leaving root-owned state behind. The lock file is intentionally persistent metadata; a full uninstall may leave only `operation.lock` so future reinstall/maintenance commands continue to share the same synchronization point safely.

Read-only `status`/`verify` paths and all supported dry-runs remain unlocked. Non-dry-run `install.sh` acquires the lock immediately after CLI parsing and before reading an existing manifest so another update/uninstall/service mutation cannot change lifecycle state between resume inspection and the eventual write. Child release helpers inherit that lock, while managed-service calls receive the authenticated lock context explicitly across `sudo`.

## Installation manifest boundary

`~/.local/state/qwen38-spark/install.env` is written by `install.sh` using Bash `printf %q` encoding and mode 600. All supported consumers now treat it as data and use strict views from `scripts/state_file.py` rather than evaluating it as shell code:

- `service-runner.sh` uses `install-runtime`, validating and emitting only runtime configuration fields;
- `manage-service.sh` uses `install-service`, validating and emitting only service installation/readiness fields;
- `doctor.sh` uses `install-doctor`, validating and emitting only model pinning, runtime drift, monitor, swap, and API-access diagnostic fields;
- `uninstall.sh` uses `install-uninstall`, validating and emitting only resource paths, ownership flags, container name, configuration path, and UI language needed to decide cleanup actions;
- `install.sh` resume/migration uses `install-maintenance`, validating the closed installer field set while preserving schema-2/3/4 compatibility and emitting only keys actually present in the existing manifest;
- `profile-switch-transition.sh` parses the live, backup, and candidate install manifests with strict maintenance/runtime views before it activates, commits, restores, or recovers a switch.
- `release-profile-refresh-transition.sh` strictly parses the current/backup/candidate install manifests and couples them to the recorded immutable release IDs and manifest digests before activation, commit, or recovery.

During a managed profile switch, `install.env.profile-switch-candidate` and `install.env.profile-switch-backup` are install-manifest data files, not shell state. The candidate is prepared and strictly validated before activation; the backup is validated before rollback. Their paths and digests are bound by `profile-switch-transition.env`, and orphan candidate/backup files without matching transition state are treated as an ambiguous recovery condition rather than silently adopted.

All install-manifest views:

- accept only the closed installer key set;
- decode ordinary `printf %q` backslash quoting without invoking a shell, including paths containing whitespace;
- accept the historical empty `KEY=` representation used by older manifests;
- reject unknown and duplicate keys;
- reject ANSI-C/control-character quoting;
- validate consumer-required fields before emitting them over the NUL-delimited interface.

`install-doctor` preserves diagnostic compatibility with older schema-3 manifests: when the newer `API_*` fields are absent, it derives the read-only API view from legacy `PROXY_ENABLED` and `PROXY_PORT` fields. It does not require `PHASE=complete`; doctor still reports incomplete installation phase as a diagnostic condition instead of failing parsing solely for that reason.

`install-uninstall` intentionally exposes only values that can affect cleanup scope. Ownership flags are constrained to `0`/`1`, destructive paths must be absolute, and the managed container name is fixed to `qwen38-flash-next`. The uninstaller retains its existing deletion guards in addition to strict parsing. Full purge also removes `runtime-commit.env`, `runtime-adopt.env`, runtime/update/profile-switch/release-profile-refresh transaction state, settings transaction markers/candidates/backups, and their temporary/digest files together with the other transient lifecycle state. A real uninstall refuses to begin while any active or orphaned recovery artifact is present, so `--purge-all` never erases unresolved recovery evidence.

`install-maintenance` supports schema 2, 3, and 4. It validates every field that is present, requires the fields expected for the declared schema generation, and leaves newer fields absent on older schemas so the installer's existing migration defaults remain authoritative. `--migrate-manifest --dry-run` validates and previews migration without rewriting the manifest.

`manage-service.sh` uses the strict parser from the invoking maintenance release for install-manifest, runtime-commit, and runtime-adoption validation. The attestation/adoption records themselves bind the exact physical immutable runtime root and container ID, so recovery does not depend on an older restored release understanding newer one-shot recovery state.

## Operator rule

Do not edit lifecycle state files manually to recover an interrupted operation. Use the supported recovery commands:

```bash
bash ./scripts/update-transition.sh status
bash ./scripts/update-transition.sh recover
bash ./scripts/update-transition.sh rollback
bash ./scripts/runtime-transition.sh status
bash ./scripts/runtime-transition.sh recover
bash ./scripts/profile-switch-transition.sh status
bash ./scripts/profile-switch-transition.sh recover
bash ./scripts/profile-switch-transition.sh rollback
bash ./scripts/release-profile-refresh-transition.sh status
bash ./scripts/release-profile-refresh-transition.sh recover
```

For an interrupted profile switch, inspect/recover the profile-switch transaction before manually changing containers or install manifests. Recovery either proves and commits the target, proves and restores the previous profile, or leaves the persisted state intact and fails closed when neither side can be proven.

Malformed lifecycle or installation state is treated as an error rather than executed or silently ignored.
