# Actual DGX protected OrcaRouter mount/config read-only inspection — 2026-10-18

**Evidence class:** `ACTUAL_DGX_OPERATOR_TERMINAL`. Source HEAD
`2812aa01fdc33d7d4b6b52cdc6e7a1ecec038948`,
`feature/wizard-modular-phase1-20261014`;
operator's terminal output included
`EXACT_HEAD_CI=SUCCESS_2_OF_2`.
The exact protected mount-based tool ran successfully after
the previous **false-negative guessed model path**.

```text
ORCA_CONFIG_OPERATION=DOCKER_INSPECT_AND_SMALL_CONFIG_READ_ONLY
ORCA_CONFIG_DOCKER_MUTATION=NONE
ORCA_CONFIG_WEIGHTS_READ=NONE
ORCA_CONFIG_GPU_RUN=NOT_PERFORMED
ORCA_CONFIG_ORIGINAL_CONFIG_SOURCE=PROTECTED_CONTAINER_BIND_NOT_GUESSED_HOME
ORCA_CONFIG_PROTECTED_CURRENT_CHECK=PASS_CURRENT_ONLY
ORCA_CONFIG_MANAGED_MOUNT=EXACT_PROTECTED_RO_BIND
ORCA_CONFIG_MANAGED_MODEL_ROOT=DIRECTORY_READABLE
ORCA_CONFIG_MANAGED_ORIGINAL_CONFIG=REGULAR_BOUNDED_FILE
ORCA_CONFIG_MANAGED_OVERRIDE_CONFIG=REGULAR_BOUNDED_FILE
ORCA_CONFIG_LEGACY_MOUNT=EXACT_PROTECTED_RO_BIND
ORCA_CONFIG_LEGACY_MODEL_ROOT=DIRECTORY_READABLE
ORCA_CONFIG_LEGACY_ORIGINAL_CONFIG=REGULAR_BOUNDED_FILE
ORCA_CONFIG_LEGACY_OVERRIDE_CONFIG=REGULAR_BOUNDED_FILE
ORCA_CONFIG_MODEL_SOURCES=MATCH
ORCA_CONFIG_OVERRIDE_SOURCES=MATCH
ORCA_CONFIG_CONFIG_REWRITE=EXACT_EXPECTED_LAYER_TYPE_REWRITE
ORCA_CONFIG_ORIGINAL_LAYER_TOTAL=48
ORCA_CONFIG_ORIGINAL_LINEAR_ATTENTION=36
ORCA_CONFIG_ORIGINAL_FULL_ATTENTION=0
ORCA_CONFIG_ORIGINAL_QUANT_STRUCTURE=CT_STRUCTURE_READABLE
ORCA_CONFIG_ORIGINAL_CT_GROUPS=2
ORCA_CONFIG_ORIGINAL_CT_TARGETS=301
ORCA_CONFIG_ORIGINAL_CT_IGNORED=753
ORCA_CONFIG_OVERRIDE_LAYER_TOTAL=48
ORCA_CONFIG_OVERRIDE_LINEAR_ATTENTION=36
ORCA_CONFIG_OVERRIDE_FULL_ATTENTION=12
ORCA_CONFIG_OVERRIDE_QUANT_STRUCTURE=CT_STRUCTURE_READABLE
ORCA_CONFIG_OVERRIDE_CT_GROUPS=2
ORCA_CONFIG_OVERRIDE_CT_TARGETS=301
ORCA_CONFIG_OVERRIDE_CT_IGNORED=753
ORCA_CONFIG_COMMUNITY_LAYER_SHAPE=COUNTS_MATCH_NOT_CONFIG_EQUIVALENCE
ORCA_CONFIG_VERDICT=PASS_SOURCE_CONFIG_ONLY_NOT_RUNTIME
ORCAROUTER_CONFIG_PREFLIGHT=COMPLETED
```

## Verified physical facts

1. The exact stopped protected Docker containers passed the **current-only**
   image/identity/mount guard. Both use the same model source and same
   override bind source, and both on-host original and override
   `config.json` files are readable bounded regular files. The previous
   `STOP: Original config missing` had been from a **guessed**
   home-directory path, **not** evidence of lost model files.
2. The applied override is **exactly** the result of the maintained
   `prepare_config.convert_layer_types(original)` transformation.
   The original 48 entries included 36 `linear_attention` and
   12 `qwen_sparse_attention` (the latter inferred from
   successful exact rewrite and the reported override counts);
   the override has 36 `linear_attention` plus 12 `full_attention`.
