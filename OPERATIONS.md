# Qwen3.8 Flash Next — Operations Guide


## H38 runtime vs managed-service status

The qualified OrcaRouter H38 decoder-only runtime remains exposed through
`scripts/runtime/orcarouter-v029.sh --profile hybrid-h38-deterministic`.

This feature branch also implements the candidate transactional
installer/systemd integration for the existing `orcarouter` profile. It is
**not yet live-qualified or promoted**. The managed 16 GiB KV resilience
setting is retained; H38-specific PLE mmap, exact-QSA, decoder canonicalization,
and compile-cache controls are selected only when the installation manifest
selects the H38 image.

For an existing OrcaRouter installation, the H38 migration is one explicit
cross-release transaction. Stage/qualify the target immutable release, then run:

```bash
bash ./scripts/update-release.sh "${TARGET}" --refresh-profile-defaults
```

The coordinator builds/reuses and verifies H38, prepares the target manifest, activates
the target release + manifest pair, and only then starts the managed H38 replacement.
It does **not** require the persisted legacy CPU-offload image to become READY under
the new release. Failure restores the previous release pointers, canonical manifest,
runtime and service as one recovery boundary.

Do not skip directly from a mutable checkout to a manifest rewrite, do not use the
direct installer refresh as a substitute for this cross-release transaction, and do not
call the managed H38 path production until the lifecycle/restart/doctor,
managed-alias determinism, performance, and strict RM host-stability acceptance
in
`scripts/benchmark/evidence/orcarouter-h38-managed-integration-plan-20261007.md`
has passed.

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
bash ./scripts/release-profile-refresh-transition.sh status
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

The non-CMA available floor is a warning threshold. The current protection helper uses a heuristic for low immediately-free memory: non-CMA free must be below `MONITOR_MIN_FREE_GIB`, and either non-CMA available must also be below `MONITOR_FREE_GATE_GIB` or swap consumption since the monitor started must have increased by at least 256 MiB. Swap-free below its configured floor remains independently protection-significant. This is the **implemented safety heuristic**, not a proven discriminator for NVIDIA RM failure. Live Hybrid cold-load evidence has shown that the 256 MiB swap-growth arm can produce a false-positive protected stop during otherwise normal startup. Treat monitor protection as a fail-safe workload stop, not as HOST-STABILITY evidence by itself; the strict RM kernel-evidence rule remains authoritative. A persistent warning-only state is logged on entry and then at the configured heartbeat interval instead of every sampling interval; protection-counter samples are logged individually with swap-growth telemetry.

A protected stop writes `runtime-stop.env` and gracefully stops the inference container so systemd does not immediately restart the same memory-pressure workload. If protection fires while a replacement candidate is still starting, the runtime transaction removes that candidate, restores the previous container name in the stopped state, clears the transaction, and exits the service successfully rather than retrying the same startup. Operators can intentionally select warn-only mode with `--monitor`, or disable monitoring with `--no-monitor`.

Use strict mode when maintenance automation should fail on warnings as well as hard failures:

```bash
./scripts/doctor.sh --strict
```

Examples of signals that require operator attention include an incomplete update/runtime/profile-switch/release-profile-refresh transaction, a tampered current immutable release, an unsafe/dangling release pointer, a legacy or digest-mismatched qualification marker, a service that no longer points at the immutable `current` root, a stale `runtime-stop.env` marker referencing a running or replaced container, or a managed API listener that no longer matches the installation manifest.

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

Perform an ordinary code-only cutover when the persisted runtime image is intentionally retained:

```bash
bash ./scripts/update-release.sh "${TARGET}"
```

For the OrcaRouter cross-release H38 migration, use the atomic release + profile-default refresh path instead:

```bash
bash ./scripts/update-release.sh "${TARGET}" --refresh-profile-defaults
```

The ordinary update path changes the immutable `current` pointer and validates the
persisted runtime. The atomic H38 path owns the target release and H38 install manifest
together and starts only the H38 replacement. Do not use the ordinary path as a
precondition that requires legacy READY before H38 migration.

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

## Managed lifecycle acceptance: read-only snapshot before live operations (2026-10-12)

The staged lifecycle acceptance matrix is [docs/MANAGED-LIFECYCLE-ACCEPTANCE.md](docs/MANAGED-LIFECYCLE-ACCEPTANCE.md). **Implementation/CI and synthetic dry-run PASS are not complete live installation, uninstall, or profile-switch qualification**. The H38 managed runtime remains blocked independently of read-only state collection.

After synchronizing to a clean **exact CI-qualified** commit, inspect the current DGX host using:

```bash
QWEN38_LIFECYCLE_AUDIT_TARGET_SHA="$(git rev-parse HEAD)" \
  bash scripts/lifecycle/inspect-readonly-lifecycle.sh
```

The helper itself checks for a clean checkout and SHA equality. It only runs `install.sh --list-models`, `install.sh --list-backends`, `profile-switch-transition.sh status`, `runtime-transition.sh status`, `update-transition.sh status`, `release-profile-refresh-transition.sh status`, and `scripts/doctor.sh`. It **does not** invoke installation, uninstallation, purge, model/GPU launch, service restart or protection changes. `COLLECTED_READ_ONLY` means all seven snapshot commands returned success, **not** that live end-to-end has passed. A failed Doctor or state check is reported as `PARTIAL_CHECK_FAILURE` and should be reviewed without forcibly clearing transaction state.

Bilingual uninstall preview regression coverage runs against disposable manifests in `tests/test_uninstall_wizard_preview.py`. The uninstaller's `--dry-run` preview exits **before** its real destructive operation-lock and transaction checks; an attractive dry-run output is **not authorization to execute** `--purge-all`, `--purge-model`, `--purge-image` or `--purge-swap` on the active DGX. Full destructive acceptance must use an independently disposable host and explicitly preserved external user assets. Never run full-purge lifecycle validation on the sole Spark merely to close a checklist item.

## Runtime-exited read-only triage after a partial Doctor (2026-10-12)

The actual DGX M1 snapshot in [managed lifecycle Attempt 01 evidence](scripts/benchmark/evidence/managed-lifecycle-readonly-attempt01-doctor-partial-20261012.md) reported `PARTIAL_CHECK_FAILURE`: all four profile/runtime/update/refresh transaction states idle, valid installed checkpoints/releases/asset registry, but Doctor **five FAIL / two WARN**. An **exited** legacy OrcaRouter container, **inactive** systemd service, missing/unsafe runtime-commit attestation, missing monitor PID, no Docker published port and failed health endpoint were observed. A correctly parsed manifest or healthy memory/swap reserve does **not** authorize a restart or prove a stable serving runtime.

A further **non-mutating** discriminator is available at `scripts/lifecycle/inspect-readonly-runtime-offline.sh`. After explicit clean exact SHA validation it reads **only** `docker inspect` state/ExitCode/OOMKilled/timestamps and declared port mappings, `systemctl show` state/result/status properties, and file type/size/timestamps (not contents) of the three state files `runtime-commit.env`, `runtime-stop.env`, `monitor.pid`. Use it with a CI-qualified branch HEAD:

```bash
QWEN38_OFFLINE_DIAGNOSTIC_TARGET_SHA="$(git rev-parse HEAD)" \
  bash scripts/lifecycle/inspect-readonly-runtime-offline.sh
```

`MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY` certifies successful **metadata collection**, not health or readiness. If it reports `PARTIAL_READ_FAILURE`, preserve per-command exit codes and report the missing metadata. `RUNTIME_STOP_REASON=NOT_YET_PROVEN` remains until grounded logs and state evidence resolve it.

**Never clear or regenerate runtime-commit.env, remove runtime-stop.env, change monitor protection, force transaction recover/commit, or start/restart the legacy or H38 runtime merely to satisfy Doctor.** Inspect the current and previous immutable release/transaction ownership and stopped runtime cause first. No actual model/GPU, checkpoint payload, destructive uninstall, Docker/container mutation, or PR Ready/Merge is part of this diagnostic.

