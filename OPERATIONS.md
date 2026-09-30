# Qwen3.8 Flash Next — Operations Guide


## H38 runtime vs managed-service status

The qualified OrcaRouter H38 decoder-only runtime is currently exposed through
`scripts/runtime/orcarouter-v029.sh --profile hybrid-h38-deterministic`.

It is **not yet the transactional installer/systemd-managed runtime**. The
managed path still derives its image and served-model state from
`install.sh`, `scripts/model/model-profiles.sh`, the installation manifest,
`scripts/serve.sh`, and `scripts/runtime/service-runner.sh`.

Do not migrate those managed defaults implicitly. H38 managed-service promotion
requires its own lifecycle qualification: image preparation from a clean host,
manifest migration, service replacement, rollback, doctor/attestation,
production-alias determinism, and performance regression checks.

Current H38 evidence and runtime roles are summarized in
`docs/H38-DETERMINISM.md`.


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
├── install.env                   # active profile/runtime manifest (legacy active ownership flags)
├── asset-ownership.json          # cumulative per-model/per-image ownership registry
├── config.vllm.json              # generated compatibility config, when owned
├── runtime-transition.env        # exists only during runtime replacement
├── update-transition.env         # exists only during release cutover
├── profile-switch-transition.env # exists only during a managed profile switch
├── runtime-commit.env            # committed runtime attestation, transient
├── runtime-stop.env              # memory-protection stop marker, transient
├── install.env.profile-switch-candidate # target manifest while preparing a switch
├── install.env.profile-switch-backup    # previous manifest after target activation
└── monitor.*                     # optional memory monitor state/log
```

The systemd service uses the stable `~/.local/share/qwen38-spark/current` symlink. It does not execute directly from the mutable Git checkout after installation.

## Installer model profiles

The installer currently exposes four selectable profiles:

```text
orcarouter         stable / default
nvidia             experimental / optional
mazinb             experimental / optional
orcarouter-hybrid  experimental / generated H6 hybrid
```

The remaining roadmap profile is visible through `./install.sh --list-models`
but is not selectable yet:

```text
lychee888          planned
```

Use `./install.sh --list-models` as the canonical operator view rather than
assuming every profile tracked by the repository is installable.

## Fresh install

The clean-install baseline is a standard DGX Spark software image with the NVIDIA
driver/container stack, Docker, Git, Python 3, curl and sudo available, plus a clone of
this repository. Model checkpoints, project Docker images, the dedicated PLE swap,
application release state and the systemd unit may all be absent.

Run the normal installer:

```bash
./install.sh
```

or a non-interactive example:

```bash
./install.sh --model orcarouter --lang en --yes
# or:
./install.sh --model nvidia --lang en --yes
./install.sh --model mazinb --lang en --yes
./install.sh --model orcarouter-hybrid --lang en --yes
```

Before installing, a dry-run is recommended:

```bash
./install.sh --model orcarouter --lang en --yes --no-start --dry-run
./install.sh --model orcarouter-hybrid --lang en --yes --no-start --dry-run
```

For `orcarouter-hybrid`, no prebuilt local checkpoint is required. On an empty model
store the installer downloads the pinned OrcaRouter and mazinb source checkpoints,
builds H3 quant-layout, H4 `orca-all`, H5 neutral-input-scale, and H6
`W4A16_NVFP4`, then installs H6 as the active model. Existing validated generated
stages are reused; a non-empty stale or incomplete stage is never deleted automatically.

OrcaRouter and `orcarouter-hybrid` require gated Hugging Face access. The `hf` CLI is
not an installer prerequisite. The wizard uses an existing token environment/cache when
available, otherwise it asks for a read token without storing it. The model terms still
must be accepted in the browser before installation.

When changing from an already installed managed profile, select the target
profile directly. The installer keeps downloaded/generated model directories and
shared runtime resources, prepares the target from the same model root, then
uses the managed runtime transaction to replace the running container:

```bash
# Example: Hybrid H6 -> OrcaRouter without deleting either checkpoint
./install.sh --model orcarouter --lang en --yes

