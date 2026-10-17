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
