# Actual DGX S1 — storage inventory (2026-10-13)

Evidence class: ACTUAL_DGX, user-provided terminal log.
Checkout: 513623243c12c204378a0e22bb965ff47542f4f9
Host logfile: /home/inlc/dgx-bench-before-reclaim-20261013-132825.log
SHA256 of uploaded pasted-text bytes (not verified on-host log):
64d4d88aa79c5cea704246dfeb6ca534e32951e8f6c38903eea25995d51b0399

## Command outcomes

~~~text
RECLAIM_CHECK=filesystem rc=0
RECLAIM_CHECK=storage_status rc=0
RECLAIM_CHECK=storage_recommend rc=0
RECLAIM_CHECK=storage_plan_preview rc=0
RECLAIM_CHECK=managed_model_assets rc=0
RECLAIM_CHECK=docker_disk_accounting rc=0
RECLAIM_CHECK=docker_image_identity rc=0
RECLAIM_CHECK=docker_container_identity rc=0
RECLAIM_READONLY=COLLECTED
BENCHMARK_BEFORE_RECLAIM=REQUIRED
MODEL_OR_DOCKER_DELETION=BLOCKED_PENDING_MODEL_EVIDENCE_AND_ASSET_REVIEW
~~~

Eight of eight read-only commands passed; no model started,
deleted, benchmarked or downloaded. No removal is authorized.

## Actual filesystem and managed checkpoint inventory

| Checkpoint / asset | Individual directory size | Caution |
|---|---:|---|
| Original OrcaRouter | 171G | active, protected |
| Original mazinb | 174G | inactive, preserve pending benchmark |
| H3 quant-layout | 73G | H4/H6 ancestor |
| H4 orca-all | 64G | H5/H6 ancestor |
| H5 neutral-input | 43M | H6 ancestor |
| H6 w4a16 | 34M | final small dependent directory |
| Hugging Face cache | 471M | report only |
| Immutable release data | 921M | current and previous protected |
| PLE swap | 128G logical /129G disk use | active, protect |

Physical disk /dev/nvme0n1p2: 916G size, 765G used,
105G free, 88% utilization.
Nominal H3+H4 sizes total 137G; with mazinb, 311G.
**Not proven independently reclaimable bytes.** Separate du
estimates may double count hardlinks; reflinks, sparse extents,
shared inodes and CoW snapshots are not independently verified.

The actual model asset registry declares H6 checkpoint dependencies
on H5, H4, H3 and OrcaRouter; H5 depends on H4/H3/OrcaRouter,
H4 on H3/OrcaRouter, H3 on OrcaRouter. Small H6 size does
**not** demonstrate it can load or be reconstructed after deleting
large intermediates. Source code also uses mazinb tensors to
construct H3; do not invent a direct H6 runtime dependency on
mazinb without inspecting effective model data.

Installed manifest image: vllm-skinny-tp1:v1. The registry's
OrcaRouter H38 image mapping is a distinct prospective target,
not the currently installed image.

## Docker physical accounting and external applications

~~~text
Images       10, all referenced, 47.22GB total, 0B reclaimable
Containers   24, 2 active, 6.285GB writable, 6.239GB reclaimable
Build cache  127 entries, 1.163MB total, 7.433kB reclaimable
Volumes      3, 34.16kB total, 0B reclaimable
~~~

R25/R26/R27/R28 and H38 images each show approximately
22.1GB logical size but share ~22.05GB base layers;
unique image portions 0B–233.6kB. The v0.29 base has
15 stopped-container references. Docker image removal cannot
be assumed to free the logical image size.

The default prune command was previewed only; it proposes
20 stopped Qwen experiment containers including H38,
mazinb and Hybrid tests. Their writable layers may contain
valuable debugging/provenance data; archive before any
specific cleanup. The canonical qwen38-flash-next Docker
predecessor is stopped but preserved, and was NOT in the
preview deletion list.

Nonproject services Open WebUI and Portainer were running.
Do not remove their containers, images or volumes.

## Gate outcomes and next step

- S1 physical read-only storage inventory = PASS
- Five user-model llama-benchy reports = NOT_MEASURED
- M1 actual managed live runtime = NOT_QUALIFIED
- M2 destructive = NOT_RUN; M3 live pairs = NOT_QUALIFIED
- H38/M4 = BLOCKED; D0 independent disposable = NOT_GRANTED
- Actual model/Docker removal = NOT_PERFORMED

Next: guarded exact-SHA no-delete filesystem-block/link accounting
on the REAL model root with inspect-hybrid-reclaim-blocks.sh.
Even a PASS does not prove CoW shared extent reclaimability.
Do not delete H3/H4 until H6 dependency and recovery/rebuild
safety, quantitative benchmark archival and a separate specific
per-asset decision are addressed.