# Switch back; validated H3/H4/H5/H6 stages are reused
./install.sh --model orcarouter-hybrid --lang en --yes
```

A profile switch requires the installer-owned systemd service and runtime startup;
`--no-start` and `--no-service` are intentionally rejected for a live switch.
The update/runtime/profile-switch transaction states must be idle before a new
switch begins. Profile switching has its own persisted lifecycle:

```text
preparing -> activated -> runtime_committed -> committing -> idle
```

During model/download/image preparation, the existing `install.env` remains
unchanged and target progress is written to
`install.env.profile-switch-candidate`. The `preparing` state is persisted
before that candidate is created. When the candidate reaches `service_ready`,
the previous manifest is copied to `install.env.profile-switch-backup`, the
target manifest becomes canonical, and the transaction moves to `activated`.
The existing runtime container is preserved by the nested runtime transaction
until health, exact served-model ID, and runtime commit attestation all pass.
Only then does the profile transaction record `runtime_committed`, finalize
the target manifest as `complete`, remove the temporary manifests, and clear
the transaction state last.

Installer startup runs profile-switch recovery before resuming installation.
Managed service startup also checks for an interrupted profile switch before
parsing the canonical manifest. During an intentional switch the installer still
holds the lifecycle operation lock, so service-side recovery is deliberately
deferred rather than racing the installer.

Recovery is fail-closed. A valid target runtime attestation plus matching target
manifest/container proves that the target can be committed. If the target is not
committed and the previous runtime can be proven against the backup manifest,
recovery restores the previous profile. If neither side can be proven—for
example, power loss after the runtime transaction committed but before its
attestation was written—automatic recovery does not guess. The transaction is
left for doctor/operator inspection and destructive maintenance is blocked.

A normal uninstall is still available after all lifecycle transactions are idle
when an operator explicitly wants to stop/remove the managed runtime while
retaining models.

Do **not** use `--purge-model`, `--purge-swap`, or `--purge-all` for a
normal profile switch. Those options are removal operations, not switching
operations.

The final H6 directory intentionally contains parent links. Keep the OrcaRouter
base, H3, H4-all, and H5 directories while this profile is installed. The
managed service mounts those parents read-only at the same paths used during H6
validation. Uninstalling the active H6 model does not automatically purge those
shared/generated parents.

A successful fresh install automatically:

1. prepares the model, swap, image, optional managed API-access endpoints, and installation manifest;
2. stages the current Git commit as an immutable release;
3. runs release qualification without mutating the release payload;
4. registers that release as `current` when no baseline exists yet;
5. on a fresh install after a normal uninstall, stages/qualifies/activates the current checkout when a retained older `current` release exists;
6. creates the systemd service with `--runtime-root ~/.local/share/qwen38-spark/current`;
7. starts the runtime unless `--no-start` was requested.

The installer must be run from a Git checkout because the immutable release ID is the Git
commit SHA. An in-progress/resumed installation fails closed if its immutable runtime release
does not match the checkout revision. An already installed/running profile is not silently
updated by re-running the installer; use the explicit update path below for normal code
updates.

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
bash ./scripts/profile-switch-transition.sh status
systemctl is-active qwen38-flash-next.service
docker ps -a --filter name=qwen38-flash-next
```

Healthy steady state has all transaction states idle:

```text
UPDATE_STATE=idle
TRANSACTION_STATE=idle
PROFILE_SWITCH_STATE=idle
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
- no incomplete or malformed `profile-switch-transition.env` is left from an interrupted profile cutover;
- no orphan profile-switch candidate/backup manifest exists without its transaction state;
- no stale or malformed `runtime-stop.env` marker is left behind;
- an installed systemd unit executes from `~/.local/share/qwen38-spark/current` rather than the mutable checkout;
- runtime image, model mount, served model name, loopback publication, and rollback-container state match the installation manifest;
- managed Docker-app and LAN API listeners match the API-access settings recorded in the installation manifest.

A memory monitor that was intentionally disabled at install time is reported as a healthy configured state:

```text
[PASS] runtime memory monitor is disabled by configuration
```

If the monitor is configured as enabled, a missing or stale monitor PID remains a failure. Memory margins are CMA-aware on DGX Spark: the monitor and doctor subtract `CmaFree` from both `MemAvailable` and `MemFree` before applying the normal available/free thresholds. This avoids treating CMA-reserved pages as a safe host-allocation margin for NVIDIA system-page allocation.

Fresh `orcarouter-hybrid` installs enable the monitor in protection mode by default. Existing manifests are not silently rewritten. When upgrading an older Hybrid install from a newer checkout, first advance the immutable runtime release through the normal qualified update path, then rewrite the existing profile settings with protection enabled:

```bash
TARGET="$(git rev-parse HEAD)"
bash ./scripts/release-manager.sh stage "${TARGET}"
bash ./scripts/lifecycle/qualify-release.sh "${TARGET}"
bash ./scripts/release-manager.sh verify "${TARGET}"
bash ./scripts/update-release.sh "${TARGET}"

