# lychee888 local installed-image PLE source — isolated read-only probe plan

**Status:** PROPOSAL / NOT AUTHORIZED / NOT EXECUTED, 2026-10-18.
**Host scope:** the sole protected NVIDIA DGX Spark GB10; this document
is a *review contract*, not a command to create/remove Docker objects.
**Project rules:** [permanent handoff](SESSION-HANDOFF-PROMPT.md),
[current status](CURRENT-STATUS.md),
[model-specific integration](LYCHEE888-WIZARD-INTEGRATION.md) and
[immutable ACTUAL_DGX evidence](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## Exact observed ACTUAL_DGX prerequisite

The operator fast-forwarded a clean checkout to
`769332111dc4cdfa13e9817544b9166402985f66` and executed
`python3 -B scripts/model/audit_installed_ple_image.py --plan-isolated-source`.
The actual on-host read-only planner output was:

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

This proves **metadata-only preview execution** on the physical host.
The fixed image identity, two matching containers and their nested
read-only binds are attested; the image config declares no volumes.
It does not prove that the installed image's PLE module is at any
particular path or compatible with lychee888.

## Why an isolated unstarted temporary container is under consideration

Docker Engine **29.6.2** on the DGX predates the 29.8.2
overlapping-bind-mount Docker-copy fix
([Moby #53724](https://github.com/moby/moby/pull/53724)).
The managed and historical A/B containers each have a read-only
`/model` bind containing another read-only bind at
`/model/config.json`. The managed copy of unrelated `/etc/group`
fails at `openat model/config.json: read-only file system`.
Reusing the A/B container does not remove the blocking condition.

An unstarted container **created from the same immutable local image
but with zero additional mounts** is a candidate for a bounded
`docker cp` inspection without that nested-mount replay path. Such
a temporary container still changes the Docker object store, consumes
metadata/writable-layer resources, and would later require deletion.
It is NOT a purely read-only host operation. The declared-volume
`NONE` result rules out only image-declared anonymous volumes, not
all side effects. `docker cp` on the future temporary container
is not yet tested or guaranteed to succeed.

## Preconditions before requesting separate owner approval

1. Revalidate the exact full **local Docker image SHA256** and both
   protected container full IDs, image references, statuses and
   mounts. Re-run the nonmutating planner on the reviewed code SHA
   and compare to the immutable evidence; do not rely on image tag alone.
2. Verify the image's `Config.Volumes` remains absent/empty and
   no implicit mounts or privileged features can be introduced by the
   proposed create-only parameters. Record a unique proposed
   temporary name and an owner/experiment label not used by normal
   managed services; reject any collision.
3. Inspect host disk/inodes and Docker data-root filesystem
   **without printing sensitive paths**. Bound the permitted
   writable-layer/disk/time costs and stop if the margin is
   insufficient. Docker image `Size=20629141958` bytes is **not**
   the expected extra creation cost or evidence of free capacity.
4. Confirm absence of concurrent installer/uninstaller, managed
   transition, benchmarking, Docker prune/GC, other conflicting
   changes and any maintenance/ownership conflict. The normal
   protected assets, monitoring and service settings stay untouched.
5. Require **separate explicit approval** for the narrow pair of
   Docker mutations: create exactly one uniquely owned, unstarted
   temporary container; remove only that same verified ID. Approval
   is never inferred from the planner `REVIEW_CANDIDATE` status,
   a CI pass, a prior message saying “continue”, or the mere
   presence of this plan.
6. Review the exact allowlisted procedure and tests before physical
   use. No unattended cleanup command may be allowed to delete a
   container identified only by mutable name. Prepare a recovery
   path if cleanup is blocked, preserving forensic evidence.

## Proposed execution contract — only after explicit approval

**No executable mutation command is provided by this plan.**

- **Create:** one container via Docker **create**, never run/start/exec,
  from the exact already-installed immutable image ID. No user-provided
  bind mounts, named/anonymous volumes, model checkpoint, GPU devices,
  exposed/published ports, network access or restart policy.
  Select an inert entrypoint to make accidental execution less
  dangerous, but do not rely on it as a start-prevention control.
  Capture its returned full container ID immediately.
- **Immediately inspect:** verify exact newly created ID, origin
  image SHA256, `State.Status=created`, expected ownership label,
  `HostConfig.ReadonlyRootfs`, and **empty** effective
  `Mounts` and bind/device allocations. Any mismatch is STOP;
  do not probe files or start the object.
- **Copy transport test:** at most one bounded non-model
  `/etc/group` TAR stream; reject an invalid/oversized TAR.
  If this generic control fails, stop rather than attempting
  twenty-four PLE/GEMM paths.
- **Source capture:** probe only predefined Python package paths
  already allowlisted in the maintained source auditor. Limit the
  **total bytes and per-file bytes** (currently
  `MAX_RESPONSE=1,048,576`, `MAX_SOURCE=524,288`) and
  fail closed on symlinks, multi-entry archives, size overflow,
  invalid UTF-8, invalid AST, or wrong filename. Never export
  the full 20.63-GB image or touch model weight shards.
- **Evidence:** record only verified image/container provenance,
  exact source path, source SHA256, bounded source static
  signatures, Docker copy result and whether the observed
  source was overridden by image/container mounts. The probe
  proves a source snapshot in an isolated container derived
  from the same image ID; it does **not** independently establish
  runtime FP8 branch selection, BF16 scale ingestion, TP=1
  readiness, inference, or a measured benchmark.
- **Cleanup:** before deletion, re-inspect **the exact newly
  created full ID**, state still `created`, same ownership
  label, same immutable image, and nonprotected name.
  Only the narrowly approved exact-ID temporary object may
  be removed. No `--force`, `prune`, name-wide removals,
  existing managed object deletion, or history cleanup.
  If identity/state changed, STOP and request human review;
  do not auto-remove or silently leave unreported leftovers.
- **Postconditions:** independently re-inspect protected managed
  `qwen38-flash-next` and `qwen38-ab-legacy` IDs, image ID,
  active runtime/service intent, mount metadata, and original
  immutable evidence. Record whether the temporary container
  still exists, measured additional disk cost/recovery and
  any cleanup error. A failed postcheck is `INCOMPLETE`,
  never `PASS`.

## Explicitly forbidden in this investigation

No `docker run`, `docker start`, `docker exec`, model load,
GPU benchmark, new Docker image build/pull, daemon upgrade/restart,
host remount, checkpoint download, `docker save` bulk export,
unbounded Docker layer-store walk, existing container rename/delete,
unapproved temporary create/remove, or protected PR merge.

## Outstanding questions

- Whether create-only on this physical Docker 29.6.2 installation
  without mounts is accepted without unusual storage effects.
- Which allowlisted `ple_layer.py` path really exists within
  the installed image; exact source SHA is **NOT_CAPTURED**.
- Whether `compressed-tensors` `mixed-precision` checkpoint
  produces a supported FP8 PLE method, registers and uses its
  global BF16 scale, and is safe at single DGX Spark TP=1.
- Whether separately approved actual host resource and rollback
  margins would permit this *small* temporary-object test.

**Current gate:** `PHYSICAL_PREVIEW=PASS_METADATA_ONLY`,
`CREATE_DELETE_APPROVAL=NOT_GRANTED`,
`TEMP_CONTAINER=NOT_CREATED`,
`PLE_IMAGE_SOURCE=NOT_CAPTURED`,
`LYCHEE888_INSTALLABLE=NO`.
