# Script layout

This directory preserves upstream-derived paths and stable operator entry points at
`scripts/*` while keeping repository-specific implementations in role-specific
subdirectories.

## Top-level role map

Files directly under `scripts/` fall into one of three intentionally different roles. A path may appear in more than one role when an upstream-derived file is also a stable operator command.

| Role | Purpose | Examples | Relocation policy |
|---|---|---|---|
| Upstream-derived | Preserve provenance and compatibility with the upstream repository layout. | `serve.sh`, `bench-prefill.py`, `download-weights.sh`, `patch-*.py`, `Dockerfile.*` | Keep the upstream path. |
| Stable operator entry point | Human- or service-facing command whose path is part of the operational interface. | `doctor.sh`, `manage-*.sh`, `release-manager.sh`, `update-release.sh`, `runtime-transition.sh`, `profile-switch-transition.sh`, `release-profile-refresh-transition.sh`, `prepare-h38-image.sh`, `run-h38-managed-followup-gates.sh` | Keep the public path stable; move implementation only when a thin entry point can preserve compatibility. |
| Compatibility shim | Legacy helper path that forwards to a canonical implementation in a role directory. | `qualify-release.sh`, `collect-diagnostics.sh`, `validate-runtime.py`, `state_file.py` | Keep thin; new internal code must target the canonical path. |

Canonical repository-specific implementation belongs in `scripts/<role>/`, currently:

```text
scripts/
├── benchmark/
├── diagnostics/
├── lifecycle/
├── lib/
├── model/
└── runtime/
```

This distinction is intentional: the goal is not an empty `scripts/` root. The root remains the compatibility and operator surface, while role directories hold canonical internal implementation.

## Upstream provenance

The canonical upstream for this repository is:

- `dolf3131/qwen3.8-flash-next-dgx-spark`

The following files exist upstream under the same `scripts/` paths and must remain
at those paths in this fork. Some are byte-identical to upstream; others have been
extended locally but retain upstream provenance:

- `Dockerfile.nv-mixed`
- `Dockerfile.skinny-gemm`
- `bench-prefill.py`
- `download-weights.sh`
- `patch-nv-mixed.py`
- `patch-skinny-gemm-tp1.py`
- `serve.sh`

These files are not candidates for cosmetic relocation.

## Stable operator entry points

The following repository-specific top-level paths are stable commands or service
entry points and remain directly available:

- `doctor.sh`
- `manage-service.sh`
- `manage-proxy.sh`
- `manage-swap.sh`
- `manage-models.sh`
- `manage-storage.sh`
- `wait-ready.sh`
- `release-manager.sh`
- `update-release.sh`
- `runtime-transition.sh`
- `update-transition.sh`
- `profile-switch-transition.sh`
- `release-profile-refresh-transition.sh`
- `prepare-h38-image.sh`
- `run-h38-managed-followup-gates.sh`
- `preflight-runtime.sh`
- `service-runner.sh`

## Compatibility entry points

Several older top-level helper paths are retained as thin compatibility shims so
existing releases, tests, scripts, and automation do not break while canonical
implementations live under role-specific directories:

- `bootstrap-release.sh` -> `lifecycle/bootstrap-release.sh`
- `qualify-release.sh` -> `lifecycle/qualify-release.sh`
- `update-transition.sh` -> `lifecycle/update-transition.sh`
- `profile-switch-transition.sh` -> `lifecycle/profile-switch-transition.sh`
- `release-profile-refresh-transition.sh` -> `lifecycle/release-profile-refresh-transition.sh`
- `prepare-h38-image.sh` -> `runtime/prepare-h38-image.sh`
- `collect-diagnostics.sh` -> `diagnostics/collect-diagnostics.sh`
- `monitor-runtime.sh` -> `runtime/monitor-runtime.sh`
- `runtime-transition.sh` -> `runtime/runtime-transition.sh`
- `preflight-runtime.sh` -> `runtime/preflight-runtime.sh`
- `service-runner.sh` -> `runtime/service-runner.sh`
- `validate-runtime.py` -> `runtime/validate_runtime.py`
- `model-profiles.sh` -> `model/model-profiles.sh`
- `inspect-model.py` -> `model/inspect_model.py`
- `prepare-config.py` -> `model/prepare_config.py`
- `state_file.py` -> `lib/state_file.py`
- `release_manifest.py` -> `lib/release_manifest.py`
- `doctor-observability.sh` -> `diagnostics/doctor-observability.sh`

