# ACTUAL DGX — existing-image PLE static audit stopped on source mount

**Evidence class:** ACTUAL_DGX, operator-supplied Wizard terminal excerpt
dated 2026-10-16. Original terminal file SHA256, complete Docker
inspect output, exact image digest, offending mount path and mounted
source bytes are **NOT_CAPTURED**. Do not claim an independent host
audit or infer what the mount contains.

## Read-only operator procedure

The operator launched Model Management → Candidate metadata →
**4 Existing image PLE loader source (read-only)**, from the
`feature/wizard-modular-phase1-20261014` line that already contained
the read-only audit implementation (latest prior CI PASS at
`00e0b1d1d6e58996e3d7dba83465592baeb03119`).
The exact checkout HEAD was **not** printed at this invocation.

```text
Existing image PLE loader source / 설치 이미지 PLE 소스 점검
Only local Docker image/container inspect and copy from the EXISTING
qwen38-flash-next container.
No container creation, start, GPU use, downloads, model data
or service changes.
PLE_IMAGE_AUDIT=INCONCLUSIVE: Mounted vLLM source could differ from image layer
DOCKER_MUTATION=NONE
GPU_RUN=NOT_PERFORMED
Installed image source is INCONCLUSIVE or unavailable;
NO managed resources were changed.
lychee888 remains NOT installable.
Runtime adapter and memory admission are still blocked.
```

**Interpretation:** The original audit refused source attestation
when any mount destination matched a broad vLLM Python package
prefix. This is a deliberate fail-closed guard, not an observed
lychee888 loader failure, nor proof the mount actually shadows
`ple_layer.py`. Docker bind mounts can obscure image-layer data,
and `docker cp` cannot reliably copy user-created mounts;
the effective source must be resolved with provenance rather than
equated to original image contents.

## Source-only remediation, not a new physical result

The project now distinguishes (a) unrelated Python/vLLM mount
destinations, (b) an exact or ancestor bind mount covering the
candidate PLE source, and (c) no relevant mount. In case (b) a
bounded local **no-symlink-following read** of the corresponding
host bind source may be used, with an explicit
`source_origin=HOST_BIND_MOUNT_FILE_NOT_IMAGE_LAYER`, provided
the exact existing Docker image/container identity matches.
Ambiguous overlays, non-bind mounts, unreadable, symlinked or
oversized source files remain `INCONCLUSIVE`.
This does not require restarting Docker, a container, model,
service or GPU and does not qualify TP=1.

The updated SOURCE/CI and its Wizard route must be synchronized
on the DGX before repeating **3 → 7 → 4**. No subsequent physical
source extraction was supplied at the time of this record.
