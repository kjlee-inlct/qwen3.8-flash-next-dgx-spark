# H38 CT expert/shard destination and unique coverage — source-only gate (2026-10-11)

## Why this next gate exists

The operator already qualified two separate exact-image source-only gates under fixed H38 image ID `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`:

- [CT eight-registration/Layerwise/RoutedExperts source Attempt 03 PASS](orcarouter-h38-ct-layerwise-accounting-attempt03-source-pass-20261011.md) at exact operator HEAD `5fa4265d394255744f8886b857804a28c433cf3f`.
- [CT input-scale postconstruction attribute Attempt 01 PASS](orcarouter-h38-ct-scale-attr-attempt01-source-pass-20261011.md) at exact operator HEAD `1865521c2ff58add7bddeed6735c76803a3e3637`.

Both are **source contracts only**. In particular, counting `aten.copy_` destination elements per loader invocation and then accumulating to a layer threshold cannot logically prove unique coverage if callbacks overlap. A separate external CPU PyTorch toy supported that general possibility without measuring the installed H38 loader; see [external CPU toy](h38-ct-copycounter-indexed-write-external-cpu-toy-20261011.md).

The next question is therefore which *potential destination* each routed expert/shard event may affect. **A static source branch map is a prerequisite, not an actual 512-expert coverage trace.**

## New repository code (not yet observed in H38)

- `scripts/benchmark/inspect-h38-ct-expert-destination-source.py`: Python standard-library AST-only inspection. Requires exact preapproved SHA256 pins for CT, RoutedExperts, reload/layerwise and reload/meta. Reads no checkpoint names/payload and does not import `torch` or vLLM.
- `scripts/benchmark/check-h38-ct-expert-destination-source.sh`: exact clean checkout and immutable H38 image-ID/H11-H12-H38 label gates, read-only `runc` with `--pull never --network none --cap-drop ALL --security-opt no-new-privileges --user 65534:65534 --memory 512m --memory-swap 512m --cpus 1 --pids-limit 64`. No H38 model/GPU execution or managed-service/host protection change.
- `tests/test_h38_ct_expert_destination_source.py`: synthetic normal/negative AST fixtures and wrapper restrictions; CI is **not** an in-image observation.

## Candidate source-driven destination table — pending image-specific source check

The inspector encodes a *conditional interpretation* that must be validated as AST anchors in the pinned installed image. Actual checkpoint name matches, runtime branch selections, local physical expert numbering, TP slicing, padding and copy events remain **UNVERIFIED**.

| CT registration | Logical checkpoint shard candidates | Source helper / possible destination |
|---|---|---|
| `w13_weight_packed` | w1 / w3 | `_load_w13`: first/second logical packed half of each selected expert |
| `w2_weight_packed` | w2 | `_load_w2`: down projection region |
| `w13_weight_scale` | w1 / w3 | `_load_w13`: first/second logical grouped-scale half |
| `w2_weight_scale` | w2 | `_load_w2`: down-projection grouped scale |
| `w13_weight_global_scale` | w1 / w3 | `_load_per_tensor_weight_scale`: expert cell index 0/1 if TENSOR branch |
| `w2_weight_global_scale` | w2 | `_load_per_tensor_weight_scale`: per-expert scalar if TENSOR branch |
| `w13_input_global_scale` | w1 / w3 | generic `_load_single_value` assigns an **expert row**; ModelOpt special branch may address index 0/1 instead |
| `w2_input_global_scale` | w2 | `_load_single_value`: per-expert scalar/row |

Particular caution: the generic input-scale branch has equality/conflict conditions for compressed quant methods and may return/throw before writing. A w1/w3 row-overwrite inference must not be promoted to observed duplicate loading, a successful broadcast, or a claim of equivalent input scales without an actual safe trace of the resolved branch and tensor shapes. Source checks will capture existence of this conditional rather than report successful writes.

## Source distinctions that could change the actual mapping

