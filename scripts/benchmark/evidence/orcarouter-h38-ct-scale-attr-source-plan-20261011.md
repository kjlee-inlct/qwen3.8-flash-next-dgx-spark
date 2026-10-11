# H38 CT input-scale postconstruction weight-loader attribute provenance — source-only plan (2026-10-11)

**Status: REPOSITORY-SIDE INSPECTOR/STDLIB TESTS STAGED. Exact installed-H38 execution PENDING.** Do not confuse the completed earlier H38 CT packed/scale *registration* source audit with the new post-construction attribute inspection. Neither source check establishes runtime weight or scale coverage.

## Existing evidence and context

- The exact installed-image CT accounting source check **Attempt 03 PASS_SOURCE_CONTRACT_ONLY**, rc=0, on clean HEAD `5fa4265d394255744f8886b857804a28c433cf3f`, image `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`, is preserved in [Attempt 03](orcarouter-h38-ct-layerwise-accounting-attempt03-source-pass-20261011.md).
- The eight CT constructor contracts include two input-global-scale variables (`w13_input_scale`, `w2_input_scale`) registered as plain `torch.nn.Parameter`. Their constructors do not explicitly pass a `weight_loader` argument. This **does not prove** whether a weight_loader attribute was attached later.
- Other six CT constructors are vLLM Parameter subclasses with a constructor `weight_loader` keyword; actual runtime callback success still unverified.
- Public vLLM **v0.29.0 reference** source (a reference only, not proof of installed-image semantics) suggests that `create_weights` calls `set_weight_attrs(w13_input_scale, extra_weight_attrs)` and the counterpart for w2 after registration and a `quant_method=TENSOR` tag; `vllm/model_executor/utils.py::set_weight_attrs` sets attributes with an overwrite guard; `RoutedExperts.__init__` exports its loader in `moe_quant_params`; and `reload/layerwise.py` reassigns `tensor.weight_loader` to its online wrapper. These are the hypotheses for **pinned-image source inspection**.
- Reference source: `https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/model_executor/utils.py`, `.../compressed_tensors_moe_w4a4_nvfp4.py`, `.../routed_experts.py` and `.../reload/layerwise.py`. Do not silently treat upstream source text as the exact H38 image.

## New code and safety envelope

- `scripts/benchmark/inspect-h38-ct-scale-attr-provenance.py`: AST-only Python stdlib reader; requires previously validated exact SHA256 for CT, RoutedExperts and layerwise source files. Independently computes and reports the **previously unpinned** `vllm/model_executor/utils.py` SHA256 under the fixed H38 image-ID guard, while checking that the helper function contains an attribute assignment guarded against overwrites. This newly observed utility digest **must not be misreported as an independent pre-approved SHA256** until captured/qualified on DGX.
- For each input scale, fail closed if the `register_parameter` or `set_weight_attrs(var, extra_weight_attrs)` site is missing/duplicated, appears in the wrong order, or has no intervening `quant_method=TENSOR` update. Check the H11 `extra_weight_attrs.get("weight_loader")` source expression and reject an explicit `extra_weight_attrs.pop("weight_loader")` in this CT method.
- Check `RoutedExperts.__init__` exports the loader in source, and `layerwise._wrap_parameters_weight_loader` assigns the online wrapper plus `make_online_process_loader` references `_get_original_loader`.
- **Limitations:** AST sites and source text do not show actual dictionary values, function execution order across dynamic branches, whether runtime `setattr` succeeds, which particular loader executes, whether TorchDispatchMode emits `aten.copy_.default` for indexed scales, whether scale/weight destination coverage is unique, or a memory bound. Those remain `UNVERIFIED`.
- `scripts/benchmark/check-h38-ct-scale-attr-provenance.sh`: separate guard; requires exact clean checkout and fixed H38 image ID/labels, read-only user 65534 runc, `--pull never --network none --read-only --cap-drop ALL --security-opt no-new-privileges`, CPU/PID/memory caps, no GPU, no checkpoint/model data and no service/protection mutations.
- `tests/test_h38_ct_scale_attr_provenance.py`: stdlib-only happy and fail-closed fixtures for both input scales, nonmatching attribute dictionary, missing/early call sites, missing quant tag, missing H11 loader source, explicit loader pop, broken helper/routed/layerwise anchors, digest mismatch and wrapper safety checks. Unit tests do not prove actual H38 execution.

A future `H38_CT_SCALE_ATTR_PREFLIGHT=PASS_SOURCE_SITES_ONLY` is **only** evidence that the pinned image's static sites and guarded setter syntax are present. It must not be mapped to model loading success or the already completed CT Attempt 03 registration audit. If the installed H38 utility helper differs from upstream, record INVALID with source digest and classify without modifying the H38 image.