## Actual stopped runtime Docker/systemd metadata and bounded journal window (2026-10-12)

At actual DGX offline inspection HEAD `6ce45561640f4069d534cbe04f5064a39095a88a`, the current legacy OrcaRouter Docker container was `exited` with `ExitCode=0`, `OOMKilled=false`, `State.Error=""`. Docker **declared** port binding `8888/tcp → 127.0.0.1:8888` is correct; `NetworkSettings.Ports={}` on the exited runtime explains why a `docker port` read can report none. Systemd was `inactive/dead` but reported `Result=success`, `ExecMainCode=1` (process exited class), `ExecMainStatus=0`. Docker finished **2026-10-07 22:08:34 KST**. Systemd entered active at **22:08:29 KST** and inactive at **22:18:17 KST**. The transient `runtime-commit.env`, `runtime-stop.env` and `monitor.pid` files were all absent when observed. [Canonical evidence](scripts/benchmark/evidence/managed-runtime-offline-attempt01-exit0-no-oom-20261012.md). The actual stop requester, protective-monitor action, and earlier cleanup history remain UNKNOWN; no explicit reason was present in the metadata.

As a **final bounded, non-mutating discriminator**, after an exact clean CI-qualified checkout, run:

```bash
QWEN38_STOP_JOURNAL_TARGET_SHA="$(git rev-parse HEAD)" \
  bash scripts/lifecycle/inspect-readonly-runtime-stop-journal.sh
```

The script requires the checkout pin and host `+0900` timezone. It retrieves **only** `qwen38-flash-next.service` unit entries for **2026-10-07 21:55:00–22:25:00 KST**, capped at **160 lines**. Output is historical journal evidence, not current service activation. It reports `COLLECTED_READ_ONLY` if lines were read, or `INCONCLUSIVE_OR_READ_FAILURE` if no lines/permission/error; its `RUNTIME_STOP_CAUSE=NOT_YET_CLASSIFIED` is deliberately **not** an assessment of the messages. Historical log content may contain identifiers or sensitive values: inspect/redact secret values before sharing.

**Do not restart/start the service or Docker container, fabricate runtime-commit attestation, remove stop markers, change monitor/protection settings, or run `--refresh-profile-defaults` based on the existing Doctor FAIL.** An exited container with exit0 is not enough to call the runtime stable, and an empty port mapping in the exited state is not enough to call port configuration wrong. M1 healthy LIVE E2E remains NOT_QUALIFIED.

## October 7 managed transition stop is now documented as a protection-triggered abort (2026-10-12)

The [actual bounded service-journal evidence](scripts/benchmark/evidence/managed-runtime-stop-journal-attempt01-protected-abort-20261012.md) identified an explicit sequence that the earlier container/Doctor snapshots alone could not resolve. The **previous canonical runtime** returned HTTP 200 before the managed transition; it was **gracefully stopped at 22:08:30 KST**, the **new candidate** started with monitor `protect=1` at **22:08:35**, readiness validation had reached `540/1800s`, then at **22:18:16** the service reported `Candidate runtime was stopped by memory protection during startup`. At **22:18:17** the old runtime was **restored but left stopped**, and the transition was **aborted by memory protection with state=idle**. This directly explains the Docker `ExitCode=0`/non-OOM previous-container exit, inactive systemd unit, absent attestation and failing Docker-port/health-readiness Doctor observations. It **does not** prove the new candidate was healthy, the specific monitor threshold, false-positive protection, or NVIDIA RM stability.

The candidate monitor startup line names `/home/inlc/.local/state/qwen38-spark/monitor.log`. Exactly **one** further numeric diagnostic is available for a clean, exact CI-qualified branch SHA:

```bash
QWEN38_MONITOR_TRIGGER_TARGET_SHA="$(git rev-parse HEAD)" \
  bash scripts/lifecycle/inspect-readonly-monitor-trigger.sh
```

It checks a regular non-symlink readable `monitor.log` at `XDG_STATE_HOME` (default `~/.local/state/qwen38-spark`), refuses files over 64 MiB and prints only the first **120 structured monitor messages** from **2026-10-07 22:08–22:19 local time**. It excludes arbitrary Docker model logs and messages not explicitly matching monitor counters/PROTECT/heartbeat. `COLLECTED_READ_ONLY` confirms data collection **only**; `INCONCLUSIVE_OR_READ_FAILURE` leaves the **specific triggered predicate UNKNOWN**. Source monitor heuristic checks swapfree critical floor or low non-CMA free combined with low available/free gate or sustained swap-growth. Do not assume which branch caused Oct07 abort without the original numeric counters; any historical monitor source/config differences also remain unverified.

After this bounded numerical-sample inspection (or a missing file), **stop expanding H38 runtime archaeology** and return to lifecycle acceptance: synthetic installer/uninstaller, ownership-safe disposable-host uninstall/reinstall, and reversible profile-switch test matrix. No service restart, Docker start, monitor threshold/protection changes, attestation fabrication, H38 model/GPU, checkpoint payload, PR Ready or Merge; current M1 live host is **not healthy/qualified**.

## Oct 07 memory monitor: actual low-free + swap-growth 5/5; diagnostics complete (2026-10-12)

The final, bounded **actual DGX monitor numeric-sample** read ran at operator HEAD `7e4580bdca4054a788715bdf141e006bbb6b3f59`, with no service/model/protection mutation and `MONITOR_TRIGGER_READONLY=COLLECTED_READ_ONLY` (`monitor_audit_rc=0`). [Canonical numeric evidence](scripts/benchmark/evidence/managed-monitor-trigger-attempt01-low-free-swap-growth-pass-20261012.md).

The exact candidate monitor startup line at **2026-10-07 22:08:35 KST** said `mode=protect noncma-free=2GiB free-gate=10GiB swap-growth=256MiB swapfree=8GiB`. At **22:17:33**, `noncmafree=2017MiB` but `swapgrowth=17MiB` so `protect=0/5`. At **22:17:35** `noncmafree=1151MiB` and `swapgrowth=654MiB` crossed the combined protective condition. Consecutive **1/5 to 5/5** samples completed by **22:17:43**, when the monitor explicitly logged `PROTECT stopping`. Across these samples `noncma_available` stayed **>10GiB** and `swapfree` stayed **>8GiB**, ruling out those two alternative monitor branches for the observed stop.

The following service journal recorded **22:18:16** protected-candidate abort and **22:18:17** previous runtime restored in stopped state. Thus the observed stop was **the actual configured low non-CMA free plus swap-use growth heuristic**, NOT proof of an actual kernel OOM, NVIDIA RM `NV_ERR_NO_MEMORY`, or necessarily a correctly calibrated memory safeguard. The previous Docker exited status 0 and OOMKilled=false refer to the **old** runtime. **Never disable/relax the monitor, restore runtime attestation or restart the container merely to make Doctor green.**

**Do not rerun the historical monitor/journal probe.** The remaining investigation about whether protection was necessary belongs to a separately approved H38 runtime/stability program, presently **BLOCKED**. Continue the user's main task: synthetic installer and uninstall wizard validation, profile-switch transition recovery and asset ownership, and disposable-host end-to-end acceptance. M1 live host remains `NOT_QUALIFIED`, M2 destructive E2E `NOT_RUN`, M3 all-pairs `NOT_QUALIFIED`. PR #259 remains Draft/Open and not merged.


## Destructive uninstall swap ownership preflight (2026-10-12)

For `--purge-swap` and `--purge-all`, `SWAP_OWNED=1` is required **before any destructive step**. An unowned swap refuses real uninstall without registry bootstrap, service/container teardown or partial model/release deletion. The dry-run preview intentionally exits before this real-operation preflight and **must not be interpreted as deletion approval**. The synthetic fixture regression in `tests/test_uninstall_wizard_preview.py` checks early refusal without executing host Docker/systemd/swap actions. Do not use the active single DGX for real purge validation.


## Uninstall cancellation before ownership registry bootstrap (2026-10-12)

