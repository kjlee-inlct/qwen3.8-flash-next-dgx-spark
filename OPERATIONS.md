# Qwen3.8 Flash Next — Operations Guide

This document describes the supported operational lifecycle for this repository. The model/performance background remains in `README.md`; this file is the runbook for install, update, recovery, and uninstall.

## Lifecycle model

A normal installation has two kinds of persistent application state:

```text
~/.local/share/qwen38-spark/
├── releases/<git-commit>/        # immutable code payloads
├── qualified/<git-commit>.env    # qualification markers bound to release manifests
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

1. prepares the model, swap, image, optional managed API-access endpoints, and installation manifest;
2. stages the current Git commit as an immutable release;
3. runs release qualification without mutating the release payload;
4. registers that release as `current` when no baseline exists yet;
5. creates the systemd service with `--runtime-root ~/.local/share/qwen38-spark/current`;
6. starts the runtime unless `--no-start` was requested.

The installer must be run from a Git checkout because the immutable release ID is the Git commit SHA. Re-running `install.sh` does not silently move an existing `current` release to a newer checkout commit. Use the explicit update path below for code updates.

### API access choices

The runtime itself remains published on loopback only at `127.0.0.1:8888`. The installer wizard asks how that API should be made available:

1. **This PC only** — no additional listener; use `http://127.0.0.1:8888/v1`.
2. **Docker apps** — adds a docker0 listener, default port `8000`. Containers can use `http://host.docker.internal:8000/v1`. OpenWebUI is one example of a Docker app that can use this path.
3. **Docker apps + LAN** — keeps the Docker-app listener and also adds a listener on one exact host LAN IPv4 address.

For a new installation, LAN port `8001` is recommended so Docker-app access on `8000` and LAN API access have visibly different purposes. Example:

```text
Docker apps : host.docker.internal:8000 -> 127.0.0.1:8888
LAN clients : 192.168.0.57:8001         -> 127.0.0.1:8888
```

If existing clients already use `http://<DGX-IP>:8000/v1`, choose LAN access and enter `8000` as the LAN port. The managed socket can listen on both the docker0 address and the selected LAN address on port `8000`, so existing client URLs do not need to change.

Non-interactive examples:

```bash
# Local-only API
./install.sh --yes --api-access local

# Docker applications only
./install.sh --yes --api-access docker --api-docker-port 8000

# Recommended new LAN endpoint
./install.sh --yes --api-access lan \
  --api-docker-port 8000 \
  --api-lan-address 192.168.0.57 \
  --api-lan-port 8001

# Preserve an existing DGX-IP:8000/v1 contract
./install.sh --yes --api-access lan \
  --api-docker-port 8000 \
  --api-lan-address 192.168.0.57 \
  --api-lan-port 8000
```

Wildcard LAN listeners (`0.0.0.0`) are not supported. The selected LAN address must be an IPv4 address currently assigned to the host. API access intent is stored in `install.env` using `API_ACCESS_MODE`, `API_DOCKER_PORT`, `API_LAN_ADDRESS`, and `API_LAN_PORT`. Legacy `PROXY_*` fields remain for compatibility with older installations and lifecycle code.

## Health and state inspection

```bash
./scripts/doctor.sh
./scripts/manage-proxy.sh status
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

### Doctor lifecycle observability

`doctor.sh` is read-only and reports more than container/API health. It also verifies the operational lifecycle around the runtime:

- the `current` immutable release pointer resolves inside the managed release store;
- the current release still matches its cryptographic manifest;
- the current release has a strictly parsed qualification marker;
- schema-2 qualification is bound to the SHA-256 digest of that exact `.release-manifest.json`;
- historical schema-1 qualification is reported as a legacy unbound warning and must be re-qualified before a future cutover;
- an optional `previous` release pointer is safe and its manifest remains verifiable;
- no `update-transition.env` is left from an interrupted release cutover;
- no stale or malformed `runtime-stop.env` marker is left behind;
- an installed systemd unit executes from `~/.local/share/qwen38-spark/current` rather than the mutable checkout;
- runtime image, model mount, served model name, loopback publication, and rollback-container state match the installation manifest;
- managed Docker-app and LAN API listeners match the API-access settings recorded in the installation manifest.

A memory monitor that was intentionally disabled at install time is reported as a healthy configured state:

```text
[PASS] runtime memory monitor is disabled by configuration
```

If the monitor is configured as enabled, a missing or stale monitor PID remains a failure. A low memory/swap reserve remains a warning or failure according to the configured thresholds.

Use strict mode when maintenance automation should fail on warnings as well as hard failures:

```bash
./scripts/doctor.sh --strict
```

Examples of signals that require operator attention include an incomplete update/runtime transaction, a tampered current immutable release, an unsafe/dangling release pointer, a legacy or digest-mismatched qualification marker, a service that no longer points at the immutable `current` root, a stale `runtime-stop.env` marker referencing a running or replaced container, or a managed API listener that no longer matches the installation manifest.

## Update a checkout revision

Stage and qualify the target commit first:

```bash
TARGET="$(git rev-parse HEAD)"
bash ./scripts/release-manager.sh stage "${TARGET}"
bash ./scripts/qualify-release.sh "${TARGET}"
bash ./scripts/release-manager.sh verify "${TARGET}"
```

Qualification writes a schema-2 marker containing `RELEASE_MANIFEST_SHA256`, the SHA-256 of the staged release's `.release-manifest.json`. `update-transition.sh prepare` and `commit` both verify the release manifest again and require the marker digest to match. A legacy schema-1 marker is not sufficient for a new cutover; re-run `qualify-release.sh` for that release first.

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

Owned managed API-access endpoints are removed together. API access created outside the installer remains untouched unless it was explicitly adopted into the manifest.

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
./scripts/manage-proxy.sh status
bash ./scripts/update-transition.sh status
bash ./scripts/runtime-transition.sh status
```

After maintenance:

```bash
./scripts/doctor.sh
./scripts/manage-proxy.sh status
bash ./scripts/release-manager.sh status
bash ./scripts/update-transition.sh status
bash ./scripts/runtime-transition.sh status
curl -fsS http://127.0.0.1:8888/health
curl -fsS http://127.0.0.1:8888/v1/models
```

Do not consider an operation complete while either transaction state is non-idle.