Compatibility shims are intentionally small. New internal code should use the
canonical path rather than adding new dependencies on a shim.

## Canonical internal categories

Repository-specific implementations are organized as follows:

- `lib/`: reusable Python helpers shared across lifecycle/runtime scripts.
- `diagnostics/`: read-only diagnostics and support-bundle implementation.
- `runtime/`: runtime transition, preflight, service runner, monitor, and runtime validation.
- `lifecycle/`: immutable-release bootstrap, qualification, update transaction, profile-switch transaction, and atomic release/profile-refresh logic.
- `model/`: model profile, checkpoint inspection, and config preparation helpers.
- `benchmark/`: canonical read-only benchmark runner and benchmark helpers.

Canonical implementations include:

- `lib/state_file.py`
- `lib/release_manifest.py`
- `diagnostics/doctor-observability.sh`
- `diagnostics/collect-diagnostics.sh`
- `runtime/runtime-transition.sh`
- `runtime/preflight-runtime.sh`
- `runtime/service-runner.sh`
- `runtime/service-adopt-runner.sh`
- `runtime/service-stop.sh`
- `runtime/monitor-runtime.sh`
- `runtime/wait-ready.sh`
- `runtime/validate_runtime.py`
- `lifecycle/update-transition.sh`
- `lifecycle/profile-switch-transition.sh`
- `lifecycle/release-profile-refresh-transition.sh`
- `lifecycle/bootstrap-release.sh`
- `lifecycle/qualify-release.sh`
- `model/model-profiles.sh`
- `model/inspect_model.py`
- `model/prepare_config.py`
- `model/prepare-hybrid-checkpoint.py`
- `model/prepare-quant-layout-hybrid-checkpoint.py`
- `model/inspect-checkpoint-diff.py`
- `model/inspect_catplusplus_metadata.py` (pinned Hub JSON full-tree only)
- `model/inspect_lychee888_metadata.py` (pinned-source JSON L0)
- `model/assess_lychee888_loader.py` (pinned JSON vs NVIDIA patch source)
- `model/audit_installed_ple_image.py` (existing container/source read-only)

## Read-only model candidate evidence tools

The canonical Python modules in `scripts/model/` are independently testable;
operators reach the candidate inventory via `./wizard.sh` → **3 → 7**.
`inspect_catplusplus_metadata.py` (Wizard items 1/2) reads only immutable
Hub JSON; `assess_lychee888_loader.py` (item 3) compares pinned
lychee888 config/index to repository source without weights. Item 4 runs
`audit_installed_ple_image.py`, which reads only an existing exact-image
managed Docker container and, if the PLE source is bind-mounted, the
corresponding host source file using size-limited no-follow read-only
operations. It ignores unrelated vLLM mounts. The output **always**
distinguishes `HOST_BIND_MOUNT_FILE_NOT_IMAGE_LAYER` from
`EXISTING_CONTAINER_FILESYSTEM_NOT_PROVEN_RUNTIME`; ambiguous overlay
or unsafe file provenance fails closed. No `docker run`, `exec`,
`start`, Docker/host mutation or GPU is invoked by these probes.
Source SHA256 and static AST method presence are not a runtime import,
tensor load, scale consumption or TP=1 readiness proof.
The read-only audit first attempts a single bounded non-model
`/etc/group` TAR copy to preflight Docker-copy transport and
records allowlisted `HostConfig.ReadonlyRootfs` (without changing it).
If the copy fails with `FILESYSTEM_READ_ONLY` or
`CONTAINER_ROOTFS_READ_ONLY`, it skips **all 24** PLE/GEMM file
probes (`NOT_ATTEMPTED_PRECHECK_BLOCK`) rather than falsely claiming
the files absent. Otherwise the existing source-path probes and
sanitized failure counts apply. No copied bytes, stderr, mounted
host paths or credentials are printed, and the result never
qualifies the model loader.
See `docs/LYCHEE888-WIZARD-INTEGRATION.md` for the exact evidence gates.

## Model download transport

`scripts/download-weights.sh` keeps revision pinning, disk-reserve checks, the
project model manifest, profile guards, and SHA-256 verification in the host script.
For large checkpoints, transfer is delegated to
`huggingface_hub.snapshot_download()` inside an existing local Docker image when
available.

Installable profiles such as `mazinb` no longer require `--candidate`; the normal
registry path accepts them directly. `--candidate` is retained as an explicit escape
hatch for a tracked download profile that is not yet installable through the managed
installer. It bypasses only the installability guard; it does not make that profile
qualified or selectable by `install.sh`.