The typed `DELETE` consent for a real uninstall now occurs before creating `operation.lock` or migrating the manifest into `asset-ownership.json`. Refusal or EOF is fail-closed without modifying install files or runtime assets. After consent, the uninstaller obtains the operation lock, rechecks active/stale lifecycle transactions, bootstraps registry and applies its usual destructive-eligibility checks. `--yes` skips only interactive consent, never safety preflights. Unowned swap remains rejected before the prompt; `--dry-run` remains preview-only. This is synthetic-regression coverage, NOT authorization to uninstall anything on the single active DGX Spark.


## Ownership preflight does not mutate canonical registry on refusal (2026-10-12)

For real uninstall after `DELETE` or `--yes`, the uninstaller takes its existing operation lock and creates a private `.uninstall-preflight.*` stage in the lifecycle state directory. It copies the current cumulative registry (if any), bootstraps legacy ownership there and runs model/image/full-purge plus external-container and unowned-service checks **against the staged data**. Failure exits with the canonical `asset-ownership.json`, install manifest, service, model and image data unchanged; the staging directory is normally removed by an EXIT trap. The operation lock file may be created and retained. Only successful preflight allows registry publication and subsequent teardown. This does **not** promise atomic rollback if actual deletion subsequently fails or the host/process crashes. Do not run real purge on the active single DGX.


## Docker removal failure and partial-uninstall retry safety (2026-10-12)

Previously `uninstall.sh` ignored **every** `docker rm -f` failure with `|| true`, risking model/image/release deletion when the Docker daemon or authorization was broken and the managed container could still exist. Now arbitrary Docker errors are **fail-closed before asset purge**; only an exact Docker `No such container: <managed name>` message permits idempotent continuation. `PHASE=complete` remains when service/container removal fails, allowing an operator-directed retry. `asset-ownership.json` may already reflect the successful preflight; the service may already have been disabled or removed. Neither rollback of completed teardown nor crash-atomicity is claimed. Real managed host and H38 model remain untouched. New disposable synthetic fault-injection regressions cover service-remove failure, Docker-remove failure, retry-after-recovery and already-absent Docker container; final CI result to be recorded in PR #259. M1 live host NOT_QUALIFIED, M2 destructive E2E NOT_RUN, M3 profile all-pairs NOT_QUALIFIED, M4 H38 BLOCKED, PR Draft/Open, Merge BLOCKED.


### Post-teardown failure and safe retry: synthetic CI acceptance (2026-10-12)

