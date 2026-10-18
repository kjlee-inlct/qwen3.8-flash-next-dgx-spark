# 2026-10-17 actual DGX existing-image PLE audit: expected file path not found

**Evidence class:** operator-supplied ACTUAL_DGX read-only Wizard output,
not independent assistant execution. Source checkout SHA at the time,
exact Docker image ID, mounted file origin, container ID, full Docker CLI
stderr and host evidence-file checksum: **NOT_CAPTURED**. Do not infer
these details from branch commits, earlier host inspections or expected
build paths.

## Actual result

The operator selected the candidate metadata Wizard option
**3 → 7 → 4**, `Existing image PLE loader source (read-only)`.
The visible output was:

```text
PLE_IMAGE_AUDIT=INCONCLUSIVE: No known PLE loader path in existing matching container
DOCKER_MUTATION=NONE
GPU_RUN=NOT_PERFORMED
Installed image source is INCONCLUSIVE or unavailable; NO managed resources were changed.
lychee888 remains NOT installable. Runtime adapter and memory admission are still blocked.
```

Unlike the previous audit's broad vLLM mount conflict, this time
the existing-image and managed-container identity checks progressed
past validation. No source was attested at the original inspector's
eight fixed `/usr/local/lib/python3.{10,11,12,13}/{dist,site}-packages/vllm/models/qwen3_8_flash_next/nvidia/ple_layer.py`
candidates. **This is not evidence that the container has no PLE
implementation**, or that the checkpoint failed to load; a package
layout variant, different source module, absent file or Docker
copy-layer limitation remain possible. The original error does not
identify which of these applies.

## Source-only follow-up

The existing read-only `audit_installed_ple_image.py` module
now retains the conservative `INCONCLUSIVE` outcome, but also reports
the validated existing image and container IDs, number of fixed
candidate paths checked (expanded to Python 3.14/3.15), and a
bounded read-only Docker-copy probe for
`qwen3_8_flash_next/nvidia/low_latency_gemm.py`. This is an
appropriate control because the pinned source Dockerfile
`scripts/Dockerfile.skinny-gemm` explicitly asserts existence of
that low-latency file during build. A successful *sentinel* copy is
only evidence of the image package-path layout, **not** evidence that
`ple_layer.py` exists, that its loader selected FP8 or that
lychee888 TP=1 would fit GB10.

No container creation/start/exec, image build/pull, weight payload
access, GPU run, service change or installed model mutation is
performed by this follow-up. The expanded diagnostic is
**SOURCE/CI ONLY** until the owner synchronizes it and supplies
another physical `3 → 7 → 4` output. If the sentinel is also
unavailable, stop: do not infer compatibility or restart Docker.

## Follow-up physical DGX fixed-path + sentinel diagnostics (owner output)

A later same-day Wizard **3 → 7 → 4** read-only run captured two
verified Docker identities, 12 PLE candidates and the small
skinny-GEMM sentinel. The exact Git checkout HEAD at that host
invocation was not supplied. The following lines are transcribed
from the operator's terminal output:

```text
PLE_DIAGNOSTIC_IMAGE_ID=sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4
PLE_DIAGNOSTIC_MANAGED_CONTAINER_ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24
PLE_DIAGNOSTIC_PLE_CANDIDATES_CHECKED=12
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_STATE=SKINNY_GEMM_REFERENCE_UNAVAILABLE
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_PATH=NOT_CAPTURED
PLE_DIAGNOSTIC_PLE_SOURCE_FILE=NOT_CAPTURED
PLE_IMAGE_AUDIT=INCONCLUSIVE: No known PLE loader path in existing matching container
DOCKER_MUTATION=NONE
GPU_RUN=NOT_PERFORMED
```

**Interpretation:** image/container identity consistency was checked
by the inspector. Neither the PLE source nor the originally
skinny-GEMM-asserted build-reference file was available through
the fixed `docker cp` candidate paths. The earlier mount policy
blocker did not recur in this output. This result does **not** prove
either image-internal files are absent: the prior inspector discarded
per-copy subprocess exit-status and stderr details. It also does not
prove the Docker copy transport works. No Python source SHA,
live import, tensor/header verification, or model execution occurred.

**Next SOURCE/CI-only diagnostic:** classify each copy error using
an allowlisted reason vocabulary, never raw stderr or host paths,
and read only a small pre-existing non-model `/etc/group` file
as a Docker-copy transport control (parsed as a bounded TAR in
memory; file bytes are not printed or written). This separates
copy-system failure from a PLE package path issue without creating,
starting or executing any container, or accessing model weights.
The actual physical outcome of the new transport check is
`NOT_CAPTURED` until a future operator run.

## Follow-up: all Docker copies returned an unclassified failure

The latest supplied physical Wizard **3 → 7 → 4** output on
2026-10-17 showed the same immutable local image/container IDs
as above, no new PLE source, and:

```text
PLE_DIAGNOSTIC_PLE_CANDIDATES_CHECKED=12
PLE_DIAGNOSTIC_DOCKER_CP_PLE_FAILURE_KINDS=COPY_FAILED_UNCLASSIFIED:12
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_STATE=SKINNY_GEMM_REFERENCE_UNAVAILABLE
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_FAILURE_KINDS=COPY_FAILED_UNCLASSIFIED:12
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_PATH=NOT_CAPTURED
PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_STATE=COPY_FAILED_UNCLASSIFIED
PLE_DIAGNOSTIC_PLE_SOURCE_FILE=NOT_CAPTURED
PLE_IMAGE_AUDIT=INCONCLUSIVE: No known PLE loader path in existing matching container
DOCKER_MUTATION=NONE
GPU_RUN=NOT_PERFORMED
```

