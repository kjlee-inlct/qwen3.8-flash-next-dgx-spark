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
