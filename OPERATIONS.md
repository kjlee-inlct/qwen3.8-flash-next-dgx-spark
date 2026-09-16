# Qwen3.8 Flash Next — Operations Guide

This document describes the supported operational lifecycle for this repository. The model/performance background remains in `README.md`; this file is the runbook for install, update, recovery, and uninstall.

## Lifecycle model

A normal installation has two kinds of persistent application state:

```text
~/.local/share/qwen38-spark/
├── releases/<git-commit>/        # immutable code payloads
├── qualified/<git-commit>.env    # qualification markers
├── current -> releases/<commit>  # code used for the managed runtime
└── previous -> releases/<commit> # rollback code, when available

~/.local/state/qwen38-spark/
├── install.env                   # installation/resource ownership manifest
├── config.vllm.json              # generated compatibility config, when owned
├── runtime-transition.env        # exists only during runtime replacement
├── update-transition.env         # exists only during release cutover
├── runtime-stop.env              # memory-protection stop marker, transient
└── monitor.*                     # optional memory monitor state/log
```

The systemd service uses the stable `~/.local/share/qwen38-spark/current` symlink. It does not execute directly from the mutable Git checkout after installation.

## Fresh install

Run the normal installer:

```bash
./install.sh
```

or a non-interactive example:

```bash
./install.sh --model orcarouter --lang en --yes
```

Before installing, a dry-run is recommended:

```bash
./install.sh --model orcarouter --lang en --yes --no-start --dry-run
```

A successful fresh install automatically:

1. prepares the model, swap, image, optional proxy, and installation manifest;
2. stages the current Git commit as an immutable release;
3. runs release qualification without mutating the release payload;
4. registers that release as `current` when no baseline exists yet;
5. creates the systemd service with `--runtime-root ~/.local/share/qwen38-spark/current`;
6. starts the runtime unless `--no-start` was requested.

The installer must be run from a Git checkout because the immutable release ID is the Git commit SHA. Re-running `install.sh` does not silently move an existing `current` release to a newer checkout commit. Use the explicit update path below for code updates.

## Health and state inspection

```bash
./scripts/doctor.sh
bash ./scripts/release-manager.sh status
bash ./scripts/update-transition.sh status
bash ./scripts/runtime-transition.sh status
systemctl is-active qwen38-flash-next.service
docker ps -a --filter name=qwen38-flash-next
```

Healthy steady state has both transaction states idle:

```text
UPDATE_STATE=idle
TRANSACTION_STATE=idle
```

## Update a checkout revision

Stage and qualify the target commit first:

```bash
TARGET="$(git rev-parse HEAD)"
bash ./scripts/release-manager.sh stage "${TARGET}"
bash ./scripts/qualify-release.sh "${TARGET}"
bash ./scripts/release-manager.sh verify "${TARGET}"
```

Preview the cutover without changing the runtime:

```bash
bash ./scripts/update-release.sh "${TARGET}" --dry-run
```

Perform the cutover:

```bash
bash ./scripts/update-release.sh "${TARGET}"
```

The update path changes the immutable `current` pointer, restarts the managed service from that stable pointer, validates a replacement container, and commits only after runtime validation. On a cutover failure it attempts to restore the previous release pointer and service.

## Recovery after an interrupted operation

Inspect state before doing manual Docker or symlink changes:

```bash
bash ./scripts/update-transition.sh status
bash ./scripts/runtime-transition.sh status
```

Recover an interrupted runtime replacement:

```bash
bash ./scripts/runtime-transition.sh recover
```

If an update transaction is active and the cutover must be abandoned, restore its prior release pointers:

```bash
bash ./scripts/update-transition.sh rollback
```

Do not manually delete `qwen38-flash-next.rollback` while a runtime transition state file exists. The runtime transaction uses that container to distinguish recoverable crash boundaries.

## Direct `serve.sh`

`scripts/serve.sh` is fail-closed when the canonical `qwen38-flash-next` container already exists. It will not delete a running or stopped managed runtime to make room for a direct invocation.

For the installed service, prefer:

```bash
sudo systemctl restart qwen38-flash-next.service
journalctl -fu qwen38-flash-next.service
```

## Uninstall

A normal uninstall removes the runtime/service resources recorded by the installation manifest but intentionally keeps the immutable release history and the manifest so a later reinstall or full purge still knows what was owned:

```bash
./uninstall.sh
```

Uninstall refuses to start if either `update-transition.env` or `runtime-transition.env` exists. Recover or roll back that transaction first rather than deleting transaction state manually.

Preview a full purge:

```bash
./uninstall.sh --purge-all --yes --dry-run
```

A full purge removes owned model/swap/image resources according to the installation manifest and also removes the application release/state lifecycle data:

```bash
./uninstall.sh --purge-all --yes
```

`--purge-all` deletes the application-owned `~/.local/share/qwen38-spark` tree, including `releases`, `qualified`, `current`, and `previous`, after the managed runtime has been stopped and removed. It also clears transient runtime/update/monitor state and removes `install.env`.

The uninstaller continues to refuse deletion of model, swap, or image resources that were not recorded as installer-owned.

## Recommended maintenance sequence

Before maintenance:

```bash
./scripts/doctor.sh
bash ./scripts/update-transition.sh status
bash ./scripts/runtime-transition.sh status
```

After maintenance:

```bash
./scripts/doctor.sh
bash ./scripts/release-manager.sh status
bash ./scripts/update-transition.sh status
bash ./scripts/runtime-transition.sh status
curl -fsS http://127.0.0.1:8888/health
curl -fsS http://127.0.0.1:8888/v1/models
```

Do not consider an operation complete while either transaction state is non-idle.