**Evidence-based interpretation:** all 24 targeted PLE and skinny
GEMM file copy requests, **plus one** generic small
`/etc/group` Docker-copy control, failed under the same
`COPY_FAILED_UNCLASSIFIED` category. Thus current evidence
implicates the **shared copy mechanism/container filesystem
access** before any claim that a particular vLLM module is
absent. This result does not establish the exact root cause;
the old classification discarded Docker CLI exit status and
subprocess stderr beyond a narrow keyword dictionary.
Actual container runtime status is also **NOT_CAPTURED**.
No Docker image, model payload, runtime process, or managed
resource was modified by the checker.

The SOURCE-only remediation records only the existing
container's allowlisted state (`created/running/exited/paused`,
etc.), bounded exit code, stderr byte length, and a
fixed vocabulary of Docker error feature flags from the
single `/etc/group` transport control. This never prints
raw stderr, filesystem paths, credentials or file bytes.
The operator uses the existing read-only Wizard route
after the new source CI succeeds. Actual findings for
this new failure-detail probe are **NOT_CAPTURED**.

## Latest 2026-10-17 actual DGX: copy blocked by read-only filesystem

Operator repeated read-only Wizard **3 → 7 → 4**. The inspector
verified the same image and managed container identities, now
captured `State.Status=exited` and classified all attempted
Docker-copy requests as `FILESYSTEM_READ_ONLY`:

```text
PLE_DIAGNOSTIC_IMAGE_ID=sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4
PLE_DIAGNOSTIC_MANAGED_CONTAINER_ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24
PLE_DIAGNOSTIC_CONTAINER_STATE=exited
PLE_DIAGNOSTIC_PLE_CANDIDATES_CHECKED=12
PLE_DIAGNOSTIC_DOCKER_CP_PLE_FAILURE_KINDS=FILESYSTEM_READ_ONLY:12
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_STATE=SKINNY_GEMM_REFERENCE_UNAVAILABLE
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_FAILURE_KINDS=FILESYSTEM_READ_ONLY:12
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_PATH=NOT_CAPTURED
PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_EXIT_CODE=1
PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_STDERR_BYTES=76
PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_STDERR_SIGNALS=DOCKER_DAEMON_REPLY,FILESYSTEM
PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_STATE=FILESYSTEM_READ_ONLY
PLE_DIAGNOSTIC_PLE_SOURCE_FILE=NOT_CAPTURED
PLE_IMAGE_AUDIT=INCONCLUSIVE: No known PLE loader path in existing matching container
DOCKER_MUTATION=NONE
GPU_RUN=NOT_PERFORMED
```

**Conclusion:** a common Docker daemon-side read-only filesystem
error blocks all twenty-five copy requests, including a generic
`/etc/group` control file. The error is not evidence of missing
PLE modules, model incompatibility or corrupt checkpoint data.
Docker supports copying from stopped containers in general, so
`exited` alone is not an explanation. Docker's
`HostConfig.ReadonlyRootfs` for this container and the full 76-byte
Docker stderr **were not shown**; therefore the exact source of
the read-only restriction (container rootfs setting versus daemon
storage/mount state) remains unresolved. No inference about the
host root partition or need to remount is permitted.

**Repository SOURCE-only response:** inspect the existing
`HostConfig.ReadonlyRootfs` value without changing it, test the
generic small-file transport first, and when it returns
`FILESYSTEM_READ_ONLY` or `CONTAINER_ROOTFS_READ_ONLY`,
abort **before** attempting the remaining 24 targeted copies.
No container start, `docker exec`, `docker cp` into a file,
host remount, Docker restart or protected asset mutation is
authorized by this diagnostic. Exact physical outcome of this
new early-stop version is **NOT_CAPTURED**.


## 2026-10-17 — physical DGX single-copy preflight and early-stop result (owner supplied)

The operator reran read-only Wizard **3 → 7 → 4** on the actual DGX.
The visible output below is operator-supplied **ACTUAL_DGX** evidence,
not a GitHub CI result or independently run assistant command. The
exact on-host checkout SHA, full Docker CLI stderr, storage-driver
condition and PLE source bytes remain **NOT_CAPTURED**.

```text
PLE_DIAGNOSTIC_IMAGE_ID=sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4
PLE_DIAGNOSTIC_MANAGED_CONTAINER_ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24
PLE_DIAGNOSTIC_CONTAINER_STATE=exited
PLE_DIAGNOSTIC_CONTAINER_READONLY_ROOTFS=FALSE
PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_EXIT_CODE=1
PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_STDERR_BYTES=76
PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_STDERR_SIGNALS=DOCKER_DAEMON_REPLY,FILESYSTEM
PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_STATE=FILESYSTEM_READ_ONLY
PLE_DIAGNOSTIC_PLE_CANDIDATES_CHECKED=0
PLE_DIAGNOSTIC_DOCKER_CP_PLE_FAILURE_KINDS=NOT_ATTEMPTED_PRECHECK_BLOCK
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_STATE=NOT_ATTEMPTED_PRECHECK_BLOCK
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_FAILURE_KINDS=NOT_ATTEMPTED_PRECHECK_BLOCK
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_PATH=NOT_CAPTURED
PLE_DIAGNOSTIC_PLE_SOURCE_FILE=NOT_CAPTURED
PLE_IMAGE_AUDIT=INCONCLUSIVE: Docker cp transport read-only; source files NOT TESTED
DOCKER_MUTATION=NONE
GPU_RUN=NOT_PERFORMED
```