The host does not need the Hugging Face Python package installed. The default
container image is `vllm-orcarouter-v029:v1`; override it with
`HF_DOWNLOADER_IMAGE` when needed. The helper enables
`HF_XET_HIGH_PERFORMANCE=1` by default and uses eight snapshot workers by default
(`HF_DOWNLOAD_MAX_WORKERS` overrides this).

Before transfer, existing destination files are verified against the remote LFS
SHA-256 metadata. Verified files are excluded from `allow_patterns`, so a partial
checkpoint directory can resume without redownloading already-good shards. Missing,
partial, or failed-verification files are the only files requested from the snapshot
downloader. After transfer, those files are verified again before the project model
manifest is marked complete.

If Docker, the selected image, or `huggingface_hub` in that image is unavailable,
the script falls back to the older resumable `curl -C -` path rather than making
host Python packaging a prerequisite.

Examples:

```bash
MODEL_PROFILE=mazinb ./scripts/download-weights.sh --check
MODEL_PROFILE=mazinb ./scripts/download-weights.sh

HF_DOWNLOAD_MAX_WORKERS=12 \
MODEL_PROFILE=mazinb ./scripts/download-weights.sh
```

## Storage management

`scripts/manage-storage.sh` is the project-wide disk usage and cleanup entry point.
It inventories managed checkpoints, Docker usage, immutable releases, local benchmark
results, the Hugging Face cache, and the dedicated PLE swap file.

The default prune policy is deliberately conservative:

- never delete the active checkpoint or any managed model directory;
- never delete the manifest's active runtime image;
- retain both current and previous immutable releases;
- retain the PLE swap and Hugging Face cache;
- remove only stopped experiment containers, dangling images, stale build cache,
  inactive releases, and aged local benchmark results;
- remove known QSA experiment image tags only with `--experiments`.

Examples:

```bash
./scripts/manage-storage.sh status
./scripts/manage-storage.sh recommend
./scripts/manage-storage.sh plan
./scripts/manage-storage.sh plan --experiments
./scripts/manage-storage.sh prune --dry-run --experiments
./scripts/manage-storage.sh prune --yes
```

Docker image policy is defined centrally in `scripts/storage/assets.sh`. Images are
classified as `stable`, `baseline`, `optional`, or `experiment`; only registry
entries marked disposable are eligible for `--experiments`. This keeps future model
profiles and serving backends from scattering cleanup rules across scripts.

The status/plan output reports Docker image logical sizes. Because Docker layers are
shared, logical size is an upper-bound-style inventory value rather than an exact
prediction of bytes reclaimed.

`recommend` is read-only. It ranks inactive managed checkpoints, Docker reclaimable
space, Hugging Face cache usage, and protected active allocations. For inactive
checkpoints it prints the exact `manage-models.sh remove ... --dry-run` command rather
than deleting the checkpoint itself.

`scripts/manage-models.sh` is the logical model/profile lifecycle view. It keeps
the original checkpoint-only `remove PATH` command, and also exposes Docker-aware
profile commands:

```bash
./scripts/manage-models.sh assets
./scripts/manage-models.sh retire hybrid-h8-ct-block --dry-run
./scripts/manage-models.sh retire hybrid-h8-ct-block --yes
```

`assets` reports each profile's checkpoint, container, image, active state, and
checkpoint/image dependencies. `retire PROFILE` removes a stopped profile
container plus profile-owned disposable image/checkpoint assets only when their
independent dependency checks allow it. Active installation assets, running
containers, and assets required by a present child profile are protected.

Checkpoint and Docker-image dependencies are tracked separately. For example,
H10 uses the installed OrcaRouter checkpoint but does not depend on the legacy
`vllm-skinny-tp1:v1` image; H10's derived image does depend on the H9 image.
This separation allows the legacy skinny image to be reclaimed after the
canonical installation stops referencing it without risking the current
v0.29 experiment lineage.

The checkpoint-only model manager still recognizes both normal model manifests and
`.qwen38-hybrid-manifest.json`; it refuses to delete the active installation model
or any checkpoint currently mounted by a running Docker container.

## Benchmark layout

The canonical repository benchmark harness lives under `scripts/benchmark/`:

