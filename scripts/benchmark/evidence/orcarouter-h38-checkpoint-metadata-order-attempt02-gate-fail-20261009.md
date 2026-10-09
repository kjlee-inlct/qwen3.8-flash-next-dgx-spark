# H38 production checkpoint metadata/order attempt 02 — VALID ANALYSIS, ORDER GATE FAIL — 2026-10-09

Status: **VALID METADATA ANALYSIS / ORDER_GATE=FAIL / CT DEFERRED-W13 STILL BLOCKED**. The outer runner incorrectly printed `PREFLIGHT=INVALID` when the analyzer exited 3 for a legitimate order-gate failure. Preserve both raw outputs and classify the **content** according to the inner completed result.

## Exact operator provenance and outcome

The DGX Spark operator ran the unmodified 64 MiB private-tmpfs metadata reader on:

- Source checkout: `eadaaeefbc23abf428e880890537ca26ea162f9d`; clean worktree check passed.
- Installed image: `vllm-orcarouter-v029-h38-decoder-scope:v1`.
- Pinned image ID: `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`.
- Model directory: `$HOME/models/qwen3.8-flash-next-orcarouter`; index was present.
- Execution flags: `--runtime runc --network none --read-only --user 65534:65534`, read-only model/source bind, `--tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777`.
- Operator-side raw log: `/tmp/h38-checkpoint-metadata-order-attempt02.txt` (provided as terminal text, not separately ingested as original file).
- Full content analysis printed `H38_CKPT_METADATA_ORDER=BEGIN`, JSON output, `H38_CKPT_METADATA_ORDER=END` and **`H38_CKPT_METADATA_ORDER_GATE=FAIL`**.
- Outer runner incorrectly collapsed the non-zero analyzer gate exit code (3) into **`H38_CKPT_METADATA_PREFLIGHT=INVALID reason=checkpoint_metadata_order_invalid`** because it used `docker run ... || fail ...` for all non-zero exits. This outer label is **a classification bug**, not evidence that the completed JSON analysis was invalid.
- Unlike Attempt 01, no Python tempfile error occurred. This establishes that the restricted `/tmp` tmpfs removed the original execution blocker.

## Actual measured metadata

| Metric | Operator output |
|---|---:|
| `index_verified` | true |
| `shard_count` | 18 |
| Numbered model file set | `model-00001-of-00017.safetensors` through `model-00017-of-00017.safetensors`: **17 files** |
| Auxiliary indexed file | `model-mtp.safetensors`: **1 file** |
| `tensor_count` | 223,046 |
| `routed_expert_tensor_count` | 221,186 |
| `routed_expert_layer_count` | 48 |
| `missing_layers` / `unexpected_layers` | [] / [] |
| `routed_expert_revisited_layers` | **[0, 8, 11]** |
| `routed_expert_max_overlapping_intervals` | **3** |
| `routed_weight_total_bytes` | **72,981,184,512** |
| `scenario_peak_routed_bytes_release_at_last_routed_key` | **6,448,748,544** |
| `scenario_peak_routed_bytes_release_at_last_any_layer_key` | **6,448,748,544** |
| `status` / `H38_CKPT_METADATA_ORDER_GATE` | **FAIL / FAIL** |

The additional `model-mtp.safetensors` had **31 tensors, only 2 routed keys**. The reported 18 files are **not** 18 consecutively numbered base-model shards; they are 17 numbered base-model shards **plus** one MTP file referenced by the index. The direct operator output does **not** identify the layer IDs of those two MTP routed keys, nor the exact shard boundaries responsible for the 0/8/11 revisits. Attribution of any particular revisit to MTP would be premature.

The estimated 6,448,748,544-byte hypothetical peak is **an on-disk routed-tensor byte-retention scenario under the inspecter's assumed ordering/release rules**. It is not measured CPU allocated memory, GPU usage, pinned memory, or proof that a CT meta loader would hold exactly this many bytes. The two hypothetical release scenarios yielding the same value does not validate either scenario against the installed runtime.

## Decisive acceptance interpretation

The examined metadata order **does not satisfy** the strict `48 complete routed layers / no layer revisits / maximum one concurrent interval` feasibility criterion of the previous M1-style w13-deferral proposal: there are three reported layer revisits and up to three overlapping routed intervals.

This is **not** evidence of corrupted safetensors files, checkpoint weights, or runtime layerwise materialization failure. It means the *particular proposed contiguous-layer checkpoint streaming assumption fails* over the **18 indexed files, including MTP**, using the inspector's `natural_sorted_file_order + safe_open().keys()` model. The installed H38 loader's exact production iterator semantics still have **not** been independently verified. The metadata gate cannot be relabeled PASS by excluding MTP or by changing a threshold without separate evidence.

## Narrow next discriminator — static only

1. **Preserve this FAIL** unchanged. Do not implement `device="meta"` or `uses_meta_device=True` in H38 CT yet. Do not run a live H38 candidate, tune host memory, or relax protection.
2. Fix the outer runner to propagate completed `ORDER_GATE=FAIL` distinctly from `INVALID` (exit code 3 versus 2 or infrastructure error).
3. Add bounded header-only `per_shard_routed_layer_ids`, `revisited_layer_run_locations` (first/last tensor names + numbered shard vs auxiliary file), and **diagnostic-only** numbered-base-model revisit indicators. This will distinguish base-model shard fragmentation from possible MTP-related reappearance without silently dropping `model-mtp.safetensors` from the full-stream gate.
4. Static check remains read-only and may be replayed once on the same exact checkpoint/image **only for these new diagnostics**, with the same strict gates. Source-only Python/CI tests are not a substitute for that real observed breakdown.
5. Independent pinned-H38-loader ordering and exact CT weight-loader completion/scale materialization contracts remain required before proposing a safe buffered strategy.

Explicit negative gates remain:

```text
actual_metadata_order_gate=FAIL
h38_loader_order_equivalence=UNVERIFIED
all_layerwise_weight_buffers_bounded=NO
ct_meta_patch_implemented=NO
meta_w13_materialization_proven=NO
rm_alloc_reduction_proven=NO
host_stability_qualified=NO
production_promotion=BLOCKED
```

**No GPU/model run, R33 instrumentation, monitoring change, managed restart/promotion, PR Ready or merge is authorized. PR #259 stays Draft/Open.**