**Verified limited conclusion:** the newly implemented single
`/etc/group` copy-transport preflight ran on the existing matched
image/container and correctly stopped the 24 targeted PLE/GEMM copy
attempts. `HostConfig.ReadonlyRootfs=FALSE` excludes a configured
readonly rootfs as a directly observed property, **not** all Docker
snapshotter/storage/mount problems. A daemon-side filesystem read-only
error remains the immediate copy-transport blocker. `exited` is not
by itself a Docker-copy failure cause. PLE paths and the actual
FP8/BF16 scale implementation are **NOT TESTED**, not absent;
single GB10 TP=1 admission, model download and GPU run remain blocked.

**Next safe evidence:** without restarting Docker or touching protected
assets, obtain the exact short stderr from one existing-container
`docker cp qwen38-flash-next:/etc/group - >/dev/null` invocation,
reviewing it locally for sensitive paths before sharing. If still
ambiguous, plan bounded read-only Docker storage/host mount metadata
checks separately. Do not remount, restart, run the container, build
an image, or elevate the model to installable on this evidence.

## 2026-10-17 — ACTUAL_DGX exact Docker daemon stderr and checkout SHA

The owner supplied the following **actual DGX terminal output** after
the earlier preflight result (no image, container or model mutation):

```text
$ git -C ~/Workspace/llm/qwen3.8-flash-next-dgx-spark rev-parse HEAD
7c93e4db2efd37d0bdc4f2f40748b1fe23d5f360
$ docker cp qwen38-flash-next:/etc/group - >/dev/null
Error response from daemon: openat model/config.json: read-only file system
DOCKER_CP_EXIT=1
```

This exact checkout SHA is attested **at the command invocation**, not
retroactively for all earlier Wizard outputs. An unrelated
`/etc/group` copy fails during daemon access to
`model/config.json`, a path neither requested nor printed by the
sanitized inspector. This is a **strong clue for a nested mount /
archive filesystem-view error**, not proof that the model config,
checkpoint or the host rootfs is read-only or corrupt. The existing
project `serve.sh` has two nested read-only bind arguments:
`/model:ro` and `/model/config.json:ro` when a config override
is configured. The exact **physical container Mounts inventory** and
Docker Engine version remain NOT_CAPTURED.

