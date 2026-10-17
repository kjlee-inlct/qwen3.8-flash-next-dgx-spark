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