3. Model quantization config shape: `compressed-tensors`
   group count **2**, target entries **301**, ignore entries **753**
   in both original and override. The community pasted config
   has the same **counts** (300 FP8 explicit targets + 1 NVFP4
   experts regex and 753 ignores), and 36/12 layer counts.
   **No exact group-content, ignore-list or layer-ordinal
   equality was attested in this first physical run**.
4. No weights/safetensors headers, Docker creation/start/stop/copy,
   GPU execution, network model pull, or model READY probe occurred.

## Differential decision and next step

**Community matching flags already in maintained `serve.sh`:**
TP1/mp, CPU PLE offload with 1800s wait (legacy),
MTP2, 262K configured max, concurrency 3,
8192 batched tokens, chunked prefill,
cache-disabled settings, NVIDIA/CUTE/FlashInfer
environment, 32GiB shm, IPC host, memlock, cap
permissions and tool/reasoning parsers.
Our 16GiB KV reflects prior strict host-stability
tests and **must not be increased** because a peer used 24GiB.

Actual distinguishing candidate:
`vllm/vllm-openai:qwen38-flash-next-arm64-cu130`,
which the owner's prior read-only check reported
`OFFICIAL_IMAGE_LOCAL=NOT_PRESENT`.
That image's vLLM allocator/decoder/CUDA/PLE
source has not been compared or qualified for our
GB10. No `docker pull` or `docker run` authorized.

A source-only enhancement computes canonical
sorted-key SHA256 of the **full third-party posted
config JSON** and seven subtrees (full, quant,
CT groups, ignore list, text, exact ordered layers,
vision) from the user-uploaded 1304-line reference.
It checks the protected override *privately* and
prints **MATCH / DIFFERENT / MISSING** labels without
publishing source contents, paths or host-derived
hashes. This updated tool has **NOT YET BEEN RUN**
on the physical DGX; its results must not be
confused with the verified counts-only run.

**Status:** `ORCAROUTER_MOUNTED_CONFIG_CURRENT=PASS`,
`CONFIG_OVERRIDE_EXACT_REWRITE=PASS`,
`REFERENCE_CT_COUNTS=PARITY_ONLY`,
`EXACT_THIRD_PARTY_CONFIG_PARITY=NOT_MEASURED`,
`ORCAROUTER_GPU_REPRODUCIBLE_STABLE=NOT_QUALIFIED`.
Keep original monitor, protected image/container
and historical NVRM evidence untouched.

## Follow-up physical digest-parity run — 2026-10-18 (operator transcript)

**Provenance:** `ACTUAL_DGX_OPERATOR_TERMINAL`, copied by the owner from
`inlc@lc-gx10-pc:~/Workspace/llm/qwen3.8-flash-next-dgx-spark`.
Invoked `python3 -B scripts/model/inspect_orcarouter_mount_config_readonly.py`
and returned to the shell prompt with the following visible verdicts.
**The pasted transcript does not include `git rev-parse HEAD`, clean worktree,
remote SHA, exit status, or exact-HEAD CI output**. The latest *GitHub-side*
branch SHA checked separately is not proof of the physical checkout SHA.
Do not retrospectively assign an exact on-host execution commit from the
repository state; source pinning is `HOST_HEAD_NOT_CAPTURED_IN_THIS_TRANSCRIPT`.

