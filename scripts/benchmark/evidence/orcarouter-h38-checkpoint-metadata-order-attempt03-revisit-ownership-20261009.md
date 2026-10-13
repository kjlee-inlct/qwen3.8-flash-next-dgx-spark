# H38 production checkpoint metadata/order attempt 03 — validated revisit ownership — 2026-10-09

Status: **VALID HEADER-ONLY CHECK / STRICT FULL-STREAM ORDER_GATE FAIL / EXIT 3**.
This document does **not** establish an unsafe runtime loader or checkpoint corruption. It closes the specific question of *which indexed file and tensor namespace caused each observed routed layer revisit in the inspecter's assumed ordering*.

## Provenance and exact exit classification

The DGX Spark operator supplied the full terminal output of the single permitted bounded read-only replay:

- Branch: `feat/h38-managed-integration`; clean checkout guard passed
- Exact execution commit: `f875aa2ea141e004fe2c0b37174bd275d9df39a1`
- Image: `vllm-orcarouter-v029-h38-decoder-scope:v1`
- Pinned image ID: `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`
- Checkpoint directory: `$HOME/models/qwen3.8-flash-next-orcarouter`
- Original operator-side log: `/tmp/h38-checkpoint-metadata-order-attempt03.txt` (provided as pasted terminal transcript, **not separately fetched or byte-hashed**)
- Isolation: ephemeral runc, no network or GPU/model loading, read-only image and checkpoint, UID 65534, bounded 64 MiB private `/tmp` tmpfs
- Output: `H38_CKPT_METADATA_ORDER=BEGIN` / `END`, `H38_CKPT_METADATA_ORDER_GATE=FAIL`, `image_identity_unchanged=YES`, **`H38_CKPT_METADATA_PREFLIGHT=ORDER_GATE_FAIL`**, and **`metadata_check_rc=3`**.

The earlier Attempt 01 unusable-tempdir INVALID and Attempt 02 completed FAIL misclassified as outer INVALID are distinct historical runs; Attempt 03 confirms that the corrected runner preserves a *valid completed order-gate failure* without downgrading it to an execution INVALID.

## Complete indexed file shape, no payload reads

| Field | Observed value |
|---|---:|
| `index_verified` | true |
| `shard_count` | 18 |
| `numbered_model_shard_count` | **17** (`model-00001-of-00017` through `model-00017-of-00017.safetensors`) |
| `auxiliary_shard_names` | **[`model-mtp.safetensors`]** |
| `tensor_count` | 223,046 |
| `routed_expert_tensor_count` | 221,186 |
| `routed_expert_layer_count` | 48 |
| `missing_layers` / `unexpected_layers` | [] / [] |
| `routed_expert_revisited_layers` | **[0, 8, 11]** |
| `base_model_only_revisited_layers_diagnostic` | **[8, 11]** |
| `base_model_only_routed_layer_count_diagnostic` | 48 |
| `routed_expert_max_overlapping_intervals` | **3** |
| `routed_weight_total_bytes` | **72,981,184,512** |
| Hypothetical peak, release on last routed key | **6,448,748,544 bytes** |
| Hypothetical peak, release on last any-layer key | **6,448,748,544 bytes** |
| `status` | **FAIL** |

`model-mtp.safetensors` contains 31 indexed tensors, including exactly 2 whose names match the inspecter's routed-expert classifier, both from its own `mtp.layers.0.mlp.experts` namespace. There are 17 numbered base-model shards, **not 18 numbered base-model shards**. The full index of 18 files remains the actual analyzed object.

## Bounded, observed revisit spans — exact keys and file origins

### Layer 0 — base-model versus MTP namespace collision in classifier

First run (numbered base-model file):

```text
first_global_tensor_ordinal = 17
first_shard = model-00001-of-00017.safetensors
first_key = model.language_model.layers.0.mlp.experts.0.down_proj.weight_global_scale
last_global_tensor_ordinal = 4624
last_shard = model-00001-of-00017.safetensors
last_key = model.language_model.layers.0.mlp.experts.99.up_proj.weight_scale
routed_key_count = 4608
```

Second run (auxiliary MTP file):

```text
first_global_tensor_ordinal = 223024
first_shard = model-mtp.safetensors
first_key = mtp.layers.0.mlp.experts.down_proj
last_global_tensor_ordinal = 223025
last_shard = model-mtp.safetensors
last_key = mtp.layers.0.mlp.experts.gate_up_proj
routed_key_count = 2
```

This is **not evidence the base-model layer 0 expert weights were repeated in MTP**. The checker intentionally uses a broad numeric layer classifier, so distinct named module namespaces resolve to numeric ID 0 in the *full-file* order scan. The MTP file's separate module naming is observed syntactically; exact H38 loader handling still requires code-level verification.

### Layer 8 — actual numbered base-model shard boundary revisit

First run:

```text
first_global_tensor_ordinal = 37573
first_shard = model-00004-of-00017.safetensors
first_key = model.language_model.layers.8.mlp.experts.0.down_proj.weight_global_scale
last_global_tensor_ordinal = 39691
last_shard = model-00004-of-00017.safetensors
last_key = model.language_model.layers.8.mlp.experts.99.up_proj.weight_scale
routed_key_count = 2119
```

Second run:

```text
first_global_tensor_ordinal = 48032
first_shard = model-00005-of-00017.safetensors
first_key = model.language_model.layers.8.mlp.experts.235.down_proj.weight_global_scale
last_global_tensor_ordinal = 50520
last_shard = model-00005-of-00017.safetensors
last_key = model.language_model.layers.8.mlp.experts.511.up_proj.weight_scale
routed_key_count = 2489
```

The two observed runs total **4,608 routed keys**. Other layers appear between these runs in the full sorted per-file tensor sequence. The source trace does not establish the installed runtime's tensor retention or materialization point.

### Layer 11 — actual numbered base-model shard boundary revisit

First run:

```text
first_global_tensor_ordinal = 44329
first_shard = model-00005-of-00017.safetensors
first_key = model.language_model.layers.11.mlp.experts.0.down_proj.weight_global_scale
last_global_tensor_ordinal = 48013
last_shard = model-00005-of-00017.safetensors
last_key = model.language_model.layers.11.mlp.experts.99.up_proj.weight_scale
routed_key_count = 3685
```

Second run:

```text
first_global_tensor_ordinal = 55172
first_shard = model-00006-of-00017.safetensors
first_key = model.language_model.layers.11.mlp.experts.409.down_proj.weight_global_scale
last_global_tensor_ordinal = 56094
last_shard = model-00006-of-00017.safetensors
last_key = model.language_model.layers.11.mlp.experts.511.up_proj.weight_scale
routed_key_count = 923
```

The two observed runs also total **4,608 routed keys**. This second base-model revisit is independent of the auxiliary MTP layer-0 name collision.

### Why full-stream gate remains FAIL

The bounded diagnostic reports `base_model_only_revisited_layers_diagnostic=[8,11]`, so ignoring the auxiliary MTP file **does not make the prior one-contiguous-expert-layer criterion true**. Its purpose is attribution, not exception-based acceptance. No assumption that layer 8/11 can materialize after their first run is supported.

The index/header/name source model is `metadata_only_safetensors_key_order_assuming_default_single_thread_loader`; the output explicitly says:

```text
diagnostic_base_only_scope_can_override_full_gate=false
exact_h38_loader_order_contract_verified=false
all_layerwise_weight_buffers_bounded=false
meta_materialization_proven=false
ct_meta_patch_implemented=false
host_stability_qualified=false
```

**Do not rewrite FAIL as PASS, remove MTP, or claim a runtime buffering budget from the hypothetical 6,448,748,544-byte figure.** This quantity is indexed on-disk routed-tensor size under counterfactual release rules, not a CUDA, pinned-RAM, CPU RSS or NVIDIA RM measurement.

## Engineering decision and next useful gate

1. **Close the checkpoint metadata revisit attribution question** for the observed 18-file, `safe_open.keys()` default-order model: layer 0 is an MTP/base namespace collision; layer 8 spans numbered shards 4→5, layer 11 spans numbered shards 5→6. The strict prior contiguous streaming prerequisite is still **FAIL**.
2. **Do not attempt H38 CT deferred-w13** based on this result. The legacy M1 ModelOpt meta strategy cannot be transferred without independently proving CT's complete packed `ModelWeightParameter` lifecycle, H12 alias, dtype/device/scales and a loader-driven release/buffer strategy.
3. Next step should be **read-only, exact-installed H38 vLLM loader source contract** verification: how indexed `model-mtp.safetensors` and numbered shards are enumerated; whether weights are emitted in natural per-file `safe_open.keys()` order versus any other iterator; whether the H38 MTP loader is separate from the base model; how layerwise materialization is triggered on complete parameter names. This is static source work, **not** another broad probe or unchanged checkpoint rerun.
4. Any future buffer budget needs an explicit finite completion rule for shard-split expert weights (including layer 8 and 11) and for scales, with an actual model-loader stream equivalence proof; else the CT meta mitigation remains blocked.
5. Retain exact existing safety policy: no DGX model restart, no GPU allocator experiment/R33, no checkpoint payload reads, no protection relaxation, no managed promotion, no PR Ready/merge.

## Provenance boundary

This record is grounded only in the user-supplied Attempt 03 terminal transcript. The local `/tmp/h38-checkpoint-metadata-order-attempt03.txt` file has not been separately uploaded, copied or hashed. The inspector *reports* `tensor_payload_read=NO` by its source-only design and executes no model; the terminal log did not separately include a `tensor_payload_read=NO` end marker in this FAIL path. No runtime host memory metrics were collected.
