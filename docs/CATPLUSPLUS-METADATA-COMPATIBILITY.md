# catplusplus mixed-NVFP4 — metadata and GB10 compatibility

Status 2026-10-16: RESEARCH_ONLY / NOT_REGISTERED / NOT_DOWNLOADED / GPU_NOT_TESTED.
Target: catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed
Pinned revision from DGX owner: 3251fd8afbd08f76368a9bfa71132d9aef364813.

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

## Next read-only operator check — Wizard-first

After a clean source checkout fast-forward, open the operator Wizard:

    ./wizard.sh

Choose **3 — Models / switch preview → 11 — Candidate Hub metadata
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

1. Capture actual pinned API/tree/config/index; reconcile 63.88 GiB and
   HF ~189 GB by exact filename and byte accounting.
2. Read safetensors headers later under a separate reviewed procedure.
   Check MXFP8 E8M0 scale, fused qkvz alias, ModelOpt mixed dispatch,
   NVFP4 expert and global FP8 PLE scale consumers in a pinned backend.
3. Establish peak memory for one GB10 including weights, PLE staging,
   cache, KV, draft, CUDA graphs and watchdog safety reserve.
4. Do not register or offer this profile as installable until qualified.
   No bulk download, GPU launch, Docker mutation or PR transition approved.