- `scripts/benchmark/run.py` is the canonical benchmark CLI.
- `scripts/benchmark/lib/` contains implementation helpers used by the CLI.
- `scripts/benchmark/common.py` is a local compatibility import used by the runner.
- top-level `bench/run.py` and `bench/common.py` are compatibility shims for older callers.
- `scripts/bench-prefill.py` stays at its upstream-derived path and is not the canonical benchmark harness for this fork.

## Dependency boundary policy

Canonical category code follows an explicit dependency direction:

| Category | May directly depend on |
|---|---|
| `lib/` | no other canonical category |
| `model/` | `lib/` |
| `runtime/` | `lib/`, `model/` |
| `lifecycle/` | `lib/`, `runtime/` |
| `diagnostics/` | `lib/`, `lifecycle/`, `runtime/` |
| `benchmark/` | no other canonical category; it measures the exposed runtime/API rather than importing orchestration |

Self-references inside a category are allowed. Stable top-level operator entry points are not treated as canonical-category dependencies because they are part of the public compatibility surface.

The layout tests scan canonical implementation files for explicit cross-category path references and fail when a reference points outside this allowlist. This is a guardrail rather than a full language-level import graph, so new dependency styles should extend the test instead of bypassing it.

## Layout rules

1. Do not relocate upstream-derived paths from `dolf3131/qwen3.8-flash-next-dgx-spark`.
2. Keep operator/service entry points stable.
3. Put repository-specific implementation under an explicit role directory.
4. Preserve older helper paths with small compatibility shims when removing them
   would break existing releases, tests, or automation.
5. Update internal references, tests, documentation, and CI in the same change.
6. When an operational workflow starts needing repeated ad-hoc commands, promote it to a reusable operator helper and document it in the same PR.
7. Do not combine layout refactors with unrelated runtime behavior changes.

## CI rule

Shell syntax and ShellCheck must recurse into script subdirectories. Python compilation must recurse through `scripts/` and `tests/`; canonical benchmark code is included under `scripts/benchmark/`.

### Read-only Docker-copy nested-mount topology hint

The existing-image PLE audit now prints a sanitized
`PLE_DIAGNOSTIC_DOCKER_CP_MODEL_CONFIG_MOUNT_TOPOLOGY` value based
on the existing protected container's `Mounts` entries for two
**fixed** destinations, `/model` and `/model/config.json`.
`MODEL_CONFIG_NESTED_RO_BINDS` means one bind at each destination,
both with `RW=false`; it is **not** proof of the daemon's root
cause. Other outcomes distinguish absent config-overlay, ambiguous
records, non-bind mounts and a nested pair with other RW flags.
No Docker bind source/path is displayed, no container is executed,
and the existing fail-closed `/etc/group` copy preflight and all
loader/TP=1 restrictions remain in effect. Use Wizard **3 → 7 → 4**.

### PLE isolated source read-only feasibility preview

Developer/reviewer-only command (not another Wizard menu action):

```bash
python3 -B scripts/model/audit_installed_ple_image.py --plan-isolated-source
```

This new mode performs **exactly three Docker metadata inspections**:
the existing tagged image, protected `qwen38-flash-next` and
historical `qwen38-ab-legacy`. It checks immutable image
identity, bounded image-size metadata, both container states,
`/model` and `/model/config.json` fixed mount topology
and image-declared `VOLUME` metadata. It never invokes
`docker cp`, creates/runs/removes a container, reads source
bytes, accesses model weights or uses GPU. It never prints
bind `Source` paths, environment values or full inspect JSON.
`REVIEW_CANDIDATE_NOT_AUTHORIZED` denotes only that a future
*create-only, mountless, unstarted* isolated container method
is worth explicit operator review; it does not grant permission
to create such a container and does not attest installed
PLE code. An image-declared `VOLUME` blocks qualification
because a temporary create can cause unexpected volume creation.
The old Wizard **3 → 7 → 4** behavior remains unchanged.

### Physical isolated-source metadata preview result (2026-10-18)

The owner physically ran
`audit_installed_ple_image.py --plan-isolated-source`
at exact checkout `769332111dc4cdfa13e9817544b9166402985f66`.
It reported `DECLARED_IMAGE_VOLUMES=NONE`,
`REVIEW_CANDIDATE_NOT_AUTHORIZED`, 3 inspect requests,
0 copies, 0 mutations and no source capture. A future
created-only mountless object remains out of scope without
**separate explicit approval**. See the
[review-only bounded procedure](../docs/LYCHEE888-ISOLATED-SOURCE-READ-PLAN.md)
for STOP conditions and owner/cleanup safeguards. This
developer-only review does not add a mutating Wizard action.

