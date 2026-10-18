## 2026-10-18 — catplusplus M0 benchmark plan is source-only (NOT MEASURED)

Owner prioritized preparing catplusplus comparison ahead of further
OrcaRouter C GPU work, while retaining P0 Wizard-first install/switch.
The pinned L0 tree metadata (`3251fd8afbd08f76368a9bfa71132d9aef364813`)
already established **188,540,029,444 repository bytes (175.59158564 GiB)**
and **about 174.8553 GiB root weights** on the actual DGX.
A simple 128GB single-GB10 fully resident unchanged-weight load
is impossible without special offload/residency design.

**GitHub SOURCE-ONLY M0:** Added `scripts/benchmark/catplusplus-plan.py`
and Wizard Benchmark **5 -> 22** read-only plan, plus synthetic
tests and `llama-benchy-report.py` profile label support for
future **actual** measured JSON. Baseline shape matches physical mazinb
M1: PP512/TG128 and PP2048/TG128, concurrency1, 1 warmup + 3 runs,
pinned upstream benchy `e9be344578cec17745066b220798b80a0d2686d3`.
Every catplusplus throughput/latency stays `NOT_MEASURED`.

**Still blocked:** exact MXFP8 fused qkvz/scale, ModelOpt mixed NVFP4
and FP8 PLE loader source compatibility, bounded offload/host RM
memory reserve, model payload availability, separate download
and GPU-start authorization, isolated protected lifecycle.
No checkpoint downloaded, no Docker/GPU, no new model registered
or switched. [Detailed M0 plan](model-reports/catplusplus.md).

# catplusplus mixed-NVFP4 — metadata and GB10 compatibility

Status 2026-10-16: RESEARCH_ONLY / NOT_REGISTERED / NOT_DOWNLOADED / GPU_NOT_TESTED.
Target: catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed
Pinned revision from DGX owner: 3251fd8afbd08f76368a9bfa71132d9aef364813.

## 2026-10-16 actual DGX pinned full-tree inventory — L0 metadata PASS

**ACTUAL_DGX / Hub API JSON / Wizard 3 → 7 → 1, owner-captured output.**
The read-only inspector was re-run after the compact-paging source fix
on immutable Hugging Face revision
`3251fd8afbd08f76368a9bfa71132d9aef364813`.
It reported `TREE_METADATA_COMPLETE`, `legacy_tree_reconciliation_complete=True`,
`GPU_RUN=NOT_PERFORMED`, and page progress at 1/10/20, ending with
17,448 repository files, including 96 `.safetensors` files and
96 weight filenames referenced by the safetensors index. Config and
index JSON were retrieved and validated at that exact revision,
but this operator output did **not** display per-tensor config values,
headers, dtype, shape or weight payload checksums.

**Exact reconciliation from physical summary output:**

| Scope | Decimal bytes | Binary GiB | What the probe proves |
|---|---:|---:|---|
| Legacy API `siblings[].size` subtotal | 68,586,923,924 | 63.876550574 | Previously reported 63.88 GiB |
| Additional full-tree files absent from legacy siblings | 119,953,105,520 | 111.715035066 | The omitted file inventory, **not unknown-size entries** |
| **Complete repository** | **188,540,029,444** | **175.591585640** | **188.540029444 decimal GB**, consistent with Hub UI ~189 GB |
| Root `.safetensors` only | Rounded by probe | 174.8553 | Data on disk, **not** measured resident memory |

`legacy_siblings_unknown_size_entries=0` and
`legacy_missing_size_recovered_tree_bytes=0`; the mismatch arose
from **files omitted from the old sibling listing**, not LFS size fields
being null. This supersedes the earlier **unresolved** and
**missing-size hypothesis** sections below, which are retained as dated
historical evidence only. The reported 96 index filenames is metadata
mapping count; it does not establish file content or actual loader support.
The exact root-safetensors byte total and per-path breakdown were not
printed by the summary view; retain that precision distinction rather
than reverse-engineering exact values from rounded GiB.

**Single GB10 capacity screen — planning inference, not live load:**
NVIDIA specifies 128 **decimal GB** coherent unified RAM on DGX Spark,
approximately 119.21 GiB. The **stored root safetensors alone** are
about 174.86 GiB (~187.75 decimal GB), exceeding total unified
physical capacity by about 55.65 GiB (59.75 decimal GB) even before
runtime memory, KV cache, CUDA buffers and monitor reserve. Thus a
simple fully resident, unchanged-weight TP=1 load does **not** fit.
This comparison cannot rule out separately engineered partial residency,
mmap, CPU/NVMe paging or further quantization, and it does not prove
runtime performance or stability. Publisher's separate Thor result is
not a DGX Spark TP=1 proof. **Do not download weights or try a GPU
launch** on the basis of the metadata PASS.

**Disposition:** Reconciliation L0 complete. Candidate remains
`RESEARCH_ONLY / NOT_INSTALLABLE / GPU_NOT_TESTED`. Next actions are
source/architecture-level comparisons with lychee888 and a bounded
memory-residency/loader compatibility assessment. Preserve the exact
owner-captured output as this record; a full 17,448-path inventory was
not attached to this evidence and should not be claimed as archived.

## Separate evidence tiers

**Historical physical DGX remote inspection:** The existing generic remote
inspector reported 63.87655057385564 GiB, architecture/model_type/
quantization_method=null, safetensors_files=0. SOURCE inspection establishes
that its remote path sums only non-null siblings[].size and does not fetch
config.json, inspect file headers or list full tree metadata. The absent
fields do not mean the checkpoint has no weights.