An independent Moby change on 2026-09-17,
[moby/moby commit 7420e624](https://github.com/moby/moby/commit/7420e6240935b25644155447a3197a25af703d35),
fixes `docker cp` handling of overlapping nested bind mounts by
avoiding opening an already-existing inner target for writing. The
specific upstream reproducer has a different error code/path, so this
is a matching failure **mechanism candidate**, not a confirmed diagnosis
of the installed daemon version.

**Next physical evidence:** read-only inspect of the protected
container's exact `/model` and `/model/config.json` mount
type/RW fields, plus Docker server version; emit no host bind
source paths. Do not restart Docker, change mount settings, create
new containers, modify the model, or claim FP8-PLE qualification.

## 2026-10-17 — ACTUAL_DGX nested read-only model/config mounts confirmed at cee107d

The operator cleanly fast-forwarded the checkout
`feature/wizard-modular-phase1-20261014` from
`7c93e4db2efd37d0bdc4f2f40748b1fe23d5f360` to
`cee107d9e47b278d7dede40a8d401ea9c2ccea32`, verified
`git rev-parse HEAD`, then ran the **actual DGX**
read-only Wizard **3 → 7 → 4**. Output was:

```text
PLE_DIAGNOSTIC_IMAGE_ID=sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4
PLE_DIAGNOSTIC_MANAGED_CONTAINER_ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24
PLE_DIAGNOSTIC_CONTAINER_STATE=exited
PLE_DIAGNOSTIC_CONTAINER_READONLY_ROOTFS=FALSE
PLE_DIAGNOSTIC_DOCKER_CP_MODEL_CONFIG_MOUNT_TOPOLOGY=MODEL_CONFIG_NESTED_RO_BINDS
PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_EXIT_CODE=1
PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_STDERR_BYTES=76
PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_STDERR_SIGNALS=DOCKER_DAEMON_REPLY,FILESYSTEM
PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_STATE=FILESYSTEM_READ_ONLY
PLE_DIAGNOSTIC_PLE_CANDIDATES_CHECKED=0
PLE_DIAGNOSTIC_DOCKER_CP_PLE_FAILURE_KINDS=NOT_ATTEMPTED_PRECHECK_BLOCK
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_STATE=NOT_ATTEMPTED_PRECHECK_BLOCK
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_FAILURE_KINDS=NOT_ATTEMPTED_PRECHECK_BLOCK
PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_PATH=NOT_CAPTURED
PLE_DIAGNOSTIC_PLE_SOURCE_FILE=NOT_CAPTURED
PLE_IMAGE_AUDIT=INCONCLUSIVE: Docker cp transport read-only; source files NOT TESTED
DOCKER_MUTATION=NONE
GPU_RUN=NOT_PERFORMED
```

**Verified on physical DGX:** using the previously matched immutable
Docker IDs, the inspector read the protected container's existing
`Mounts` metadata and found **one read-only bind at
`/model` and one read-only bind at `/model/config.json`**.
The Docker `ReadonlyRootfs` flag is `FALSE`. The generic
`/etc/group` `docker cp` still fails with
`FILESYSTEM_READ_ONLY` (exit 1); the 24 PLE/GEMM file probes
were deliberately NOT ATTEMPTED. No model source was read,
no GPU was run, and the tool reported no Docker mutation.

Together with the earlier **exact** daemon stderr
`openat model/config.json: read-only file system` for the unrelated
`/etc/group` request, this is strong, directly supported evidence
of a **nested-readonly-bind Docker copy failure mechanism**.
Upstream Moby's September 2026
[overlapping-bind Docker-copy fix](https://github.com/moby/moby/commit/7420e6240935b25644155447a3197a25af703d35)
is relevant supporting SOURCE evidence, not proof of the
installed engine's affected code/version. The Docker **server**
version and direct patch applicability remain **NOT_CAPTURED**.
Do not claim lychee888 FP8-PLE compatibility, image-source presence
or whole-host filesystem failure.

**Next bounded read-only diagnostic:** obtain only
`docker version --format '{{.Server.Version}}'`, plus optionally
`docker version --format '{{.Server.APIVersion}}'` if necessary,
without changing Docker mounts, rebuilding/recreating containers,
restarting services, or downloading/loading weights.

## 2026-10-17 — ACTUAL_DGX Docker Engine 29.6.2 overlay2 verified

Owner supplied the actual DGX read-only host inspection:

```text
=== Docker Engine ===
SERVER_VERSION=29.6.2
SERVER_API=1.55
=== Docker storage ===
STORAGE_DRIVER=overlay2
```

This is **ACTUAL_DGX server metadata**, not a GPU or Docker filesystem
mutation and not proof of image or PLE loader compatibility.

**Independent exact upstream source comparison (SOURCE_REVIEW, not
physical binary disassembly):**

- Official Moby `docker-v29.6.2` `daemon/containerfs_linux.go`
  calls `root.Open(relDest)` for a replayed mount target and
  `root.OpenFile(unsafePath, os.O_CREATE|os.O_WRONLY, 0o755)`
  inside `createIfNotExists`.
- Official Moby `docker-v29.8.2` replaces those operations with
  `root.OpenFile(relDest, unix.O_PATH, 0)` and
  `root.OpenFile(unsafePath, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o755)`
  (existing targets are left alone on `EEXIST`).
- Docker's [29.8.2 release notes](https://docs.docker.com/engine/release-notes/29/)
  dated **2026-09-30** explicitly list a nested-bind-mount
  `docker cp` fix linked to
  [moby/moby#53724](https://github.com/moby/moby/pull/53724).
  The earlier [Moby commit 7420e624](https://github.com/moby/moby/commit/7420e6240935b25644155447a3197a25af703d35)
  documents the faulty write-open/replay mechanism.

The actual `29.6.2` server version **precedes the upstream
fix**. In conjunction with the confirmed nested read-only
`/model` / `/model/config.json` mounts and the
`openat model/config.json: read-only file system` error while
copying `/etc/group`, the original upstream defect is a
**high-confidence cause hypothesis**. `overlay2` alone
does not prove storage-driver corruption. A distributor-specific
backport or binary patch was not investigated; do not claim
verified daemon build provenance or directly established stack trace.
The exact effective PLE loader remains NOT_CAPTURED and
`lychee888` remains NOT installable.

**Next nonmutating feasibility checks:** bound the installed
image's declared `Size` and enumerate existing stopped containers
matching the **same immutable image ID**; if none can be proven to
expose an unshadowed source path, stop and plan another reviewed
read-only strategy. A `docker image save` may stream a large
archive and is NOT automatically authorized just because it
does not create a container. No Docker upgrade/restart, image
rebuild, container create/start, weight download, or GPU run.

## 2026-10-17 — ACTUAL_DGX exact image-size and ancestor-filter container inventory

The owner reported the following **read-only actual DGX outputs**;
the checkout HEAD at this *particular* invocation was not printed.
Do not retroactively attach the preceding verified `cee107d` SHA
or infer a container's immutable image ID from its displayed tag.

```text
=== Exact image identity and size ===
IMAGE_ID=sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4 IMAGE_SIZE_BYTES=20629141958
=== Existing image-related containers ===
ID=57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56 IMAGE=vllm-skinny-tp1:v1 STATUS=Exited (137) 4 days ago NAME=qwen38-ab-legacy
ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24 IMAGE=vllm-skinny-tp1:v1 STATUS=Exited (0) 10 days ago NAME=qwen38-flash-next
```

**Physical finding:** the installed reference image is
20,629,141,958 bytes (about 19.21 GiB), much too large to
make an unplanned `docker image save` a low-impact source
probe. The `docker ps -a --filter ancestor=...` query returned
**two existing stopped containers**, including historical
A/B object `qwen38-ab-legacy`. The `ancestor` filter and
displayed `IMAGE` field are **not an immutable image identity
assertion**; the legacy container's actual `.Image` digest,
`.HostConfig.ReadonlyRootfs`, mount topology and any vLLM
source-path shadowing remain **NOT_CAPTURED**. Its historical
exit 137 is not a reason to restart it and not proof of
source compatibility.

**Next bounded read-only differentiation:** inspect only
`qwen38-ab-legacy` using Docker `container inspect`.
Print exact `Id`, `Image` digest, `State.Status`,
`HostConfig.ReadonlyRootfs`, and mount destination/type/RW
(no `Mounts[].Source`, labels, environment, model contents).
Do not call `docker cp` on this alternate until immutable
identity and absence of problematic nested bind mounts have
been validated. Even successful source copy from a distinct
existing container would be **container-filesystem evidence**,
not automatic image-layer or managed runtime attestation.
Preserve the historical A/B container, managed container,
image, checkpoint, and all PR protection boundaries.

## 2026-10-17 — ACTUAL_DGX legacy exact digest and matching nested config binds

The owner performed **read-only Docker inspect** of the historical A/B
container `qwen38-ab-legacy`, and supplied the actual DGX output:

```text
CONTAINER_ID=57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56
IMAGE_ID=sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4
IMAGE_TAG=vllm-skinny-tp1:v1
STATE=exited
ROOTFS_READONLY=false
MOUNT_DEST=/model TYPE=bind RW=false
MOUNT_DEST=/model/config.json TYPE=bind RW=false
MOUNT_DEST=/root/.cache/flashinfer TYPE=bind RW=true
MOUNT_DEST=/root/.cache/vllm TYPE=bind RW=true
```

**New ACTUAL_DGX proof:** the legacy container references the
**same exact immutable image ID** as the managed container, and
has the same `/model:ro` with nested
`/model/config.json:ro` bind configuration. Both rootfs flags
are false and both containers are stopped. Its cache bind mounts
have no proven bearing on PLE loader source access. No
Docker-copy test on the legacy container was performed.

**Decision:** the existing alternate container does **not**
remove the known nested-bind precondition for the Docker
29.6.2 copy-path defect. It is **not a qualified workaround**
for extracting the existing PLE source. Do not try repeated
`docker cp` attempts on historical or managed containers
merely to repeat the known failure. Do not relabel either
container or create a replacement.

Potential future methods require separate safety review:
a bounded **source-only** comparison against a pinned external
upstream tree can proceed without claiming it is the actual
installed-image source; accessing immutable local image layer
bytes via `docker save` or Docker's internal layer store
would need an explicit bounded resource/ownership/read-only
plan first (image declared size ~20.63 GB; no blind bulk
export, root filesystem traversal, host mount or daemon
restart). Actual `ple_layer.py` SHA and runtime loader
remain `NOT_CAPTURED` and `NOT_QUALIFIED`.

## 2026-10-18 — ACTUAL_DGX isolated source planner exact-SHA preview

**Evidence provenance:** owner-supplied physical DGX terminal output,
read-only code sync followed by read-only Docker inspect; not
independently executed by the assistant, and not a CI/GPU result.
The operator verified clean branch
`feature/wizard-modular-phase1-20261014`,
fast-forwarded from `cee107d` to exact
`769332111dc4cdfa13e9817544b9166402985f66`,
stopped on SHA mismatch, and ran the maintained
`audit_installed_ple_image.py --plan-isolated-source` command:

```text
PLE_SOURCE_PLAN_IMAGE_ID=sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4
PLE_SOURCE_PLAN_IMAGE_SIZE_BYTES=20629141958
PLE_SOURCE_PLAN_MANAGED_MOUNT_TOPOLOGY=MODEL_CONFIG_NESTED_RO_BINDS
PLE_SOURCE_PLAN_LEGACY_MOUNT_TOPOLOGY=MODEL_CONFIG_NESTED_RO_BINDS
PLE_SOURCE_PLAN_DECLARED_IMAGE_VOLUMES=NONE
PLE_SOURCE_PLAN_EXISTING_CONTAINER_COPY_ROUTE=BLOCKED_SAME_NESTED_RO_MOUNTS
PLE_SOURCE_PLAN_ISOLATED_CREATE_ONLY_FEASIBILITY=REVIEW_CANDIDATE_NOT_AUTHORIZED
PLE_SOURCE_PLAN_SOURCE_BYTES_CAPTURED=NO
PLE_SOURCE_PLAN_DOCKER_INSPECT_REQUESTS=3
PLE_SOURCE_PLAN_DOCKER_CP_REQUESTS=0
PLE_SOURCE_PLAN_DOCKER_MUTATION=NONE
PLE_SOURCE_PLAN_GPU_RUN=NOT_PERFORMED
PLE_SOURCE_PLAN_LYCHEE888_TP1_LOADER=NOT_QUALIFIED
PLE_SOURCE_PLAN=PREVIEW_ONLY_NOT_AUTHORIZED
```

**Verified narrow result:** one exact pre-existing local image,
two container image/mount records, no image-declared volumes;
the read-only feasibility planner returned
`REVIEW_CANDIDATE_NOT_AUTHORIZED` after
**3 inspections, 0 copies, 0 mutations, 0 GPU runs**.
The human-visible checkout SHA guard and fast-forward succeeded.
Declared `Config.Volumes=NONE` reduces one particular
anonymous-volume creation hazard but does not exclude metadata,
storage, device, or Docker daemon side effects of a future
container create. This evidence is **NOT permission to create
or delete** a temporary Docker object, and does **not**
demonstrate that a mountless copy would work or that image PLE
files exist.

**Repository next step (source-only):** added the reviewed-but-
unapproved [isolated image source-access plan](../../../docs/LYCHEE888-ISOLATED-SOURCE-READ-PLAN.md)
with identity/resource/STOP/postcheck/cleanup rules.
The plan does **not** implement or run any Docker mutation.
Installed PLE source SHA and lychee888 TP=1 still
`NOT_CAPTURED / NOT_QUALIFIED`.

## 2026-10-18 — ACTUAL_DGX isolated temporary source captured but protected postcheck failed

Owner supplied **actual physical DGX** terminal output, not a CI/synthetic run.
Clean `feature/wizard-modular-phase1-20261014` checkout fast-forwarded
`7693321..f1bce18`, and the checked-out exact full source SHA was
`f1bce18ef6ab444ced20f4efed2ba8ec42a250f0`. The command
read GitHub exact-head CI and obtained `EXACT_HEAD_CI=SUCCESS_2_OF_2`.
The default preflight was metadata-only, with
`PLAN_ONLY_PROTECTED_IDENTITIES_MATCH`, no create/copy.

**Actual approved single-operation result:**

```text
PLE_TEMP_PRE_FREE_BYTES=448726278144
PLE_TEMP_PRE_FREE_INODES=59498649
PLE_TEMP_PLANNED_NAME=qwen38-ple-read-e7e7bac84a0b79e85020ff51
PLE_TEMP_CREATED_ID=eb91d18dd1a1b45a4cba233160165bbe43b7835afa21873686402b505aac9375
PLE_TEMP_CREATED_STATE=CREATED_NO_MOUNTS
PLE_TEMP_COPY_CONTROL=SMALL_REGULAR_TAR_READABLE
PLE_TEMP_SOURCE_PATH=/usr/local/lib/python3.12/dist-packages/vllm/models/qwen3_8_flash_next/nvidia/ple_layer.py
PLE_TEMP_SOURCE_SHA256=a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7
PLE_TEMP_SOURCE_SHA256=a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7
PLE_TEMP_FP8_PLE_SELECTION_SOURCE=NATIVE_FP8_CONFIG_ONLY_SOURCE
PLE_TEMP_BF16_GLOBAL_SCALE_REGISTRATION_SOURCE=PRESENT
PLE_TEMP_FP8_SCALE_MULTIPLY_SOURCE=PRESENT
PLE_TEMP_SOURCE_AUDIT=STATIC_ONLY_NOT_EXECUTION
PLE_TEMP_LYCHEE888_TP1_LOADER=NOT_QUALIFIED
PLE_TEMP_CLEANUP=EXACT_ID_REMOVED_VERIFIED
PLE_TEMP_PROTECTED_POSTCHECK=FAIL_REVIEW
```

The duplicate `SOURCE_SHA256` lines were emitted by two stages of the same
source-processing function, not evidence of two independent captures.
The copied source itself was **not stored** in this evidence report, but
the installed-image-derived, no-bind, unstarted container's source path,
SHA256 and bounded static AST signatures were captured.

**Established:** on Docker Engine 29.6.2, a temporary container created
from exact installed image SHA256
`01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`
without nested model binds permitted a small generic TAR copy and
PLE source copy. The newly created exact ID
`eb91d18dd1a1b45a4cba233160165bbe43b7835afa21873686402b505aac9375`
was reportedly removed and absence checked via
`EXACT_ID_REMOVED_VERIFIED` (not yet independently re-observed later).
No container start, model load or GPU usage is reported.

**Critical unresolved:** `PLE_TEMP_PROTECTED_POSTCHECK=FAIL_REVIEW`.
The implementation compared serialized `Id`, `Image`, `Name`,
`Mounts`, entire `State`, entire `HostConfig` before/after;
the boolean result did **not** disclose which field(s) differed.
It is **not proof of actual container damage**, nor proof of
unchanged protected resource state. Differences may be caused by a
changing metadata field, unrelated concurrent activity, or an
unexpected Docker operation; do not assert root cause without
separate physical evidence. The `set -e` subshell exited to the
caller after the nonzero physical return; code did not emit
`SOURCE_CAPTURED_STATIC_ONLY`. No re-run, new Docker temp
object, forced cleanup, service restart or inference is authorized.

**Assessment: `PLE_SOURCE_SNAPSHOT=CAPTURED_STATIC_ONLY`,
`TEMP_CLEANUP=REPORTED_EXACT_ID_REMOVED_VERIFIED`,
`PROTECTED_POSTCHECK=FAIL_REVIEW_UNCLASSIFIED`,
`TOTAL_OPERATION=PARTIAL`,
`LYCHEE888_TP1=NOT_QUALIFIED`.**

Next **read-only only**: verify exact temp ID/name absence, current
protected image IDs, container state, nested mount topology, and
normal metadata drift by comparing name/ID Docker inspect snapshots
without showing bind source paths or environment secrets. This
later current-state check **cannot recreate the missing historical
before/after field-level difference**. Preserve existing objects,
do not replay already-consumed one-time approval.

## 2026-10-18 — ACTUAL_DGX second read-only postcheck: legacy Mounts differs between name and ID

The operator synced clean local source
`f1bce18ef6ab444ced20f4efed2ba8ec42a250f0` to
`4fa3a83f33be508736ea4d79f0ed97d24bc0be60`,
verified `EXACT_HEAD_CI=SUCCESS_2_OF_2`, and physically ran
**only** the read-only
`inspect_ple_postcheck_readonly.py` (maintained read-only model diagnostic).

```text
PLE_POSTCHECK_RESULT_KIND=CURRENT_READ_ONLY_NOT_HISTORICAL_REPLAY
PLE_POSTCHECK_TEMP_ABSENCE=ABSENT_ID_AND_NAME
PLE_POSTCHECK_HISTORICAL_FAILURE_CAUSE=UNRECOVERABLE_WITHOUT_PRE_POST_FIELD_SNAPSHOTS
PLE_POSTCHECK_DOCKER_MUTATION=NONE
PLE_POSTCHECK_DOCKER_COPY=NOT_PERFORMED
PLE_POSTCHECK_GPU_RUN=NOT_PERFORMED
PLE_POSTCHECK_IMAGE=MATCH_PINNED_ID_AND_SIZE
PLE_POSTCHECK_MANAGED_IDENTITY=MATCH_EXACT_ID_IMAGE_NAME
PLE_POSTCHECK_MANAGED_STATE=EXITED
PLE_POSTCHECK_MANAGED_ROOTFS=READONLY_FALSE
PLE_POSTCHECK_MANAGED_MOUNT_TOPOLOGY=MODEL_CONFIG_NESTED_RO_BINDS
PLE_POSTCHECK_MANAGED_NAME_VS_ID_FIELDS=MATCH
PLE_POSTCHECK_LEGACY_IDENTITY=MATCH_EXACT_ID_IMAGE_NAME
PLE_POSTCHECK_LEGACY_STATE=EXITED
PLE_POSTCHECK_LEGACY_ROOTFS=READONLY_FALSE
PLE_POSTCHECK_LEGACY_MOUNT_TOPOLOGY=MODEL_CONFIG_NESTED_RO_BINDS
PLE_POSTCHECK_LEGACY_NAME_VS_ID_FIELDS=DIFFERENT_Mounts
PLE_POSTCHECK_CURRENT_STATIC_POSTCHECK=STOP_REVIEW_REQUIRED
```

**Confirmed**: the temporary object is absent under its exact
full ID **and** its unique name; the pre-existing pinned
image ID and size remain the same; both protected objects
retain exact expected names/IDs, exited state, writable
container rootfs flags and the expected nested `/model`
and `/model/config.json` read-only bind topology.
Neither protected object was started or modified by this
read-only inspection.

**Unresolved**: `qwen38-ab-legacy`'s `Mounts`
**serialized array** differs between querying its Docker
name and exact full ID. The first script compared arrays
with order significance and emitted only the section name
`DIFFERENT_Mounts`. This may be an **order-only reordering**
from Docker inspect serialization, or a material change
within the mount records; the physical output cannot
distinguish. Do **not** assert mount damage or automatic
resolution. Original one-shot source probe's
`PROTECTED_POSTCHECK=FAIL_REVIEW` remains historical
`FAIL_REVIEW` with unrecorded before/after field-level
details.

**Next SOURCE_ONLY fix:** extend the same read-only tool to
compare complete mount records **without list-order
sensitivity**, identify any destination/type/RW/other
field differences via non-sensitive classification labels,
and test failure cases. No source reread, new temporary
container, Docker mutation or GPU activity is authorized.

## 2026-10-18 — ACTUAL_DGX order-aware protected postcheck PASS_CURRENT_ONLY

The operator physically ran the revised, **read-only**
`inspect_ple_postcheck_readonly.py` at a clean local
`feature/wizard-modular-phase1-20261014` checkout,
fast-forwarded `4fa3a83..a24cd3a` and SHA-checked
`a24cd3a7ce48c7531cabbdfec0139327eefce18a`.
The operator's exact-HEAD CI guard printed
`EXACT_HEAD_CI=SUCCESS_2_OF_2`.
Actual DGX terminal output was:

```text
PLE_POSTCHECK_RESULT_KIND=CURRENT_READ_ONLY_NOT_HISTORICAL_REPLAY
PLE_POSTCHECK_TEMP_ABSENCE=ABSENT_ID_AND_NAME
PLE_POSTCHECK_HISTORICAL_FAILURE_CAUSE=UNRECOVERABLE_WITHOUT_PRE_POST_FIELD_SNAPSHOTS
PLE_POSTCHECK_DOCKER_MUTATION=NONE
PLE_POSTCHECK_DOCKER_COPY=NOT_PERFORMED
PLE_POSTCHECK_GPU_RUN=NOT_PERFORMED
PLE_POSTCHECK_IMAGE=MATCH_PINNED_ID_AND_SIZE
PLE_POSTCHECK_MANAGED_IDENTITY=MATCH_EXACT_ID_IMAGE_NAME
PLE_POSTCHECK_MANAGED_STATE=EXITED
PLE_POSTCHECK_MANAGED_ROOTFS=READONLY_FALSE
PLE_POSTCHECK_MANAGED_MOUNT_TOPOLOGY=MODEL_CONFIG_NESTED_RO_BINDS
PLE_POSTCHECK_MANAGED_NAME_VS_ID_MOUNTS=ORDER_ONLY
PLE_POSTCHECK_MANAGED_NAME_VS_ID_FIELDS=MATCH
PLE_POSTCHECK_LEGACY_IDENTITY=MATCH_EXACT_ID_IMAGE_NAME
PLE_POSTCHECK_LEGACY_STATE=EXITED
PLE_POSTCHECK_LEGACY_ROOTFS=READONLY_FALSE
PLE_POSTCHECK_LEGACY_MOUNT_TOPOLOGY=MODEL_CONFIG_NESTED_RO_BINDS
PLE_POSTCHECK_LEGACY_NAME_VS_ID_MOUNTS=IDENTICAL_ORDER
PLE_POSTCHECK_LEGACY_NAME_VS_ID_FIELDS=MATCH
PLE_POSTCHECK_CURRENT_STATIC_POSTCHECK=PASS_CURRENT_ONLY
```

**New verified physical state:** the previously created one-off
temporary object remains **absent by exact ID and unique name**.
Pinned image ID/size and both existing protected container
names/full IDs/Image SHA remain matched; both are `exited`,
both have `ReadonlyRootfs=false` and the previously verified
nested `/model` + `/model/config.json` read-only bind topology.
The managed object's name-vs-ID inspect `Mounts` comparison
reported **`ORDER_ONLY`** (all complete mount record values
equal, only list order differs); legacy A/B object reported
**`IDENTICAL_ORDER`**. Name-vs-ID comparison of the other
original fingerprint fields also returned `MATCH`. No
Docker create/copy/delete/start, host changes or GPU use
occurred in this follow-up.

**Decision:** current protected-state triage
`PASS_CURRENT_ONLY`; the earlier ambiguous raw-array
`DIFFERENT_Mounts` is **not a reproduced substantive
mount-record difference in this new snapshot**. This is
NOT proof that the prior `FAIL_REVIEW` was solely mount
ordering or that the historical before/after metadata were
identical. The one-shot physical image source extraction
remains `SOURCE_SHA256_CAPTURED`, but the original
`FAIL_REVIEW` evidence is immutable and historically
`UNCLASSIFIED` because raw pre/post field snapshots were
not retained.

Next work may proceed **source-only** on
`compressed-tensors` vs native `Fp8Config` routing,
BF16 global scale tensor loader semantics and single GB10
TP=1 non-GPU preconditions. No additional Docker temp,
GPU execution, model installation, weight download or
protected-object mutation is approved.

## 2026-10-18 — ACTUAL_DGX pinned lychee888 JSON L0: 132279699754 indexed bytes, loader blocked

The operator provided full actual DGX terminal results, not
a CI or synthetic simulation. Local clean checkout:
`b9114544eb35d7275740cf0ca2e9d010134f7cbb`,
branch `feature/wizard-modular-phase1-20261014`;
`git fetch` reported already up to date.
The earlier two exact-head CI workflows were both
`SUCCESS`. The operator executed the standalone
**pinned JSON-only**, read-only
`assess_lychee888_loader.py --json` command, which
finished with `LYCHEE888_METADATA_COMMAND=COMPLETED`.
It did not execute Docker, GPU, checkpoint tensor
downloads, or model loading.

The physically observed report contained:

```text
checkpoint=lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE
immutable_revision=1b3c3cedc14fb3bee4294dea5e3515af74b8268a
installed_image_id=sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4
installed_ple_source_path=/usr/local/lib/python3.12/dist-packages/vllm/models/qwen3_8_flash_next/nvidia/ple_layer.py
installed_ple_source_sha256=a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7
installed_ple_source_dispatch=NATIVE_FP8_CONFIG_ONLY_SOURCE
installed_source_evidence=ACTUAL_DGX_SHA_AND_STATIC_AST_ONLY_NOT_FULL_SOURCE_ARCHIVE
physical_protected_postcheck=PASS_CURRENT_ONLY_HISTORICAL_FAIL_REVIEW_RETAINED
quant_declared_format_class=COMPRESSED_TENSORS_MIXED_PRECISION_CONFIRMED_IN_METADATA
runtime_quant_class_expectation=COMPRESSED_TENSORS_CLASS_EXPECTED_NOT_RUNTIME_ATTESTED
installed_native_gate_reachability=NO_DIRECT_NATIVE_FP8_CLASS_MATCH_PROVEN
bf16_global_scale_loader_gate=FP8_METHOD_CONDITIONAL_ONLY_BF16_SCALE_LOAD_UNVERIFIED
ple_dtype_dispatch=NOT_PROVEN_IN_INSTALLED_SOURCE
ct_prefix_scheme_resolution=NOT_AUDITED_FOR_INSTALLED_IMAGE
installed_loader_contract=BLOCKED_SOURCE_ONLY_UNQUALIFIED
indexed_tensor_bytes=132279699754
dgx_spark_nominal_unified_bytes=128000000000
full_resident_nominal_memory_screen=INDEXED_TENSOR_BYTES_EXCEED_NOMINAL_UNIFIED_MEMORY
runtime_peak_memory=NOT_MEASURED
l0_verdict=INDEX_STRUCTURE_PASS_METADATA_ONLY
index_tensor_keys=223047
ple_weight_shards=128
ple_files=10
global_weight_scale_keys=1
ple_embedding_dtype=float8_e4m3fn
quant_method=compressed-tensors
quant_algo=null
quant_format=mixed-precision
nvidia_patch_source_dispatch=NOT_APPLICABLE; NVIDIA PATCH EXPECTS ModelOptMixedPrecisionConfig
managed_runtime_adapter=NOT_IMPLEMENTED_OR_NOT_QUALIFIED
single_gb10_tp1=NOT_VERIFIED
verdict=SOURCE_ONLY_LOADER_UNQUALIFIED
```

**Important provenance split:** the pinned model revision and
`indexed_tensor_bytes` were obtained in this actual
metadata-only Hub read; the
`installed_image_id`, `installed_ple_source_path`,
`installed_ple_source_sha256`, `installed_ple_source_dispatch`,
and physical postcheck label in this particular JSON
are **fixed, previously recorded code constants** from
earlier separately attested DGX probes, **not** fresh
independent image inspection on this execution.

The pinned safetensors index declares
`metadata.total_size=132279699754` bytes; that is
**4,279,699,754 bytes over** nominal DGX Spark unified
memory `128000000000` bytes, before any other memory.
This is a necessary caution for a hypothetical fully
resident untransformed checkpoint, **not a host memory
measurement or proof of model load failure**. mmap,
quantization transformations and offload residency
are entirely unqualified. The metadata-only test
does not inspect actual safetensors tensor headers
or hashes; global BF16 scale dtype and loading
are not attested by the index key alone.

**Disposition:** L0 pinned metadata
`INDEX_STRUCTURE_PASS_METADATA_ONLY`; exact source
snapshot SHA available as a historical attestation;
**loader contract `BLOCKED_SOURCE_ONLY_UNQUALIFIED`**;
GB10 TP=1 **`NOT_VERIFIED`**, candidate **NOT_INSTALLABLE**.
No new Docker or GPU operation is authorized.