**Evidence:** [CI #38189466067](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38189466067) **SUCCESS, 771/771** at `09527d81121ad6fe820400382a12eb9a443318b6`; [CI #38189596217](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38189596217) **SUCCESS, 772/772** at `69df950fc4a7f1c6038ab8aff9f5e3ee45dc80b7`, including Bash syntax, ShellCheck, Python compilation and whitespace checks.

A synthetic real-CLI sequence using only disposable HOME/XDG and command denial/stubs shows:
1. Managed service-removal fault => no Docker removal attempt, owned synthetic model intact, manifest `PHASE=complete`.
2. Service removal succeeds, Docker daemon removal fails => script exits nonzero **before** model/image/release purge, records no completed uninstall, owned model and release preserved; published registry retains ownership evidence.
3. After fault clearance, retry completes, removes the **synthetic owned model only**, retains release data and sets `PHASE=uninstalled`.
4. An exact Docker `No such container` diagnostic is idempotent; unowned model and release remain.
5. On `--purge-all`, after **synthetic model and image removal** a simulated swap-remove failure exits nonzero with remaining fake swap and release preserved, manifest still `PHASE=complete` and cumulative registry reflecting completed asset removal. On retry after fault clearance, the script tolerates the already absent owned model/image, removes only the fake swap and synthetic release/manifest, and completes.

This proves bounded **synthetic retry behavior**, NOT rollback of previously removed components, interruption/crash durability, actual systemd/Docker/PLE behavior, independent disposable-host install/remove/reinstall E2E, or single-DGX host qualification. Actual DGX was untouched. M1 actual host NOT_QUALIFIED; M2 destructive E2E NOT_RUN; M3 all-profile E2E NOT_QUALIFIED; M4 H38 BLOCKED. PR #259 remains Draft/Open, Ready/Merge BLOCKED.


## SIGKILL interrupted-uninstall preflight recovery (2026-10-12)

Under the lifecycle operation lock and before creating a staged ownership copy or doing any teardown, `uninstall.sh` now refuses existing `.uninstall-preflight.*` artifacts, including symlinks. A `SIGKILL` or power loss bypasses shell EXIT traps, so these private staging snapshots may survive. Do **not** automatically delete them or treat them as canonical ownership evidence. Inspect each exact stale path, verify ownership and contents, confirm no concurrent lifecycle operation, and handle its removal/quarantine only as a separately authorized maintenance action. No blanket wildcard deletion on the active DGX. This guard is fail-closed: the install manifest and canonical ownership registry remain authoritative, and model/image/swap removal cannot proceed while an unreviewed preflight snapshot exists. Synthetic SIGKILL crash tests and exact GitHub CI evidence are tracked in PR #259; actual power-loss durability is NOT_QUALIFIED. PR remains Draft/Open and merge blocked.


### Interrupted uninstall recovery procedure and validation boundaries (2026-10-12)

**Stop condition:** a `.uninstall-preflight.*` artifact, missing model ownership manifest, drifted registry fingerprint, interrupted model deletion, or a state/host mismatch is **not** permission to resume unattended `uninstall.sh --yes`. Leave all host protection and stopped runtime settings intact.

1. Preserve evidence before any repair: read the canonical `install.env`, `asset-ownership.json`, exact `.uninstall-preflight.*` entries, file owner/mode and applicable logs **without executing the staged file or running host mutators**. The canonical registry is the only ownership authority; staged snapshots are untrusted. Acquire or confirm exclusive lifecycle maintenance ownership before any later mutation.
2. Reconcile actual read-only service/container/swap state with the recorded manifest. `PHASE=complete` after a crash **does not** mean the service is still installed, container still exists, model remains complete or swap is intact. Never infer successful teardown from parent process exit status alone; child deletion commands may outlive a killed parent.
3. For a verified orphan staging directory, document its exact path and integrity, quarantine/clear **only that exact path** after operator review, and rerun preflight before resuming; never use broad `rm -rf` globs or follow symlinks. Unreviewed staging blocks the real uninstaller.
4. For a partially deleted model with a missing/drifted `.qwen38-model-manifest.json` or `.qwen38-hybrid-manifest.json`, keep the original cumulative registry and the surviving model data; **do not invent a marker or weaken preflight**. Recovery requires independent trusted backup/provenance verification, otherwise quarantine and a separately authorized reinstall on an isolated disposable host.
5. If a fully removed owned model is already absent but a dedicated swap/release remains, a repeat purge is eligible **only after** checking the original model path, ownership history, live host state, swap provenance and pending lifecycle artifacts. No automated or live sole-DGX destructive recovery is authorized by the synthetic tests.
6. Preserve an interruption evidence report (files/hashes, timeline, host-command results, whether child process survived, repair decision). Host power-loss filesystem ordering/fsync, SIGKILL of the whole process group, real teardown replay and install→remove→reinstall remain unverified separately.

Synthetic `test_sigkill_during_stage_requires_manual_stale_recovery`, `test_sigkill_partway_through_model_delete_requires_verified_recovery`, and `test_sigkill_at_swap_after_model_purge_can_resume` use the **real** CLI with disposable HOME/XDG, fake owned model/swap and PATH-denied Docker/sudo/systemctl/swapoff. Their SIGKILL is injected from a child stub and the stub must exit immediately rather than completing its own deletion after killing the parent. These tests do not simulate power loss or provide live-host authorization. Previous failing CI attempts due to a child-stub execution bug are retained as historical failures; the corrected commit and its CI outcome are recorded in PR #259. All M1 actual-host/M2 real-destructive/M3 all-profile/H38 gates remain blocked or unqualified; PR #259 remains Draft/Open, Ready/Merge BLOCKED.


## Guarded DGX code synchronization and synthetic-only local verification (2026-10-12)

The previous 775/775 GitHub Actions result was **CI**, not evidence that the operator's single DGX had fetched the latest branch or run any tests locally. To close this handoff gap without touching live host resources, `scripts/lifecycle/verify-synthetic.sh` now validates an explicitly supplied 40-character checkout SHA, clean Git worktree, exact `feat/h38-managed-integration` branch and matching `origin/feat/h38-managed-integration` tracking ref **without any Git mutation**. It then runs bounded Python synthetic lifecycle suites inside a disposable HOME/XDG_STATE_HOME/XDG_DATA_HOME/TMPDIR, with a first-in-PATH deny wrapper for Docker, sudo, systemctl, swapoff/swapon, mount/umount and nvidia-smi. Tests are restricted to installer/uninstaller preview, ownership, operation lock, lifecycle integration and non-mutating lifecycle snapshot tests; no actual install/uninstall, Docker, service change, runtime startup, model download or host Doctor is invoked. The test wrapper is itself exercised on GitHub Actions in `--ci` mode and refuses `--ci` outside `GITHUB_ACTIONS=true`.

**Operator sync procedure, not executed by ChatGPT:** on the actual DGX working checkout, require `git status --porcelain=v1 --untracked-files=all` empty and the expected feature branch already selected; `git fetch --prune origin`; confirm `origin/feat/h38-managed-integration` equals the **exact tested target SHA**; then `git merge --ff-only origin/feat/h38-managed-integration`, confirm HEAD and worktree, and invoke the new verifier with that SHA. No `git reset --hard`, stash/pop, force merge or automatic checkout switching. Sync/test modifies the local Git checkout and disposable test files only; no remote host access or DGX test was performed from ChatGPT. **Report DGX_LOCAL_SYNTHETIC=NOT_RUN until the operator supplies actual local output.** Keep `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, PR #259 Draft/Open; Ready/Merge BLOCKED.


### Verified safe Git sync and synthetic-only DGX test handoff (2026-10-12)

[CI #38192014751](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38192014751) **SUCCESS** for code commit `c915f805b7fe7abbc8a260379df69148ef5f54e6`: **780/780** full unit tests, Bash syntax, ShellCheck, Python compilation, whitespace, plus an actual execution of `scripts/lifecycle/verify-synthetic.sh` in the GitHub PR checkout with **48/48** bounded synthetic tests (16 uninstall wizard, 6 asset ownership, 8 operation lock, 14 lifecycle integration, 4 snapshot tests). The GitHub Actions checkout may be a PR merge SHA rather than the feature branch HEAD; the verifier checks the exact SHA **of the checkout it is given**. An earlier [CI #38191976973](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38191976973) failure was a missing-SHA message/test mismatch; corrected in `c915f80` with tests passing.

**DGX operator-only sync/test, not run by ChatGPT**: choose the latest verified GitHub branch head SHA as `TARGET`. Start on branch `feat/h38-managed-integration` with a clean worktree. Confirm remote `origin` points to the expected GitHub repository, fetch only the branch without tags, assert `origin/feat/h38-managed-integration` equals the pinned SHA, and fast-forward only with Git hooks disabled. Never reset/stash/force-overwrite local edits. Then run `bash scripts/lifecycle/verify-synthetic.sh "$TARGET"` to verify the exact local checkout. This tool **does not run fetch/merge**, Docker, service manager, install, uninstall, runtime/host Doctor or any model; it runs only the five synthetic test modules under disposable HOME/XDG/TMPDIR and intercepts host commands through PATH stubs. **PATH interception is not an OS-level sandbox**; tests are allowlisted after source review and GitHub CI qualification. If remote advanced beyond the pinned target or any preflight fails, stop without changing the checkout and reassess the SHA.

`DGX_LOCAL_SYNTHETIC=NOT_RUN` until the operator sends the **actual DGX output** (including exact SHA and `LOCAL_SYNTHETIC_RESULT=PASS`). `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, PR #259 Draft/Open and Ready/Merge BLOCKED.

```bash
# Pin TARGET to the exact SHA verified in PR #259 before starting.
(
  set -Eeuo pipefail
  cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark
  BRANCH="feat/h38-managed-integration"
  TARGET="<approved-40-character-GitHub-head-sha>"

  [[ "$TARGET" =~ ^[0-9a-f]{40}$ ]]
  [[ "$(git branch --show-current)" == "$BRANCH" ]]
  [[ -z "$(git status --porcelain=v1 --untracked-files=all)" ]]
  ORIGIN="$(git remote get-url origin)"
  case "${ORIGIN%.git}" in
    https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark|git@github.com:kjlee-inlct/qwen3.8-flash-next-dgx-spark) ;;
    *) printf 'Wrong GitHub origin: %s\n' "$ORIGIN" >&2; exit 2 ;;
  esac
  git -c core.hooksPath=/dev/null fetch --no-tags origin \
    "refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
  [[ "$(git rev-parse "refs/remotes/origin/$BRANCH")" == "$TARGET" ]]
  git -c core.hooksPath=/dev/null merge --ff-only "refs/remotes/origin/$BRANCH"
  [[ "$(git rev-parse HEAD)" == "$TARGET" ]]
  [[ -z "$(git status --porcelain=v1 --untracked-files=all)" ]]
  bash scripts/lifecycle/verify-synthetic.sh "$TARGET"
)
```

This updates **only the operator's Git worktree** (fast-forward, if verified) and disposable synthetic test fixtures. It is **not** a real install/uninstall, actual runtime check or E2E acceptance. Preserve the command output for evidence and do not run on a dirty checkout.


## Selected model profile first: DGX read-only status then synthetic regression (2026-10-12)

The operator supplied actual **single-DGX** output from the earlier guarded
fast-forward to \`0e910a7e0ab6246228857cc9432c19b5787eb812\`:
\`LOCAL_SYNTHETIC_RESULT=PASS\`, **48/48 fixture tests PASS**,
\`DGX_SYNTHETIC_VALIDATION_COMPLETE\`. Local ShellCheck was
\`SKIPPED_NOT_INSTALLED\`; the same earlier GitHub CI passed ShellCheck.
This qualifies only the local synthetic test handoff, **not** a live
model/service, E2E uninstall or host stability check.

For subsequent verified branch syncs, use the already documented exact-SHA,
clean-worktree, expected-origin, fetch and \`git merge --ff-only\` guards.
**Place the following status and test steps in this order after Git sync:**

\`\`\`bash
# Normal operator HOME/XDG: inspect the configured profile and observed status.
python3 scripts/lifecycle/inspect-selected-profile.py

# Target is the same verified GitHub feature-branch HEAD used in the sync.
bash scripts/lifecycle/verify-synthetic.sh "$TARGET"

# Optional expanded read-only inventory, transition statuses and Doctor.
# Doctor may return a nonzero code because M1 live host is NOT_QUALIFIED.
QWEN38_LIFECYCLE_AUDIT_TARGET_SHA="$TARGET" \
  bash scripts/lifecycle/inspect-readonly-lifecycle.sh
\`\`\`

The first command is read-only: strictly parses \`install.env\`,
transaction markers and optional \`docker inspect --type container\` /
\`systemctl show\` observations. It does **not** call Docker run/start/stop,
systemctl restart, sudo, uninstall, install, a model or GPU. It reports
\`SELECTED_PROFILE\` (stored installation intent), \`INSTALL_PHASE\`,
\`MODEL_PATH_STATUS\`, \`MONITOR_PROTECT\`, \`SERVICE_STATE\`,
\`CONTAINER_STATE\`, four transition states, and the observed
\`RUNTIME_CONFIGURATION\`. Even a matching running container is labeled
\`MATCHED_NOT_READINESS\` with \`ACTUAL_SERVED_PROFILE=NOT_VERIFIED\`;
the snapshot alone can never produce \`HOST_HEALTH=PASS\`.

If the profile snapshot returns code **3**, a malformed install manifest or
pending/unsafe transition artifact was detected: examine its output rather
than proceeding blindly. Do not remove artifacts, fabricate attestation,
relax monitor protection, or restart the runtime. An inactive service or
stopped container is recorded honestly and does not itself require mutation.

The synthetic verifier still uses disposable HOME/XDG and now tests the
snapshot logic via fake Docker/systemctl fixture commands, **never the real
host state**. As of this commit, the new DGX status snapshot has not been
executed on the DGX; only the earlier local synthetic result above is
operator-evidenced. PR #259 remains Draft/Open, M1 actual host
NOT_QUALIFIED, M2 destructive E2E NOT_RUN, M3 all-pairs NOT_QUALIFIED,
M4 H38 BLOCKED, Ready/Merge BLOCKED.


## DGX actual selected-profile and isolated test evidence (2026-10-12)

**Source:** operator-provided actual DGX transcript, fast-forward from `0e910a7`
to exact feature HEAD `87fb463984683f75435302eff5ffc3b3b9f941bf` with clean
post-test checkout and `DGX_PROFILE_AND_SYNTHETIC_VALIDATION_COMPLETE`.
`verify-synthetic.sh` reported `LOCAL_SYNTHETIC_RESULT=PASS` with **56/56**
disposable synthetic tests (16 uninstall, 6 ownership, 8 lock,
14 integration, 8 selected-profile snapshot, 4 read-only snapshot).
Local `BASH_SYNTAX=PASS`; `SHELLCHECK=SKIPPED_NOT_INSTALLED` (separately,
[GitHub CI #38194619518](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38194619518)
SUCCESS: 788/788 full unit tests and ShellCheck PASS). **DGX_LOCAL_SYNTHETIC=PASS at
this exact SHA only.**

Actual read-only DGX `inspect-selected-profile.py` reported:

| Observed field | Reported value / qualification |
|---|---|
| `MANIFEST_STATUS` / `INSTALL_PHASE` | `VALID` / `complete` |
| `SELECTED_PROFILE` | `orcarouter` (configuration intent) |
| `PROFILE_REPOSITORY` | `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` |
| `EXPECTED_IMAGE` and `CONTAINER_IMAGE` | `vllm-skinny-tp1:v1` (legacy installed tag; H38 not active) |
| `MODEL_PATH_STATUS` | `MARKER_PRESENT_NOT_VERIFIED` (not checksum/integrity) |
| `MONITOR_PROTECT` / `MONITOR_ENABLED` | `1` / `1` (configured, not verified running protection) |
| `PROFILE_SWITCH_STATE`, `RUNTIME_TRANSITION_STATE`, `UPDATE_STATE`, `RELEASE_PROFILE_REFRESH_STATE` | all `IDLE` |
| `STALE_TRANSACTION_ARTIFACTS` | `NONE` (only the configured tracked subset) |
| `CONTAINER_STATE` / `SERVICE_STATE` | `EXITED` / `INACTIVE` |
| `RUNTIME_ATTESTATION` | `MISSING`; do not manufacture it |
| `PROFILE_STATUS_SUMMARY` | `CONTAINER_NOT_RUNNING` |
| `ACTUAL_SERVED_PROFILE` | `NOT_VERIFIED` |
| `HOST_HEALTH_QUALIFICATION` | `NOT_ESTABLISHED_BY_THIS_SNAPSHOT` |

**Interpretation and next priority:** Git code/tests are synchronized and the
selected profile is `orcarouter`, but the runtime is stopped. Its stop cause
is **NOT YET DETERMINED** by this newly submitted output: an exited container
plus inactive service does not prove OOM, a protection-triggered stop,
deliberate administrative shutdown or a runtime error. Runtime commit
attestation is absent; never reconstruct an attestation without verified
provenance. H38 code is not an installed/serving H38 model. Retain host
monitor/protection and all stopped services as observed: **NO restart, H38 GPU
rerun, swap cleanup, reinstall, profile-switch or uninstall**.

**Next existing read-only tool (no new script or additional Git pull is
required at verified SHA `87fb463...`):**
```bash
(
  set -Eeuo pipefail
  cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark
  TARGET=87fb463984683f75435302eff5ffc3b3b9f941bf
  test "$(git rev-parse HEAD)" = "$TARGET"
  test -z "$(git status --porcelain=v1 --untracked-files=all)"
  QWEN38_OFFLINE_DIAGNOSTIC_TARGET_SHA="$TARGET" \
    bash scripts/lifecycle/inspect-readonly-runtime-offline.sh
)
```
This existing exact-SHA helper reads `docker inspect` (container exit
code, OOMKilled, start/finish timestamp, state error, declared ports),
`systemctl show` (ActiveState/Result/ExecMainCode/ExecMainStatus/timestamps),
and `stat` file metadata for `runtime-commit.env`, `runtime-stop.env` and
`monitor.pid`. It prints `RUNTIME_STOP_REASON=NOT_YET_PROVEN`; the output
is **evidence for triage**, not authorization to restart or proof of cause.
Historical Oct-07 journal/monitor scripts are time-window bound, so only use
them after checking whether the observed `FinishedAt` falls in their
documented window. If the offline command returns 3, preserve its partial
results and do not reinterpret failure as stop-cause evidence.

**Gates:** `DGX_LOCAL_SYNTHETIC=PASS` at specified SHA, but
`M1_HOST_HEALTH=NOT_QUALIFIED`, `HOST_STABILITY=INCONCLUSIVE`,
`M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`,
`M4_H38=BLOCKED`, `HOST_PROTECTION=UNCHANGED`; PR #259 Draft/Open,
Ready/Merge BLOCKED.


## Reconciled DGX offline repeat versus previously resolved Oct 7 protection stop (2026-10-12)

The operator's latest **actual DGX** read-only `inspect-readonly-runtime-offline.sh`
run at a clean exact checkout `87fb463984683f75435302eff5ffc3b3b9f941bf`
completed all three queries (`rc=0`) and returned `MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY`.
Docker `status=exited exit_code=0 oom_killed=false`, started **2026-10-07
16:35:45.800732 KST**, finished **22:08:34.847185 KST**; correct declared
loopback `127.0.0.1:8888` binding with no active port mapping while stopped.
Systemd `Result=success ExecMainCode=1 ExecMainStatus=0 inactive/dead`,
ActiveEnter **22:08:29 KST**, InactiveEnter **22:18:17 KST**.
`runtime-commit.env`, `runtime-stop.env`, and `monitor.pid` were **ABSENT**
at observation. The repeated values match the older exact-DGX
[offline Attempt 01](scripts/benchmark/evidence/managed-runtime-offline-attempt01-exit0-no-oom-20261012.md)
recorded at a different checkout, not a new runtime or H38 test.

**Resolve chronology using existing historic evidence, not an additional
monitor experiment.** The already archived
[service journal](scripts/benchmark/evidence/managed-runtime-stop-journal-attempt01-protected-abort-20261012.md)
explicitly records graceful stop of the **previous** container for candidate
handover **22:08:30**, candidate monitor/start at **22:08:35**, and candidate
abort by memory protection **22:18:16**, then **previous container restored
but left STOPPED 22:18:17**. The separately archived
[numeric monitor samples](scripts/benchmark/evidence/managed-monitor-trigger-attempt01-low-free-swap-growth-pass-20261012.md)
confirm low non-CMA free memory **below 2 GiB** together with swap growth
**at least 256 MiB**, counted for **5 consecutive protection samples**
and `PROTECT stopping` at **22:17:43**. Thus the stopped canonical container's
`exit_code=0 oom_killed=false` correlates with the previous container's
handover/rollback, **not** with the candidate's unobserved Docker exit.
There is no candidate immutable ID or attestation proof in the new snippet;
no kernel OOM/NVIDIA RM failure, false positive, safe memory peak or
candidate READY may be inferred.

This reconciliation supersedes earlier **intermediate** lines stating the
Oct 7 *managed transition's* stop cause or protection threshold branch were
still wholly undetermined. The inspector itself intentionally emits the
literal `RUNTIME_STOP_REASON=NOT_YET_PROVEN` as a collection marker, and
must remain unchanged. The **managed-service protection-abort sequence
and numeric trigger branch are confirmed by earlier evidence**, while
ultimate kernel/driver/model root cause and protective-policy appropriateness
are still **UNVERIFIED**. No new H38 GPU rerun or additional journal hunt.

Canonical new [repeat cross-check evidence](scripts/benchmark/evidence/managed-runtime-offline-repeat-crosscheck-20261012.md)
preserves source, timestamps and limits. `DGX_LOCAL_SYNTHETIC=PASS` only
for the earlier 56/56 locally run at `87fb463`; the new docs-only GitHub
HEAD has **not** been pulled/tested on the DGX. Maintain
`M1_HOST_HEALTH=NOT_QUALIFIED`,
`M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`,
`M4_H38=BLOCKED`, `HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`,
PR #259 **DRAFT/OPEN, Ready/Merge BLOCKED**. Primary next engineering
priority is **host-independent installer/uninstaller/profile-switch acceptance**,
then independent disposable-host E2E. Do not restart or mutate the sole DGX.


## Fail-closed uninstall plan, Docker dependency, and image absence (2026-10-12)

GitHub source-only hardening captures an ownership `plan-purge` during staged
preflight with an explicit successful producer exit; partially output
nonzero plans cannot authorize teardown. External `docker ps` must succeed,
not merely return zero results; `docker image inspect` must explicitly
report `No such image/object` to authorize an absent image. Unexpected
Docker command failures stop the purge, including at final image-forget.
Fixture regressions exercise failures before registry publication and retain
the preexisting canonical manifest/registry and unowned assets.

Final qualifying CI for the code at
[GitHub Actions #38196834096](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38196834096)
**SUCCESS 792/792 Python, 60/60 bounded synthetic tests**, plus Bash,
ShellCheck, Python compilation, whitespace. Two intermediate CI failures
were test-stub representation problems, preserved in
[specific evidence](scripts/benchmark/evidence/managed-uninstall-fail-closed-purge-plan-docker-20261012.md).
The independent [disposable-host E2E plan](docs/DISPOSABLE-LIFECYCLE-E2E-PLAN.md)
is an **acceptance plan, NOT an executed test**.

Current sole DGX checkout was last operator-observed at `87fb463...`, with
56/56 synthetic PASS and service/container intentionally stopped after the
Oct 7 protection-abort sequence; new source not locally synchronized/tested.
`M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`,
`M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`,
`HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`.
Never run destructive lifecycle gates on the sole DGX. PR #259 Draft/Open,
Ready/Merge BLOCKED.


## DGX local synthetic acceptance at exact uninstall-hardening SHA (2026-10-12)

An actual operator-provided DGX terminal log confirms a clean guarded
fast-forward `87fb463 → 02e9c61`, exact checkout
`02e9c61d90c7f15484b0605dc872bbbb21ec253b`, final SHA/worktree
checks, and `DGX_SYNTHETIC_VALIDATION_COMPLETE`. The isolated
`verify-synthetic.sh` tests passed **60/60**:
19 uninstall, 7 asset-ownership, 8 operation-lock, 14 lifecycle integration,
8 selected-profile-readonly and 4 full-readonly-snapshot tests.
`LOCAL_SYNTHETIC_RESULT=PASS`, `BASH_SYNTAX=PASS`,
`LOCAL_SYNTHETIC_SCOPE=DISPOSABLE_FIXTURES_ONLY`, and
`LOCAL_SYNTHETIC_HOST_COMMANDS=PATH_DENY_STUBS` were observed.
Local `SHELLCHECK=SKIPPED_NOT_INSTALLED`; separately
[CI #38197243631](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38197243631)
was **SUCCESS, 792/792 full tests**, **60/60 synthetic**, ShellCheck PASS.
This explicitly upgrades the earlier statement that the uninstall-hardening
code had not been synchronized/tested on the DGX.

See [actual DGX synthetic acceptance evidence](scripts/benchmark/evidence/dgx-synthetic-uninstall-hardening-pass-20261012.md).
The DGX log **does not contain a new live service/Doctor inspection**;
the prior `orcarouter` selected profile and stopped runtime observation
remain historical, not a new readiness claim. Keep
`M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`,
`M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`,
`HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`,
PR #259 Draft/Open and Ready/Merge BLOCKED.

## Full ordered profile-switch pair matrix — synthetic CI (2026-10-12)

Four state-schema profiles (`orcarouter`, `nvidia`, `mazinb`,
`orcarouter-hybrid`) yield **12 distinct ordered profile switches**. The
synthetic transaction suite now checks all 12 for (1) uncommitted
activation recovering exact source manifest, (2) attested target runtime
finalizing target manifest, and (3) mismatched candidate container-ID
attestation refusing commit then allowing provable source rollback.
Same-profile and wrong-source prepares are also refused for all four
starting profiles. Existing interrupted-state and lock fixtures remain.

[CI #38204508012](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38204508012)
**SUCCESS, 796/796 full tests, 70/70 allowlisted synthetic tests** and
Bash, ShellCheck, Python compile and whitespace PASS. The exact-SHA local
synthetic runner now includes the mocked profile-switch test module
(**10 tests**). [Pair matrix evidence](scripts/benchmark/evidence/managed-profile-switch-pair-matrix-synthetic-20261012.md)
records subtest coverage and evidence boundaries. It is **NOT** a true
Docker/systemd profile-switch E2E, and does not qualify M3.

The operator's last actual DGX synthetic run was **60/60 at `02e9c61`**;
this newer pair-matrix source has not been synchronized/run locally on
the DGX. Preserve the stopped runtime/protection, do not run live
profile switches or model starts. `M1_HOST_HEALTH=NOT_QUALIFIED`,
`M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`,
`M4_H38=BLOCKED`, `HOST_STABILITY=INCONCLUSIVE`,
`HOST_PROTECTION=UNCHANGED`; PR #259 Draft/Open and Merge BLOCKED.

## Actual DGX 70/70 directed profile-pair synthetic acceptance — 2026-10-12

The operator supplied a successful exact-SHA guarded DGX fast-forward
`02e9c61 → d2e9a1d` and `verify-synthetic.sh` output proving **70/70
selected synthetic tests PASS**, **Bash syntax PASS**, and final exact clean
checkout `d2e9a1dc2b9759bc60915f2a7cda7b0cfd9d4914`. Breakdown:
19 uninstall + 7 assets + 8 locks + 14 lifecycle integration +
**10 profile-switch transaction** + 8 selected-profile snapshot +
4 lifecycle snapshot. Profile-switch synthetic cases include all 12
ordered pair directions with successful target attestation, uncommitted
rollback, and incorrect container-ID rejection/rollback.

DGX `SHELLCHECK=SKIPPED_NOT_INSTALLED`. Separately
[CI #38204845533](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38204845533)
**SUCCESS**, 796/796 full unit tests, 70/70 selected synthetic and
ShellCheck/Bash/Python/whitespace PASS. The previous 60/60 actual-DGX
local synthetic acceptance at `02e9c61` is superseded as **latest**
local synthetic evidence. See the
[actual-DGX 70/70 evidence](scripts/benchmark/evidence/dgx-profile-pair-synthetic-pass-20261012.md).

This proves neither physical Docker/systemd transition nor readiness,
M1 host health, M2 destructive E2E, M3 actual all-pair qualification or
M4 H38. Selected `orcarouter` and stopped runtime are **historical** read-only
observations, not updated by this test. The current single DGX host's
service/monitor/swap/protection remain untouched. `HOST_STABILITY=INCONCLUSIVE`,
`HOST_PROTECTION=UNCHANGED`; PR #259 DRAFT/OPEN and Ready/Merge BLOCKED.

## New actual DGX 70/70 confirmation and GitHub-only profile-switch drift gates — 2026-10-12

The user-supplied **actual DGX** terminal log confirms exact-SHA
fast-forward `d2e9a1d → fb6e0ed`, final clean checkout
`fb6e0ed4075ac5fa8a3142137d068eb98d65e4bf` and
`verify-synthetic.sh` **70/70 PASS** (7 allowlisted modules including
10 profile-switch tests). The on-host `BASH_SYNTAX=PASS`; local
`SHELLCHECK=SKIPPED_NOT_INSTALLED`. GitHub CI #38207710548 at this
same source had **796/796 full and 70/70 selected PASS**, including
CI ShellCheck, not on-host ShellCheck. This supersedes `d2e9a1d` as
**latest actual DGX locally tested SHA**, without changing host readiness
or previously observed runtime state.

Additionally, GitHub-only source commit `8538c83` added **3
disposable profile-switch fault regressions**: tampered backup SHA
refuses rollback while preserving state; tampered candidate SHA refuses
target commit and can roll back to a provable old runtime; removal of
runtime attestation after a recorded commit refuses finalization until
proof is restored. [CI #38210907792](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38210907792)
**SUCCESS, 799/799 full Python tests, 73/73 synthetic, ShellCheck PASS**.
These 3 cases have **not been run on the actual DGX**.

Evidence: [actual DGX console](scripts/benchmark/evidence/dgx-synthetic-doc-head-pass-20261012.md)
and [manifest/attestation fault injection](scripts/benchmark/evidence/managed-profile-switch-drift-attestation-synthetic-20261012.md).
Neither result qualifies live M1, real D0–D5 M2, all-pairs service M3 or
H38 M4. `HOST_STABILITY=INCONCLUSIVE`,
`HOST_PROTECTION=UNCHANGED`. No model/service/swap/GPU change. PR #259
must remain Draft/Open/Unmerged and Ready/Merge BLOCKED.

## Actual DGX 73/73 and fail-closed profile-switch orphan-state hardening — 2026-10-12

Operator-supplied real DGX output confirms a clean, exact guarded
fast-forward `fb6e0ed → e18c56a` and **73/73 local isolated synthetic
tests PASS**, including **13 profile-switch transaction tests**.
`BASH_SYNTAX=PASS`, local `SHELLCHECK=SKIPPED_NOT_INSTALLED`,
`LOCAL_SYNTHETIC_RESULT=PASS` and final
`DGX_PROFILE_RECOVERY_SYNTHETIC_VALIDATION_COMPLETE` were observed.
Latest actual DGX verified SHA is
`e18c56aff008f717ad54ee787ab20c248e987e34`.

Subsequent GitHub-source-only review found a **false-idle fail-open**:
a dangling transition file link or orphan backup/candidate/staging
artifact could be hidden by the no-state branch of `recover`,
`rollback`, `service-recover` or `status`. The new code refuses to
claim idle while any such file or link remains, preserving normal truly
idle behavior. Three new fixture unittest methods exercise the
dangling/orphan/valid-idle matrix. [Source CI #38212223945](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38212223945)
**SUCCESS 802/802 full Python, 76/76 synthetic**, plus Bash,
ShellCheck, compile and whitespace PASS. **This new source is not yet
executed locally on the DGX.**

[Evidence details](scripts/benchmark/evidence/dgx-73-and-profile-switch-false-idle-hardening-20261012.md).
No live host E2E, Docker/systemd profile changes or H38 reruns.
`M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`,
`M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`,
`HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`,
PR #259 Draft/Open, Ready/Merge BLOCKED.


## New actual DGX 76/76 synthetic acceptance and prepare fail-closed check — 2026-10-12

A newly supplied DGX console transcript confirms exact guarded fast-forward `e18c56a → 9220624` and **76/76 local isolated synthetic methods PASS** on `922062436b71353760c2323103e749ed6eaf6240`, including 16 profile-switch methods. `BASH_SYNTAX=PASS`, local `SHELLCHECK=SKIPPED_NOT_INSTALLED`, clean exact HEAD and worktree, `LOCAL_SYNTHETIC_RESULT=PASS` and final `DGX_PROFILE_IDLE_SAFETY_SYNTHETIC_COMPLETE` were observed. The matching GitHub [CI #38212708550](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38212708550) passed 802/802 full and 76/76 synthetic tests plus ShellCheck. This **supersedes 73/73 as the latest actual DGX local synthetic**, not as any live host qualification.

A subsequent safety review found that `prepare` did not apply the existing orphan `.tmp` fail-closed check used by idle/recovery actions. The source now applies the shared guard before publishing a new transaction, with a new seven-scenario (six artifacts and one dangling symlink) fixture regression method. **The new source change was not part of the completed DGX 76/76 run.** [New-source CI #38215072213](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215072213) **SUCCESS 803/803 full tests, 77/77 bounded synthetic (17 profile-switch), ShellCheck/Bash/compile/whitespace PASS** at `51e85f6578ee0694a13964f700f30e854f17c020`. This new source has not been tested on DGX.

[New DGX and source review evidence](scripts/benchmark/evidence/dgx-76-and-prepare-orphan-guard-20261012.md). Actual Docker/systemd E2E, M1/M2/M3/M4 gates and host protection are unchanged: `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`; PR #259 stays Draft/Open, Ready/Merge BLOCKED.


## Actual DGX 77/77 profile-switch prepare guard acceptance — 2026-10-12

New operator-provided console evidence confirms guarded fast-forward `9220624 → 1283b1a` and **77/77 isolated local synthetic tests PASS** on exact DGX checkout `1283b1a9252f1ff53d51659049ca42f9449e5ccd`, including **17/17 profile-switch tests** and the new `prepare` orphan-staging preservation regression. Exact final HEAD, `LOCAL_SYNTHETIC_RESULT=PASS` and `DGX_PREPARE_ORPHAN_SYNTHETIC_COMPLETE` were observed. Bash syntax PASS; **local ShellCheck SKIPPED_NOT_INSTALLED**, distinct from [GitHub CI #38215504822](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215504822) **SUCCESS 803/803 full and 77/77 synthetic, ShellCheck PASS**.

[Canonical 77/77 operator evidence](scripts/benchmark/evidence/dgx-77-prepare-orphan-synthetic-pass-20261012.md). This updates the latest *DGX-local isolated synthetic* source from `9220624` (76/76) to `1283b1a` (77/77), **not** any real Docker/systemd/model acceptance. `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`. PR #259 remains Draft/Open/Unmerged and Ready/Merge BLOCKED; no protected DGX runtime mutation.


## Disposable D0 offline evidence precheck — code staged, not host-qualified (2026-10-12)

A new **offline-only** reviewer, `disposable-d0-preflight.py`, validates two
explicit operator-provided JSON files using Python stdlib only. It never reads
live Docker, systemd, host identity, Git or model state; it never runs commands
on any host. Required policy: exact SHA and repository, **nonempty protected
machine-id hash and Docker daemon denysets**, forbidden production roots.
Required inventory: separately identified disposable machine/daemon, clean
exact SHA + origin, owner disposable declaration, restore point, isolated
non-default Docker context without external users, nonoverlapping throwaway
model/log/work roots, bounded owned synthetic model, non-production service
unit, and no pending lifecycle transactions.

Run **only against an independently assembled, reviewed inventory**:
`python3 scripts/lifecycle/disposable-d0-preflight.py --policy <policy.json> --inventory <inventory.json>`.
No real protected machine IDs, daemon IDs, credentials or private mount
inventories belong in Git history or CI logs. Inputs are treated as
**untrusted assertions**: success prints
`D0_STATIC_REVIEW=READY_FOR_INDEPENDENT_REVIEW` but always
`D0_ADMISSION=NOT_GRANTED` and `D0_LIVE_E2E=NOT_AUTHORIZED`.
Any incomplete/mismatched evidence fails closed with exit 2. A passing
offline check is **not** permission for D1–D5; independent operator
attestation, read-only on-host cross-check and explicit disposable-host
authorization remain mandatory. Neither current DGX nor M1/M2/M3/M4
qualification is changed.


### D0 offline evidence policy CI acceptance (2026-10-12)

Source `7acd15cc5a2d8f5603bdb82b08b1cee49da7d18a` introduced a stdlib-only JSON D0 policy evaluator and nine fixture regressions. [GitHub CI #38217170909](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38217170909) **SUCCESS 812/812 full tests, 77/77 existing bounded synthetic**, Bash syntax, ShellCheck, Python compile, whitespace PASS. The D0 test methods are **not** yet in the bounded DGX verifier; latest DGX actual local run remains `1283b1a` **77/77**. A policy-consistent response is `D0_STATIC_REVIEW=READY_FOR_INDEPENDENT_REVIEW` with `D0_ADMISSION=NOT_GRANTED`; it is not live host attestation or D0 acceptance. [Permanent source/limitation evidence](scripts/benchmark/evidence/disposable-d0-offline-preflight-ci-20261012.md). M1/M2/M3/M4 remain NOT_QUALIFIED/NOT_RUN/BLOCKED and PR #259 stays Draft/Open/Unmerged.


## D0 independent-host on-host read-only cross-check (source only; 2026-10-12)

A new conservative `disposable-d0-readonly-crosscheck.py` requires the
`--ack-independent-disposable-host` flag plus the existing strict
`--policy` and `--inventory` JSON. The **sole protected DGX is not a
permitted target**. It first validates the offline D0 policy and compares a
hashed real machine identity against the inventory and protected denyset
**before** any Docker/systemd calls. It then performs bounded read-only
Git HEAD/origin/worktree, candidate path realpath and mountpoint, Docker
context/daemon/empty-container, and dedicated disposable service-unit checks.

The collector does not probe without the explicit independent-host
acknowledgement, does not ask for sudo, does not modify files or host
configuration, and never installs/uninstalls or starts models. Its JSON
output excludes raw host identities, secrets, mounts and container IDs.
The output is `ON_HOST_READ_ONLY_ASSERTION_CROSSCHECK`, with
`d0_admission=NOT_GRANTED` and `d1_d5=NOT_AUTHORIZED` **even after
all observed fields match**. A missing daemon, unknown service response,
realpath/mount drift, protected identity or unclean Git state fails closed.

This cross-check **does not independently prove** owner consent, absence of
external Docker users, isolation of the underlying daemon, mount sources
outside the selected roots, or restoration/snapshot viability. Independent
D0 trust review and explicit authorization remain necessary. Current status:
**source and fixture tests only; not executed on any physical disposable
host or the protected DGX; M1–M4 and D1–D5 unchanged**.


## D0 independent-host read-only crosscheck — GitHub source CI (2026-10-12)

The new on-host read-only D0 cross-check source was implemented at `b6d3188`. Its first [CI #38218386709](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38218386709) **FAILED 1 of 824 full tests**, because a Docker-outage *fixture* used an `AssertionError` instead of subprocess-style `OSError`. The test fake was corrected without relaxing safety guards. [Source CI #38218663210](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38218663210) **SUCCESS 824/824 full Python, 77/77 existing bounded synthetic**, Bash/ShellCheck/Python compile/whitespace PASS at `b99b510e89cc08d99d683dcbf77c75bb55941b2c`.

The 12 new fixture cases cover protected host/daemon identities, clean Git source, path and mount drift, Docker outage/contamination and nonexclusive service refusal. No actual Docker/systemd on a disposable host was inspected; the collector is **not approved for the sole protected DGX**. Its on-host result always keeps `d0_admission=NOT_GRANTED` and `d1_d5=NOT_AUTHORIZED`, even when supplied host observations match. [Permanent evidence and trust limitations](scripts/benchmark/evidence/d0-onhost-readonly-crosscheck-ci-20261012.md). Latest *actual DGX local* isolated synthetic remains 77/77 at `1283b1a`. D0 independent real-host review and D1–D5 remain NOT_RUN; M1/M2/M3/M4, strict host protections and PR #259 Draft/Open/Unmerged are unchanged.


## D0 parent-mount and Docker-endpoint fail-closed refinement (2026-10-12)

The source-only read-only host observer now rejects **non-root ancestor mounts** overlapping proposed disposable roots, Docker environment overrides, TCP/SSH and default/shared Unix socket endpoints, aliased/missing sockets, and refuses to use an implicit Docker context for daemon reads. Git command probes set `GIT_OPTIONAL_LOCKS=0` to avoid optional Git index refresh. The four trust-boundary fixture methods and one Git no-optional-locks method extend the read-only D0 module to **17/17 synthetic tests**.

[CI #38266470002](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38266470002) at `4dfc2aed238ce96be0b5f3970256b8a2ce8cadf8` **SUCCESS 828/828 full, 77/77 selected**, and [CI #38267015272](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38267015272) at `b65c0142340d90d681c8f82d05294bb72d813687` **SUCCESS 829/829 full, 77/77 selected** plus Bash/ShellCheck/Python compile/whitespace PASS. [Canonical source evidence](scripts/benchmark/evidence/d0-parent-mount-docker-endpoint-guards-20261012.md) explains remaining host-attestation gaps. The latest *actual DGX-local* isolated result remains **77/77 at `1283b1a`**. This source has not been run on either actual DGX or independent disposable host. D0 `NOT_GRANTED`; D1–D5 `NOT_RUN`; M1/M2/M3/M4 unchanged; PR #259 Draft/Open/Unmerged, Ready/Merge BLOCKED.


## D0 read-only command environment and protected-socket refusal (2026-10-13)

Source `f4e83d2ae3f17d82c5f7702497138c3431072358` hardens the on-host D0 read-only observer against redirected Git/Systemd/DBus environment selectors; removes unpinned default Docker info/container commands from the allowlist; refuses arbitrary populated Docker environment overrides; and blocks context endpoints inside forbidden production roots or on/under non-root mountpoints. `GIT_OPTIONAL_LOCKS=0` remains enforced. Five new fixture methods confirm refusal before unintended host commands. [GitHub CI #38315552300](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38315552300) **SUCCESS 834/834 full Python, 77/77 existing selected synthetic, 22/22 D0 crosscheck fixtures, ShellCheck/Bash/Python compile/whitespace PASS**.

[Permanent D0 environment and socket-source evidence](scripts/benchmark/evidence/d0-env-redirection-and-socket-boundaries-20261013.md) records provenance, safety rationale and remaining host-attestation gaps. The **latest actual DGX-local** isolated synthetic result remains **77/77 at `1283b1a`**, not the newer GitHub source. No actual independent disposable host observation or live D0 qualification occurred. `D0_LIVE_ADMISSION=NOT_GRANTED`, `D1_D5=NOT_RUN`, M1/M2/M3/M4 unchanged, and PR #259 Draft/Open/Unmerged with Ready/Merge BLOCKED.


## D0 exact-input digest receipts and offline consistency review (2026-10-13)

At source SHA `e41a34f06887f526d0a7ac7cb605d263c226f8f6`, the strict JSON reader hashes the **same bounded no-symlink file-descriptor bytes it parsed**, the read-only host collector emits `policy_sha256` and `inventory_sha256`, and the new `disposable-d0-receipt-review.py` compares its receipt to the exact supplied policy/inventory JSON. Mismatched files, invalid receipt schema, changed Git SHA and forged admission markers are refused. Consistent input is only `D0_RECEIPT_REVIEW=CONSISTENT_UNTRUSTED`; external attestation and replay freshness remain `NOT_VERIFIED`.

[Source CI #38316973840](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38316973840) **SUCCESS: 845/845 full Python, 77/77 bounded synthetic, Bash/ShellCheck/Python compile/whitespace PASS**. [Permanent fixture evidence](scripts/benchmark/evidence/d0-receipt-input-binding-ci-20261013.md) and [receipt workflow/limitations](docs/D0-RECEIPT-CHAIN.md) preserve provenance and non-admission semantics. The new 11 tests are **outside** the 77-case bounded DGX synthetic verifier; latest **actual DGX-local** synthetic remains **77/77 at `1283b1a`**. No actual disposable host observation occurred; D0 admission NOT_GRANTED, D1–D5 NOT_RUN, M1/M2/M3/M4 remain unqualified/blocked, PR #259 remains Draft/Open/Unmerged.