./install.sh --model orcarouter-hybrid --protect --yes
```

The non-CMA available floor is a warning threshold. Protection uses two signals for low immediately-free memory: non-CMA free must be below `MONITOR_MIN_FREE_GIB`, and either non-CMA available must also be below `MONITOR_FREE_GATE_GIB` or swap consumption since the monitor started must have increased by at least 256 MiB. Swap-free below its configured floor remains independently protection-significant. This preserves the observed healthy large-checkpoint shard-loading transient, where non-CMA free briefly falls below 2 GiB while available memory stays high and swap-free is essentially unchanged, but arms protection once the same low-free condition coincides with sustained unified-memory paging. A persistent warning-only state is logged on entry and then at the configured heartbeat interval instead of every sampling interval; protection-counter samples are logged individually with swap-growth telemetry.

A protected stop writes `runtime-stop.env` and gracefully stops the inference container so systemd does not immediately restart the same memory-pressure workload. If protection fires while a replacement candidate is still starting, the runtime transaction removes that candidate, restores the previous container name in the stopped state, clears the transaction, and exits the service successfully rather than retrying the same startup. Operators can intentionally select warn-only mode with `--monitor`, or disable monitoring with `--no-monitor`.

Use strict mode when maintenance automation should fail on warnings as well as hard failures:

```bash
./scripts/doctor.sh --strict
```

Examples of signals that require operator attention include an incomplete update/runtime/profile-switch transaction, a tampered current immutable release, an unsafe/dangling release pointer, a legacy or digest-mismatched qualification marker, a service that no longer points at the immutable `current` root, a stale `runtime-stop.env` marker referencing a running or replaced container, or a managed API listener that no longer matches the installation manifest.

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
bash ./scripts/profile-switch-transition.sh status
```

Recover an interrupted profile switch first when it is active:

```bash
bash ./scripts/profile-switch-transition.sh recover
```

The profile-switch helper either proves and commits the target, proves and
restores the previous profile, or fails closed while leaving its persisted state
intact. Do not delete `profile-switch-transition.env`, its candidate/backup
manifests, or runtime attestation files to force a decision.

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

A normal uninstall removes the runtime/service resources recorded by the active installation manifest but intentionally keeps the immutable release history, `install.env`, and cumulative `asset-ownership.json` so a later reinstall or full purge still knows which model/image assets the installer actually created across profile switches:

```bash
./uninstall.sh
```

Owned managed API-access endpoints are removed together. API access created outside the installer remains untouched unless it was explicitly adopted into the manifest.

Uninstall refuses to start if `update-transition.env`, `runtime-transition.env`, or `profile-switch-transition.env` exists, and it also refuses orphan profile-switch candidate/backup manifests. Recover or roll back the owning transaction first rather than deleting lifecycle state manually.

Preview a full purge:

```bash
./uninstall.sh --purge-all --yes --dry-run
```

A full purge removes every model/image asset recorded as installer-owned in `asset-ownership.json`, plus the owned swap and application release/state lifecycle data:

```bash
./uninstall.sh --purge-all --yes
```

`--purge-all` first validates the ownership registry and all owned fingerprints, checks that retained/unowned model assets do not depend on an owned Hybrid parent, and checks that owned images are not referenced by other containers. Model deletion is ordered from dependents to dependencies (for example H6 → H5 → H4 → H3 → OrcaRouter base). Only after this preflight succeeds does deletion begin. It then deletes the application-owned `~/.local/share/qwen38-spark` tree, including `releases`, `qualified`, `current`, and `previous`, clears transient runtime/update/monitor state, and removes both `install.env` and `asset-ownership.json`.

`MODEL_OWNED` and `IMAGE_OWNED` remain in `install.env` for compatibility with older lifecycle code, but they describe only the active profile. The cumulative registry is authoritative for multi-profile purge. On first use of the new lifecycle code, the currently recorded legacy ownership can be imported into the registry. Ownership already lost by older profile switches is **not inferred** from the presence of a managed manifest or image tag; that would turn provenance into a guess.

The uninstaller continues to refuse deletion of assets that are not recorded as installer-owned, have drifted from their recorded manifest/image fingerprint, or are still required by retained dependents.

## Recommended maintenance sequence

Before maintenance:

```bash
./scripts/doctor.sh
./scripts/manage-proxy.sh status
bash ./scripts/update-transition.sh status
bash ./scripts/runtime-transition.sh status
bash ./scripts/profile-switch-transition.sh status
```

After maintenance:

```bash
./scripts/doctor.sh
./scripts/manage-proxy.sh status
bash ./scripts/release-manager.sh status
bash ./scripts/update-transition.sh status
bash ./scripts/runtime-transition.sh status
bash ./scripts/profile-switch-transition.sh status
curl -fsS http://127.0.0.1:8888/health
curl -fsS http://127.0.0.1:8888/v1/models
```

Do not consider an operation complete while any update, runtime, or profile-switch transaction state is non-idle.