**Publisher / public HF website, not pinned API confirmation:** The visible
file-browser tree reports ~189 GB and individual experts-layerNN.safetensors
files near 1.42 GB. The card claims an FP8 PLE table (~47.7 GB),
NVFP4 expert tensors, MXFP8 selected projections, BF16-preserved dense
components, and a separate single-Thor serving result. Current main-branch
web config shows Qwen4ExpForConditionalGeneration / qwen4_exp,
quant_method=modelopt_mixed, quant_algo=MIXED_PRECISION, NVFP4 / MXFP8
per-layer quantization, and text_config.ple_embedding_dtype=float8_e4m3fn.
This main config must still be checked at the immutable target revision.
The author identifies fused linear_attn.in_proj_qkvz name mapping and
scale handling as a correctness-critical SGLang loader dependency.
Publisher benchmarks and stock startup examples do not qualify our DGX.

**Current project GitHub SOURCE:** serve.sh and model-profiles.sh lack a
catplusplus path. The NVIDIA MIXED_PRECISION adaptation is not proof of
MXFP8 fused-projection support in catplusplus. Newly added
scripts/model/inspect_catplusplus_metadata.py reads pinned Hub revision,
paginated complete file tree, config and optional safetensors index as
JSON only; it does not download weights or start a process on GPU.
It reports file-by-file sizes/LFS/Xet hints, legacy API known-size subtotal
and missing-size count, root safetensors and full repository sizes, optional
index referenced bytes, quant algorithm counts and fused aliases.
Unknown sizes remain unknown. The checker also partitions repository
bytes into three disjoint sets: (1) known legacy sibling sizes, (2) files
whose legacy size was NULL but the pinned tree supplies a size, and
(3) full-tree files absent from legacy siblings. It rejects duplicates,
contradictory sizes, missing API-tree filenames and an unbalanced partition.
Synthetic/offline fixtures check these reconciliation invariants.

**Provisional size clue, NOT a resolved discrepancy:** The public listing
shows experts-layer files near 1.42 decimal GB each; 48 such layers would
account for roughly 68.16 decimal GB (about 63.48 GiB), numerically
close to the old reported 63.88 GiB. Per-file values are rounded and this
does not establish what the old API actually counted, nor whether a
PLE table and other weights/extra sources were omitted. Only the pinned
full-tree reconciliation can make that determination.

The new script's actual pinned Hub output and GitHub CI must be recorded
separately; source presence alone does not mean the 189GB reconciliation
has already passed.

## 2026-10-16 physical DGX read-only metadata attempt

After fast-forwarding to `22bcba4711ee423ffea062268f4b8de3366938e1`,
the owner used Wizard **3 → 7 → 1** with manifest valid, profile
orcarouter and image `vllm-skinny-tp1:v1`. The JSON-only inspection
returned `CATPLUSPLUS_METADATA_FAIL: tree pagination repeated or exceeded
100 pages`. It did not reach file inventory validation. No weights were
downloaded or model loader exercised. The former implementation used
`recursive=true&expand=true`, with one combined guard for repeating URLs
or more than 100 pages. The original error cannot distinguish which
case occurred. Hugging Face documents that `expand=true` is a costly
request limited to ~50 entries/page, versus up to 1000 per page without
expansion. That motivates compact pagination; it does NOT independently
prove the exact cause of this DGX failure.

GitHub SOURCE change: use `recursive=true&expand=false&limit=1000`,
with exact pinned revision, validated pagination links, independent
repeated-URL/repeated-path/empty-page/256-page fail-closed errors,
plus periodic read-only progress output. Synthetic fixtures simulate
more than 100 unique pages without downloading checkpoints. The corrected
path still requires a NEW physical Hub run to establish its actual
file count and 63.88-GiB versus ~189-GB byte reconciliation. Do not
mislabel a synthetic success as a real Hugging Face validation.

## Completed operator procedure — Wizard-first (metadata L0 only)

After a clean source checkout fast-forward, open the operator Wizard:

    ./wizard.sh

Choose **3 — Models / switch preview → 7 — Candidate Hub metadata
(read-only) → 1 — catplusplus summary**. Select 2 in the same submenu
for the complete JSON file inventory printed to the terminal; 0 returns.
The Wizard invokes the pinned standard-library inspector internally and
never downloads safetensors, changes model installability, starts GPU
services or modifies Docker. A failure remains inconclusive and does not
admit a candidate. The standalone Python command remains an internal
developer/test entry point, **not the recommended operator workflow**.

Capture verdict, missing-size file names, entire file_inventory,
all_repository_bytes, root_safetensors_bytes and
index_referenced_weight_bytes. A missing index means that selective
inference download requirements remain unresolved. Compare byte totals
before converting to GB or GiB. Source/git bundles and duplicate/unused
files must be considered independently. Complete repository byte count
is not necessarily the minimum inference download or physical peak RAM.

## Outstanding admission gates

1. **DONE (aggregate accounting):** Pinned Hub API/tree/config/index
   validated on DGX and the 63.88-GiB versus ~189-GB discrepancy
   reconciled by missing legacy sibling **filenames**, not sizes.
   Full per-path evidence was not captured; only request it if needed
   for a specific loader/memory question, without printing 17k paths to
   the operator terminal.
2. Read safetensors headers later under a separate reviewed procedure.
   Check MXFP8 E8M0 scale, fused qkvz alias, ModelOpt mixed dispatch,
   NVFP4 expert and global FP8 PLE scale consumers in a pinned backend.
3. Establish peak memory for one GB10 including weights, PLE staging,
   cache, KV, draft, CUDA graphs and watchdog safety reserve.
4. Do not register or offer this profile as installable until qualified.
   No bulk download, GPU launch, Docker mutation or PR transition approved.