1. **Checkpoint names and fusedness:** `RoutedExperts.load_weights` matches checkpoint names to `get_expert_mapping(include_fused=True)`, recognizes 3-D fused tensors, and handles fused gate/up patterns separately. Source-syntactic name matching does not enumerate the actual OrcaRouter checkpoint names or give event counts.
2. **Expert parallelism:** `weight_loader` maps global expert ID to local ID and may skip nonlocal experts, with a `use_global_sf` conditional for input scales. Neither EP/TP configuration nor `512` physical destination rows can be presumed from the AST alone.
3. **Projection packing:** `_load_w13` narrows separate w1/w3 halves (with TP padding/slicing), whereas `_load_w2` copies a down-projection region. Existence of a copy site does not establish that a particular checkpoint tensor arrived, or a unique loaded range.
4. **Global scales:** TENSOR helper explicitly writes w1/w3 scalar indices 0/1 and the w2 per-expert value. Generic input-scale helper may write a broader row; these are not interchangeable with the actual `CopyCounter` copy event semantics.
5. **Layerwise completion:** counted `copy_` aggregate reaching `get_layer_size` can be a different condition from unique required destination coverage. The source audit does **not** prove an unsafe early completion actually occurred.

## Next acceptance criteria

A real operator output from the exact clean CI-qualified HEAD, using the new guarded read-only inspector, may establish:
- pinned source hashes still match;
- all checked source branch anchors are present;
- an eight-family **source-conditioned destination hypothesis map** and method line references;
- image identity preserved; no GPU/model/checkpoint read.

The pass marker will be `H38_CT_EXPERT_DESTINATION_PREFLIGHT=PASS_SOURCE_BRANCHES_ONLY`. This is **not** a real checkpoint-to-parameter index map, not a verified 512-expert load trace, and not a new memory bound. An `INVALID` result requires preserving the exact first mismatching AST anchor; do not weaken source pins or start the model.

**Do not run H38 GPU/model, patch CT meta, rebuild the image, scan checkpoint payload, alter host memory defenses/managed services, mark PR #259 Ready, or merge.** Existing `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `HOST_STABILITY=INCONCLUSIVE`, `RM_MITIGATION=UNPROVEN`, `CT_WEIGHT_COMPLETENESS=UNVERIFIED`, `COPYCOUNTER_SCALE_CREDIT=UNVERIFIED` are unchanged.


## Actual installed-image DGX source audit — Attempt 01 PASS (2026-10-11)

**This observed result supersedes the earlier staging/PENDING wording above; the source-branch scope remains unchanged.** The operator fast-forwarded the clean checkout to fd4221b5bdb2b95ad83f94255ee2740cea842c9e and executed the guarded H38 image-source inspector against immutable image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc. All four previously pre-pinned installed H38 source SHA256 digests matched.

- H38_CT_EXPERT_DESTINATION_SOURCE=PASS_SOURCE_BRANCHES_ONLY
- H38_CT_EXPERT_DESTINATION_PREFLIGHT=PASS_SOURCE_BRANCHES_ONLY
- source_check_rc=0, image_identity_unchanged=YES; no GPU/model/checkpoint payload read, image/host protection/managed service/CT meta mutation.
- 11/11 expert name/fused/full/expert-ID mapping/callback predicates, 7/7 packed/group projection destination predicates, 11/11 TENSOR/input/global scale predicates all TRUE.
- Eight-family source-conditioned destination table and method-line provenance captured in [actual operator Attempt 01 PASS evidence](orcarouter-h38-ct-expert-destination-attempt01-source-pass-20261011.md). The provided terminal transcript is preserved as the evidence origin, not a SHA256-audited byte-for-byte /tmp log.

**The new source audit does not close real-loading gates.** The inspector prints the actual input scale values/conflict, real checkpoint name-to-parameter matches, actual expert-ID mapping, real dispatch copy counts, unique real destination coverage, and layer 8/11 buffer/lifetime as UNVERIFIED. A source AST can identify branches but not count actual destination writes, infer global/local expert cardinality or prove a finite memory bound.

**Conditional branch concern:** the fixed-image RoutedExperts source (SHA identical to vLLM v0.29.0 upstream for this file) includes a generic compressed input-scale conflict check with a Python Boolean of a Tensor comparison. In a hypothetical execution with a multi-element w13 input row, that predicate may raise an ambiguous truth-value exception before writing. This is an identified conditional source hazard, **not** a reproduced H38 failure; see PR #259 comment 6105299781 and the canonical PASS evidence.

Next gate is to review **existing** no-payload checkpoint metadata-only tools and qualified prior metadata evidence, then design a unique key/expert/shard reconciliation test on synthetic manifests. Do not start the H38 runtime, weaken host memory protection, scan checkpoint payload, modify the pinned image, implement CT meta, mark PR Ready or Merge. CHECKPOINT_METADATA_ORDER_GATE=FAIL remains unchanged.