```text
ORCA_CONFIG_OPERATION=DOCKER_INSPECT_AND_SMALL_CONFIG_READ_ONLY
ORCA_CONFIG_DOCKER_MUTATION=NONE
ORCA_CONFIG_WEIGHTS_READ=NONE
ORCA_CONFIG_GPU_RUN=NOT_PERFORMED
ORCA_CONFIG_ORIGINAL_CONFIG_SOURCE=PROTECTED_CONTAINER_BIND_NOT_GUESSED_HOME
ORCA_CONFIG_PROTECTED_CURRENT_CHECK=PASS_CURRENT_ONLY
ORCA_CONFIG_MANAGED_MOUNT=EXACT_PROTECTED_RO_BIND
ORCA_CONFIG_MANAGED_MODEL_ROOT=DIRECTORY_READABLE
ORCA_CONFIG_MANAGED_ORIGINAL_CONFIG=REGULAR_BOUNDED_FILE
ORCA_CONFIG_MANAGED_OVERRIDE_CONFIG=REGULAR_BOUNDED_FILE
ORCA_CONFIG_LEGACY_MOUNT=EXACT_PROTECTED_RO_BIND
ORCA_CONFIG_LEGACY_MODEL_ROOT=DIRECTORY_READABLE
ORCA_CONFIG_LEGACY_ORIGINAL_CONFIG=REGULAR_BOUNDED_FILE
ORCA_CONFIG_LEGACY_OVERRIDE_CONFIG=REGULAR_BOUNDED_FILE
ORCA_CONFIG_MODEL_SOURCES=MATCH
ORCA_CONFIG_OVERRIDE_SOURCES=MATCH
ORCA_CONFIG_CONFIG_REWRITE=EXACT_EXPECTED_LAYER_TYPE_REWRITE
ORCA_CONFIG_ORIGINAL_LAYER_TOTAL=48
ORCA_CONFIG_ORIGINAL_LINEAR_ATTENTION=36
ORCA_CONFIG_ORIGINAL_FULL_ATTENTION=0
ORCA_CONFIG_ORIGINAL_QUANT_STRUCTURE=CT_STRUCTURE_READABLE
ORCA_CONFIG_ORIGINAL_CT_GROUPS=2
ORCA_CONFIG_ORIGINAL_CT_TARGETS=301
ORCA_CONFIG_ORIGINAL_CT_IGNORED=753
ORCA_CONFIG_OVERRIDE_LAYER_TOTAL=48
ORCA_CONFIG_OVERRIDE_LINEAR_ATTENTION=36
ORCA_CONFIG_OVERRIDE_FULL_ATTENTION=12
ORCA_CONFIG_OVERRIDE_QUANT_STRUCTURE=CT_STRUCTURE_READABLE
ORCA_CONFIG_OVERRIDE_CT_GROUPS=2
ORCA_CONFIG_OVERRIDE_CT_TARGETS=301
ORCA_CONFIG_OVERRIDE_CT_IGNORED=753
ORCA_CONFIG_COMMUNITY_LAYER_SHAPE=COUNTS_MATCH_NOT_CONFIG_EQUIVALENCE
ORCA_CONFIG_PEER_FULL_PARITY=MATCH_REFERENCE_CANONICAL_VALUES
ORCA_CONFIG_PEER_QUANT_PARITY=MATCH_REFERENCE_CANONICAL_VALUES
ORCA_CONFIG_PEER_GROUPS_PARITY=MATCH_REFERENCE_CANONICAL_VALUES
ORCA_CONFIG_PEER_IGNORE_PARITY=MATCH_REFERENCE_CANONICAL_VALUES
ORCA_CONFIG_PEER_TEXT_PARITY=MATCH_REFERENCE_CANONICAL_VALUES
ORCA_CONFIG_PEER_LAYERS_PARITY=MATCH_REFERENCE_CANONICAL_VALUES
ORCA_CONFIG_PEER_VISION_PARITY=MATCH_REFERENCE_CANONICAL_VALUES
ORCA_CONFIG_PEER_REFERENCE_SCOPE=THIRD_PARTY_POSTED_JSON_NOT_IMAGE_RUNTIME
ORCA_CONFIG_VERDICT=PASS_SOURCE_CONFIG_ONLY_NOT_RUNTIME
```

**Finding:** the actual mounted OrcaRouter override's *canonical
JSON value* matches the complete operator-pasted third-party reference
in `full`, `quant`, `groups`, `ignore`, `text`, ordered
`layers` and `vision` digests (7/7). Canonical sorting ignores
JSON object-key order and formatting but **preserves array order**.
This supersedes the earlier *counts-only* uncertainty for that
reference JSON, while preserving the earlier evidence unchanged.
The original-to-override narrow layer-type rewrite is separately exact.

**Limits:** comparator pass is `PASS_SOURCE_CONFIG_ONLY_NOT_RUNTIME`;
it cannot authenticate the community's checkpoint provenance, establish
weight-byte/tensor identity, attest the vLLM package inside either
image, or prove startup/READY, API inference, strict RM stability or
KV24 acceptance. The 2026-10-18 reference hashes were embedded in
GitHub source; they authenticate parity to *that pasted JSON*, not
an independently fetched signed upstream checkpoint. No Docker mutation,
weight read or GPU run was reported. The remaining prominent
investigation is the exact embedded official ARM64 CUDA13 vLLM
and NVIDIA RM early-allocation behavior; no image pull or live run approved.
