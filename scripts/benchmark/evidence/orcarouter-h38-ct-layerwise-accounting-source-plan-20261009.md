# H38 CT packed/scale layerwise accounting — source-only plan, 2026-10-09

Status: **SOURCE-ONLY INSPECTOR STAGED / SYNTHETIC TESTS STAGED / EXACT INSTALLED-H38 EXECUTION PENDING**. No live model/GPU test, deferred-meta patch, mitigation claim or host-stability qualification.

## Evidence and original source lineage

Earlier guarded exact-H38-source checks proved that H11 ModelWeightParameter packed-storage registration, H12 object-preserving aliases and native layerwise machinery exist. They did NOT prove that every routed expert and all scales are loaded before finalization, or establish the live buffer lifetime.

The production safetensors metadata-only Attempt 03 found routed base layer 8 split across numbered shards 4→5 and layer 11 across 5→6. The 6,448,748,544-byte hypothetical retention result was a counterfactual on-disk calculation, not actual CPU/GPU/RM memory or a safe upper bound. Attempt 04 preserved launch flags (safetensors/mp/TP=1 and auto-prefetch-disabled log), but did not recover the effective vLLM loader configuration.

Repository H11 patch creates:
- w13_weight_packed: uint8 shape (num_experts, w13_num_shards * intermediate_size_per_partition, hidden_size // 2).
- w2_weight_packed: uint8 shape (num_experts, hidden_size, intermediate_size_per_partition // 2).
- Both are ModelWeightParameter with input_dim=1, output_dim=2 and weight_loader attribute.

H12 registers the same packed objects under the final w13_weight/w2_weight names, then removes the old packed names; it does not rewrap data as ordinary Parameter.

The public upstream vLLM v0.29 reference counts aten.copy_.default destination numel and caps per loader invocation to the destination param.numel(). Per-invocation capping is not proof that repeated calls over the parameter lifetime have no overlap. The online wrapper increments an aggregate element count and can process at load_numel >= load_numel_total. Finalization can process unfinished/padded layers. This is reference behavior only; the exact installed H38 files require source verification.

References:
- https://docs.vllm.ai/en/v0.29.0/api/vllm/model_executor/model_loader/reload/meta/
- https://docs.vllm.ai/en/v0.29.0/api/vllm/model_executor/model_loader/reload/layerwise/

## New code and expected result

- scripts/benchmark/inspect-h38-ct-layerwise-accounting.py: Python stdlib AST inspector; fingerprints four pinned installed H38 source files, fails closed on drift, enumerates two packed and six scale registrations and initialization expressions, checks H12 alias syntax, CopyCounter, per-call count cap, layerwise aggregate counting, buffering, materialization, replay, finalize and post-load source anchors. It does NOT evaluate torch, import vLLM, or read checkpoint/model data.
- scripts/benchmark/check-h38-ct-layerwise-accounting.sh: requires exact clean Git SHA, fixed image ID, H11/H12/H38 labels; read-only unprivileged runc, no network or GPU, no image pull, bounded memory/CPU/PIDs and private /tmp.
- tests/test_h38_ct_layerwise_accounting.py: synthetic happy/negative registration and alias fixtures; missing scale, missing count cap, source drift and runner safety/invalid SHA tests. Such tests alone do not prove actual installed H38 semantics.

The future result PASS_SOURCE_CONTRACT_ONLY is only evidence that the targeted syntax exists under the pinned installed-source digests. It is not a per-expert completeness proof.

## Unresolved contracts and stop conditions

1. Determine whether actual parameter weight_loaders cover each of 512 experts and all packed/scale elements uniquely, across partial and repeated calls.
2. Distinguish per-call capped copy counting from lifetime deduplication. Does a repeated copy or skipped subset let aggregate load_numel reach its target early?
3. Establish whether the finalizer can process a layer with unfilled required scale/weight components after the last shard.
4. Prove behavior at layer 8/11 shard splits: the later shard must arrive before release, materialization and H12 rename if required.
5. Confirm materialize_layer preserves ModelWeightParameter subclass/metadata/device/dtype/shape/weight_loader and H12 alias identity.
6. Derive a finite simultaneous-buffer upper bound from the actual effective loader/iterator, not from hypothetical checkpoint byte offsets.

No CT deferred-meta patch is authorized. No checkpoint payload scan, H38 image rebuild, GPU/model run, host-protection relaxation, managed service restart or PR #259 Ready/merge. Existing state: checkpoint ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST-STABILITY=INCONCLUSIVE; RM mitigation UNPROVEN.

## Operator classification after GitHub CI success

Execute the guarded wrapper once from an exact clean CI-qualified HEAD with H38_CT_ACCOUNTING_TARGET_SHA set to that same SHA; retain full stdout/stderr and exit code. PASS_SOURCE_CONTRACT_ONLY only enables further source-level review; INVALID is a source/guard contract or environment error and does not establish a runtime defect. Neither outcome qualifies the memory optimization or host stability.

No DGX execution or independent SHA256 copy of operator source logs is asserted in this staging document.


## Static hardening and synthetic counterexamples — continuation, 2026-10-09

The staged AST checker now separately validates the exact **eight** H11/H12-source creation contracts rather than just the registration names: both packed uint8 tensors, both per-group float8-e4m3fn scales and four float32 global/input scales; symbolic shape expressions, ModelWeightParameter input_dim/output_dim/weight_loader, and the absence of a literal device kwarg. These are *symbolic code expressions*, not measured concrete dimensions/device allocations. The checker also pins SKIP_LOAD_TENSORS, late parameter-size refresh, post-completion rejection, incomplete-layer finalization, and the *source syntax* used to preserve parameter class/attributes in meta materialization. It still does **not** establish class preservation during actual execution.

The public vLLM v0.29 code documents that its per-invocation cap prevents one loader's internal double-copy from immediately inflating the layer total. However, the aggregate counter is not an index-range coverage map. Source-only checker presence cannot prove lack of repeated *separate* invocations of the same destination. The built-in finalizer also processes positive but incomplete non-attention layers (e.g., padding), which cannot be promoted to CT weight/scale completeness without a separate contract.

New scripts/benchmark/simulate-h38-ct-layerwise-completion.py and tests/test_h38_ct_layerwise_completion_cases.py provide a **pure-standard-library TOY counterexample**, not a runtime observation. Eight parameter names intentionally match H38 CT, but their element counts are tiny synthetic integers:

- Synthetic complete case: both halves of w13 arrive with remaining packed/scale parameters: aggregate 20 and unique coverage 20.
- Synthetic duplicate whole-packed case: copying packed w13 size 8 **twice** and w2 size 4 once yields aggregate 20, unique coverage 12, and six missing scales. The threshold could be reached before the later synthetic scales.
- Synthetic duplicate half-packed case: copying the first half of w13 twice and all other parameters yields aggregate 20 but unique coverage 16; the other w13 half remains missing.
- Synthetic delayed finalizer case: only first half of w13 plus all other named parameters yields aggregate 16 of 20; the source partial-finalization branch can still be entered.
- Synthetic shard/layer labels 8 and 11 are mnemonic references to historical checkpoint revisits; **they do not reproduce the actual 4,608 keyed tensors, 512 experts, shapes, loader callbacks, shard ownership or memory footprint**.

The synthetic cases establish that aggregate element counting *without lifetime per-parameter unique-coverage accounting* does not logically imply CT weight-and-scale completeness. They do **not** show that the installed H38 loader ever makes the repeated calls in these witness scenarios.

This reinforces the next hard gate: inspect actual weight_loader call mapping, copy destinations and source shape/scale coverage, especially for split routed layers 8 and 11, before authorizing any CT meta storage or memory-peak claim. Historical CHECKPOINT_METADATA_ORDER_GATE=FAIL, FUNCTIONAL=NOT_REACHED, HOST_STABILITY=INCONCLUSIVE, RM_MITIGATION=UNPROVEN, and draft merge prohibition remain unchanged.

**Execution provenance boundary:** repository GitHub CI can qualify synthetic tests and AST implementation; exact pinned installed-H38 CPU-only checker execution remains a separate pending DGX operator record. Do not report synthetic cases as reproduced H38 startup failures or memory-use measurements.