## Pending technical gates

1. Confirm exact-image input-scale setter sites and utility helper source with the separate guarded inspector and record its full output, SHA/exit code.
2. Decide whether a small *separately approved* strictly resource-bounded CPU-only synthetic TorchDispatchMode test is safe and useful. Even if executed successfully, that cannot establish lifetime uniqueness or actual checkpoint expert mapping.
3. Study loader callback mapping and shard 8/11 buffering without unqualified H38 GPU/model runs. Quantify true buffer peaks only with suitable bounded evidence, not a toy logical counterexample.

Unchanged: `CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY`, `CT_WEIGHT_COMPLETENESS=UNVERIFIED`, `COPYCOUNTER_SCALE_CREDIT=UNVERIFIED`, `SHARD_8_11_COMPLETENESS=UNVERIFIED`, `HOST_STABILITY=INCONCLUSIVE`, `RM_MITIGATION=UNPROVEN`, `GPU_MODEL_RERUN=BLOCKED`, `HOST_PROTECTION=UNCHANGED`, `PR_259=DRAFT_OPEN`, `MERGE=BLOCKED`.


## Actual pinned-image input-scale attribute source check — Attempt 01 PASS (2026-10-11)

**This supersedes the original STAGED/EXECUTION PENDING assertions above.** The DGX operator cleanly fast-forwarded to SHA 1865521c2ff58add7bddeed6735c76803a3e3637 and ran the guarded source-only wrapper on the fixed H38 image. Reported H38_CT_SCALE_ATTR_SOURCE=PASS_SOURCE_SITES_ONLY; H38_CT_SCALE_ATTR_PREFLIGHT=PASS_SOURCE_SITES_ONLY; source_check_rc=0; image_identity_unchanged=YES; GPU/model and checkpoint payload read NO.

Qualified static source sites:
- w13_input_global_scale: register_parameter line 183, quant_method=TENSOR source update line 184, set_weight_attrs(w13_input_scale, extra_weight_attrs) line 187.
- w2_input_global_scale: register_parameter line 192, quant_method=TENSOR source update line 193, set_weight_attrs(w2_input_scale, extra_weight_attrs) line 196.
- H11 source loader origin extra_weight_attrs.get('weight_loader'), RoutedExperts self.weight_loader export source, layerwise original loader retrieval/reassignment, and common helper guarded setattr AST anchors are present.
- CT SHA256 d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2, layerwise SHA256 9f37db893446d1f8ddc654a3bbcc3addf4b3020565920c56ef0c1ae29fd32a4a, routed SHA256 5206219da6b78315d6b35bee89fd0caa783681846affbf6917f430ef7f2481b5 are previously pinned and matched.
- The helper source (vllm/model_executor/utils.py) SHA256 f208310647a012797e0b0e9631d3498135c7f9aef831e35e42e96eceb7623f89 is a NEW image-ID-guarded observation, not a pre-approved pin for this first run. Do not conflate helper syntax checks with observed attribute execution.

Canonical [actual H38 CT scale-attr Attempt 01 PASS evidence](orcarouter-h38-ct-scale-attr-attempt01-source-pass-20261011.md). Prior CT source Attempt 03 PASS remains independent. No result certifies the effective runtime loader, TorchDispatchMode count, unique 512-expert loaded coverage, layer 8/11 buffering, or host stability; these remain UNVERIFIED. Next use is a separate isolated CPU-only dispatcher witness with strictly explicit provenance and resource safety, not repetitive CT AST inspection or model/GPU execution. PR #259 Draft/Open, merge blocked.


## Separate external PyTorch CPU indexed-write observation — 2026-10-11

An **assistant-side external Python 3.13 / torch 2.10.0+cpu** microprobe, NOT an H38-image execution, observed aten.copy_.default events under TorchDispatchMode for indexed scalar and row writes. In a tiny 3x2 toy, repeating one destination yielded aggregate per-call credit 6 while only 5 unique elements had been written. Source-labeled documentation and reproduction code: [External CPU indexed-write toy](h38-ct-copycounter-indexed-write-external-cpu-toy-20261011.md).

This observation narrows the general *semantic possibility*: some PyTorch indexed assignments count as copy_ dispatches, so it is not correct to assume they are intrinsically invisible to CopyCounter. It does **not** close the installed H38 PyTorch-version/source-specific event question nor prove repeated writes actually happen under the H38 loader. The unverified layerwise numel/unique-coverage hazard remains conditional, not an established model defect.

**Next prioritized inquiry:** determine how the exact loader maps all expected checkpoint expert/shard scale events to destination parameter slots and whether buffering and early completion can be bounded without real H38 inference. Source-only and tiny external CPU evidence should remain separate; no new H38 GPU/model, H38 container/host protection or PR Ready/Merge.
