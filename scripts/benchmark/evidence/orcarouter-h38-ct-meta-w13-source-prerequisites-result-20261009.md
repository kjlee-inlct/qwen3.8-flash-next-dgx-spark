# H38 CT meta-w13 feasibility — exact installed-source prerequisite result — 2026-10-09

Status: **VALID SOURCE-ONLY PREREQUISITES PASS** — **NO CT META PATCH, NO MODEL/GPU LOAD, NO MITIGATION OR HOST-STABILITY QUALIFICATION**.

## Operator-provided DGX result

The DGX Spark operator executed the source-only checker from a clean fast-forward checkout:

- Branch: `feat/h38-managed-integration`
- Execution checkout: `ac58309620ace2213df68ebf06b2c18b9592f394`
- Existing image: `vllm-orcarouter-v029-h38-decoder-scope:v1`
- Exact image ID (unchanged): `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`
- Original operator-side log: `/tmp/h38-ct-meta-source-prerequisites.txt` (not uploaded into the repository).
- Outer result: `H38_CT_META_SOURCE_PREFLIGHT=PASS`
- Source result: `H38_CT_META_STATIC_PREREQUISITES=PASS`
- Shell output has no explicit `source_check_rc` field, but the command completed with no visible errors and the final PASS fields. Do not invent an additional recorded exit-code line.

The checker ran in an ephemeral unprivileged runc container with no network, no GPU/model load, read-only filesystem, resource limits, and only the source inspector bind-mounted read-only. The operator output confirms:

```text
H38_CT_META_STATIC_PREREQUISITES=PASS
image_identity_unchanged=YES
managed_service_mutation=NO
gpu_or_model_load=NO
monitor_protection_changed=NO
ct_meta_w13_patch_implemented=NO
H38_CT_META_SOURCE_PREFLIGHT=PASS
```

These are scripted guard/source assertions, not an independent managed-service `StartedAt` comparison or NVIDIA RM allocation trace.

## Exact six installed source identities

| Installed source group | SHA256 |
|---|---|
| Compressed-tensors W4A4 NVFP4 MoE (H11/H12) | `d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2` |
| Base loader | `a7e925f232ad3eebbee7ab37d3aba724c24465c3078da29489da0438664c6b08` |
| Layerwise online processing | `9f37db893446d1f8ddc654a3bbcc3addf4b3020565920c56ef0c1ae29fd32a4a` |
| Meta materialization | `87a98fe340f7e39a7ba3ed136506bf5e3eef463f9215420cce5ddeb5d25a2b9c` |
| Reload size utilities | `9421654170a04244d9ad702ba8c81dcf6c09a3c8bfe7e04ccbe099baf57b63a1` |
| RoutedExperts | `5206219da6b78315d6b35bee89fd0caa783681846affbf6917f430ef7f2481b5` |

## Source assertions actually observed

```text
ct_packed_w13_h11_torch_empty=YES
ct_packed_w2_h11_torch_empty=YES
ct_h12_postload_alias=PASS
ct_declares_own_uses_meta_device=NO
loader_online_quant_finalize=SOURCE_PRESENT
layerwise_weight_loader_wrapper=SOURCE_PRESENT
layerwise_materialize_and_process=SOURCE_PRESENT
routed_quant_method_order=SOURCE_PRESENT
m1_modelopt_direct_patch_reusable=NO
h38_ct_meta_w13_patch_implemented=NO
checkpoint_loader_name_order_verified=NO
meta_w13_materialization_proven=NO
logical_rm_reduction_proven=NO
physical_memory_reduction_proven=NO
host_stability_qualified=NO
```

**Interpretation:** The H38 source has the native vLLM `uses_meta_device` / weight-loader wrapper / materialize-process and finalization *building blocks*. The H38 CT class does **not** itself declare `uses_meta_device` in the tested direct class scope; no H38 CT-specific `device="meta"` change was made. The original H11 packed `torch.empty` constructors and H12 post-load alias remain unchanged.

**What this does not establish:** whether modifying CT `uses_meta_device` would be class-wide safe, whether `ModelWeightParameter` and H12 renaming survive live materialization, whether weight-loader replay preserves exact values/dtypes, whether the H38 production 18-shard checkpoint streams tensors in suitable layer order, whether buffered weight peak is bounded, or whether the approximately 75 GiB early physical-page burst shrinks. Those remain separate gates.

## Next bounded, information-gaining work

Perform **read-only, metadata-only** analysis of the *actual H38 OrcaRouter production* safetensors shards in the **same default loader order**. Validate shard/index completeness and tensor names/shapes/byte offsets; compute per-layer contiguous/revisit and conservative multi-layer buffered-data risk. Do not access tensor payloads, scan weights, change runtime/host config, launch a model or loosen protection.

The historical `exp/m1-deferred-meta-w13` ModelOpt/R28 source patch is **not directly transferable** to the H11/H12 CT route and is not a qualified mitigation. The local source PASS only permits design-level evaluation of a new CT-specific strategy. R33 live tracing, CT code mutation, live H38 rerun, managed promotion and PR #259 merge remain blocked.

## Prior implementation validation

- Checker implementation commit: `96f2aafff2297760595962b64a0ae981c66bc400`.
- Static CI `37778807130`: SUCCESS, 613/613 tests; ShellCheck, syntax, compile, whitespace PASS.
- Canonical static-sync commit: `ac58309620ace2213df68ebf06b2c18b9592f394`.
- Static-sync CI `37779107553`: SUCCESS, 613/613 tests; source-only operator verification recorded separately here.