### One-time, owner-approved PLE isolated source probe

`model/probe_isolated_ple_source.py` implements a narrowly
approved separate research-only procedure; its default
invocation is inspect-only and its mutation route requires
`--execute`, the exact image digest, and
`--approved-scope ONE_UNSTARTED_TEMP_CONTAINER_CREATE_COPY_RM`.
It creates **one** unique, unstarted, mountless, networkless
container from the exact already-existing image (no build,
pull, GPU or weights). Source reads and TAR output are bounded.
Exact-ID deletion is allowed only for its own unchanged
created-state labeled temporary object; all existing
managed/history container IDs are protected.

Before physical execution require success on exact GitHub CI
and a clean DGX checkout to that SHA, with no concurrent
managed lifecycle transition. A failed cleanup or protected
postcheck is not a PASS and needs manual review. Owner
approval is scoped only to that temporary object's create
and removal; see
`docs/LYCHEE888-ISOLATED-SOURCE-READ-PLAN.md`.

### Read-only physical PLE protected-resource postcheck follow-up

**Physical source probe already ran once** at Git SHA
`f1bce18ef6ab444ced20f4efed2ba8ec42a250f0`:
image-derived Python 3.12 `ple_layer.py` was captured
(SHA256 `a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7`),
the unique temporary ID was removed and absence verified,
but `PLE_TEMP_PROTECTED_POSTCHECK=FAIL_REVIEW` requires
independent current-state inspection. **Do not execute the
one-time mutation probe again.**

The separate maintained
`python3 -B scripts/model/inspect_ple_postcheck_readonly.py`
performs **only seven Docker inspect requests**: temporary
full ID + temporary name, current tagged image, and the two
protected containers by name and exact full ID. It returns
only allowlisted sanitized status strings and names of
different metadata sections, never inspect JSON, mount
source host paths, labels or environment. `PASS_CURRENT_ONLY`
means *current* identities/states/topology and same-time
name-vs-ID metadata agree; it **cannot retroactively
reverse or explain** the earlier `FAIL_REVIEW`.
A mismatch/unknown returns nonzero with STOP.
[Full evidence](benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

### Postcheck mount-order-insensitive classification

After ACTUAL_DGX reported `qwen38-ab-legacy`
`NAME_VS_ID_FIELDS=DIFFERENT_Mounts`, the existing
`inspect_ple_postcheck_readonly.py` now distinguishes
two same-content mount lists with differing order
(`NAME_VS_ID_MOUNTS=ORDER_ONLY`) from
`DESTINATION_MEMBERSHIP_CHANGED`,
`TYPE_OR_RW_CHANGED`,
`OTHER_MOUNT_METADATA_CHANGED`, and
`INVALID_MOUNT_METADATA`. The unchanged exact
mount-record values, including sensitive Source
paths, are compared **privately and never printed**;
only static category labels are exposed.
`ORDER_ONLY` may yield `PASS_CURRENT_ONLY`,
but **cannot rewrite or prove** the original
single-source-probe pre/post `FAIL_REVIEW`.
All source copies and Docker mutations remain stopped.

### Installed-source-aware lychee888 loader metadata gate

`python3 -B scripts/model/assess_lychee888_loader.py --json`
fetches only **pinned** lychee888 API/config/index JSON.
It now includes the immutable **actual DGX**
image ID and installed Python PLE source SHA256
(static evidence previously captured, **source bytes
not stored**). It distinguishes checkpoint-declared
`compressed-tensors` `mixed-precision` from
NVIDIA's `ModelOptMixedPrecisionConfig` patch, and
does not claim the native `Fp8Config` branch is
reachable, that the global BF16 scale is loaded,
or that GB10 TP=1 is supported.
No model weights, Docker or GPU activity is performed.
Tests use fully synthetic offline triplets. The profile
remains non-installable; any real adapter/image change
needs a separately approved operation.

### lychee888 nominal unified memory size metadata warning

The pinned `assess_lychee888_loader.py` also emits
`indexed_tensor_bytes`,
`dgx_spark_nominal_unified_bytes` and
`full_resident_nominal_memory_screen`.
Only an index `metadata.total_size` positive
integer counts; missing/invalid metadata is
`NOT_VERIFIED`. 128 GB is hardware *nominal
unified memory*, not current free or usable
CUDA allocations. Even a below-limit index
cannot prove runtime fit. This analysis is
source-only, with no Docker/GPU or weight loads.
