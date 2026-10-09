# H38 exact-installed loader source contract — actual DGX PASS — 2026-10-09

Status: **VALID CPU-ONLY INSTALLED-SOURCE PASS**. This is NOT an active loader-config proof, MTP I/O trace, CT meta materialization qualification, memory-mitigation proof, or host-stability PASS.

## Observed provenance

The operator ran `scripts/benchmark/check-h38-installed-loader-source.sh` from a clean, fast-forwarded `feat/h38-managed-integration` checkout at exact SHA `b85f506a4f3f6e7a1272f6e5b37a137a5f57a5f9`.

- Image: `vllm-orcarouter-v029-h38-decoder-scope:v1`
- Exact image ID: `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`
- Original operator-side log: `/tmp/h38-installed-loader-source-contract.txt` (provided as pasted terminal transcript, not independently ingested or hashed)
- Scope emitted: `execution=cpu_only_no_checkpoint_mount_no_gpu_no_network`, `private_tmpfs=/tmp:32m:rw:noexec:nosuid:nodev`
- Source verdict: `H38_LOADER_STATIC_CONTRACT=PASS`
- Guard verdict: `H38_LOADER_SOURCE_PREFLIGHT=PASS`
- End assertions: `image_identity_unchanged=YES`, `model_checkpoint_payload_read=NO`, `gpu_or_model_load=NO`, `managed_service_mutation=NO`, `host_protection_changed=NO`

The observations are the checker's bounded source/guard assertions. They do not constitute an independently captured managed-service start-time diff or an RM/GPU runtime trace. No separate `source_check_rc` line was emitted; do not invent one.

## Exact installed-source SHA256 fingerprints

| Installed source group | SHA256 |
|---|---|
| Default model loader | `9c9d54b1b650bf5affc924ebb8b8c73711e187ae7486cadd9f737bb1279cc7b8` |
| Model loader weight utilities | `494b07cd6b4e4fb40314dec1d0e0c3b433fe62a135a3a9d6d9e4058059054e4a` |
| WeightsMapper / AutoWeightsLoader utilities | `745e79363f54b16666ea40e8ac84bf9ddcba630bd04710e305a1dc1d74333954` |
| Qwen4Exp model code | `46d9a2c89232786f8f5d13248728bdfdacba424a6fedaca2b27d2fe9b0cf96ba` |
| Layerwise online loader | `9f37db893446d1f8ddc654a3bbcc3addf4b3020565920c56ef0c1ae29fd32a4a` |
| Meta layer materialization | `87a98fe340f7e39a7ba3ed136506bf5e3eef463f9215420cce5ddeb5d25a2b9c` |
| Base model loader | `a7e925f232ad3eebbee7ab37d3aba724c24465c3078da29489da0438664c6b08` |
| Compressed-tensors W4A4 NVFP4 MoE | `d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2` |

The hashes for layerwise, meta, base loader and CT agree with earlier installed-H38 static source audit fingerprints. The other four hashes extend that provenance; they are not automatically equivalent to an upstream v0.29.0 file hash.

## Actual installed-source assertions observed

```text
default_index_file_filter=SOURCE_PRESENT
default_primary_and_secondary_source_enumeration=SOURCE_PRESENT
safetensors_natural_file_sort_and_key_iteration=SOURCE_PRESENT
safetensors_get_tensor_before_model_mapping=SOURCE_PRESENT
alternative_eager_prefetch_multithread_paths=SOURCE_PRESENT
qwen4_causal_and_conditional_mtp_name_drop=SOURCE_PRESENT
weights_mapper_none_skips_name=SOURCE_PRESENT
layerwise_numel_completion_and_buffer_replay=SOURCE_PRESENT
ct_h11_h12_packed_and_postload_aliases=SOURCE_PRESENT
H38_LOADER_STATIC_CONTRACT=PASS
H38_LOADER_SOURCE_PREFLIGHT=PASS
```

**Precise interpretation:** The pinned installed code includes an index-aware default loader, a naturally sorted safetensors source path, name iteration and tensor retrieval before a later model mapper, a Qwen4Exp `mtp.` name-dropping mapper, and the layerwise element-count buffering/materialization/replay functions alongside H11/H12 CT packed parameter aliases. This **does not prove** that H38 selected the default single-thread lazy path at runtime or that MTP tensor data was skipped before `get_tensor`. Name filtering at the mapping stage is not itself a disk-I/O or host-memory reduction.

The installed code also exposes alternative eager, prefetch and multithread paths; the source contract checks their presence, **not** which one was active. Nor does mere presence of the layerwise count/replay functions prove H38 CT packed `ModelWeightParameter`, scales, per-expert completion, dtype/device or H12 alias correctness when deferred from meta storage.

The execution itself explicitly reported:

```text
source_scope=pinned_h38_image_only_not_selected_runtime_path
exact_h38_active_loader_config_verified=NO
runtime_file_and_mtp_iteration_proven=NO
mtp_file_payload_skipped_before_get_tensor_proven=NO
ct_meta_w13_patch_implemented=NO
ct_meta_materialization_proven=NO
shard_split_layer_8_11_buffer_peak_bounded=NO
rm_mitigation_proven=NO
host_stability_qualified=NO
```

## Relationship to actual indexed-checkpoint Attempt 03

The prior read-only checkpoint metadata Attempt 03 remains **VALID / ORDER_GATE FAIL / exit 3**. Its 18 indexed files were 17 numbered base-model shards plus `model-mtp.safetensors`. The numeric layer-0 revisit was a base-vs-MTP namespace collision; **base-model** layers 8 and 11 independently had two routed-key runs across numbered files 4→5 and 5→6. The hypothetical 6,448,748,544 bytes was based on stored routed tensor offsets, **not** measured resident CPU/GPU memory or a safe upper bound.

The installed-source PASS is consistent with the **availability** of the header inspecter's natural-order model in the vLLM source, but not an attestation of selected active runtime iteration, mapping/skip behavior, layerwise completion, or memory lifetime. Therefore **do not promote the strict checkpoint ORDER_GATE to PASS**.

Canonical related documents:
- `orcarouter-h38-checkpoint-metadata-order-attempt03-revisit-ownership-20261009.md`
- `orcarouter-h38-installed-loader-source-contract-plan-20261009.md`
- `orcarouter-h38-ct-meta-w13-source-prerequisites-result-20261009.md`

## Next discriminators — static/offline, no model/GPU launch

1. Independently attest the **actual managed/candidate H38 loader configuration** without starting or changing it: selected `load_format`, `safetensors_load_strategy`, multithread flag, prefetch block/thread settings, EP filter, and architecture/MTP routing. A repository script/config default alone is **not** an observed runtime setting; prefer immutable startup arguments or previously captured exact container configuration/log evidence.
2. Inspect the **exact installed weight-loader logic** to distinguish base-model `mtp.` mapped-skip after iterator vs MTP-specific model initialization/loading. Avoid assuming the MTP safetensors file was never read or contributed no memory.
3. Establish a falsifiable CT-specific **element-count completion contract** for packed `w13`, `w2`, expert scales and post-load aliases when routed layers 8 and 11 span files. Explain buffer lifetime under each selected loader path; no assumption that 6,448,748,544 bytes is a safe peak.
4. If any of these are unknown, keep H38 deferred-meta implementation **BLOCKED**; preserve strict RM protection, `FUNCTIONAL=NOT_REACHED`, `HOST-STABILITY=INCONCLUSIVE` and PR #259 Draft/Open.

No live H38 rerun, source image patch, checkpoint rewrite, container/service state mutation, privileged inspect, memory-policy relaxation, R33, PR Ready or merge is authorized by this result.
