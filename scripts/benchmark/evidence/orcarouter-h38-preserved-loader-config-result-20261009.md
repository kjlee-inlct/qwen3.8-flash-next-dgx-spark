# H38 SPEC=none Attempt 04 — preserved loader launch configuration result — 2026-10-09

Status: **VALID EXISTING ARCHIVE / PASS_ARCHIVED_LAUNCH_FLAGS_ONLY**.
No new model/accelerator workload, container inspection, service mutation, or host protection change occurred in this verification. This result **does not** establish a resolved vLLM `LoadConfig`, any safe CT meta allocation, or host stability.

## Real operator execution and provenance

The user executed the read-only `scripts/benchmark/check-h38-preserved-loader-config.sh` on the DGX Spark:

- branch: `feat/h38-managed-integration`;
- exact clean checkout: `1bc76cb12cc8df9d9512de0d0cd29e49120c1233`;
- original historical archive:
  `/tmp/orcarouter-h38-mtp-none-attempt04-20261007T232026Z`;
- output file: `/tmp/h38-preserved-loader-config-attestation.txt` (operator provided pasted terminal output; the original file was **not separately imported or SHA256-hashed**);
- `scope=existing_archive_only_no_docker_no_model_no_gpu_no_service`;
- `H38_PRESERVED_LOADER_CONFIG_GATE=PASS_ARCHIVED_LAUNCH_FLAGS_ONLY`;
- `H38_PRESERVED_LOADER_PREFLIGHT=PASS_ARCHIVED_LAUNCH_FLAGS_ONLY`.

The original archive existed and was parsed: `candidate-inspect.json` and `candidate-cmd.json` agreed, and the captured Docker config matched the pinned H38 candidate image, H38 runtime-lineage environment and expected model mount. The checker does not print secrets, model-mount host paths, or the whole Docker inspect object.

### Image/command and source identity checks

```text
archive_kind=preserved_h38_mtp_none_candidate_inspect
captured_image_tag_verified=true
captured_image_id_verified=true
captured_cmd_pair_consistent=true
captured_model_mount_present=true
captured_h38_env_lineage_verified=true
```

Image identity was checked against the immutable tag
`vllm-orcarouter-v029-h38-decoder-scope:v1` and ID
`sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`
by the exact-source parser. These are **historically captured identity fields**, not a fresh live-container status check.

## Captured explicit loader CLI options

| CLI field | State observed | Literal value |
|---|---|---|
| `--load-format` | **EXPLICIT** | `safetensors` |
| `--distributed-executor-backend` | **EXPLICIT** | `mp` |
| `--tensor-parallel-size` | **EXPLICIT** | `1` |
| `--safetensors-load-strategy` | NOT_EXPLICIT | unknown |
| `--safetensors-prefetch-block-size` | NOT_EXPLICIT | unknown |
| `--safetensors-prefetch-num-threads` | NOT_EXPLICIT | unknown |
| `--model-loader-extra-config` | NOT_EXPLICIT | unknown |
| `--enable-expert-parallel` | NOT_EXPLICIT | unknown |
| `--no-enable-expert-parallel` | NOT_EXPLICIT | unknown |
| `--pipeline-parallel-size` | NOT_EXPLICIT | unknown |
| `--speculative-config` | NOT_EXPLICIT | unknown |

The archived `speculative_config` appears a second time in the parser output as `{"state":"NOT_EXPLICIT","value":null}`, consistent with the SPEC=none discriminator provenance. **Not explicitly supplied** is not evidence that the effective default is false, zero, absent, or a particular built-in runtime configuration. A `tensor_parallel_size=1` startup flag does not itself prove expert-parallel behavior.

The observed `recorded_safetensors_prefetch_log` was:

```text
AUTO_PREFETCH_DISABLED_LOG_OBSERVED
```

Thus the historical Attempt 04 startup-phase/log file **did contain** the literal marker `Auto-prefetch is disabled`. This is stronger than inferring it from the earlier atomic H38 startup record. It is a **log observation**; no further claim about explicit prefetch strategy, all I/O optimizations, thread counts, or the effective settings object follows.

## Actual negative predicates — preserve literally

```text
actual_effective_vllm_load_config_proven=false
actual_tensor_iteration_proven=false
base_vs_mtp_tensor_io_proven=false
ct_meta_layer_completion_proven=false
safe_peak_weight_buffers_proven=false
host_stability_qualified=false
metadata_order_gate_overridden=false
```

This archive pass is a **preserved launch-argument identity gate**, not a proof that the installed default `safetensors_weights_iterator` ran in any given branch or that a Qwen4Exp `mtp.` name mapper prevented an earlier `get_tensor(name)` read.

## Integration with existing H38 evidence

- The *installed source* audit `orcarouter-h38-installed-loader-source-contract-result-20261009.md` confirmed that the pinned H38 image exposes safetensors natural file order/key iteration, alternative eager/prefetch/multithread paths, Qwen4Exp MTP name-drop mapping and native layerwise numel-completion/buffer replay. **SOURCE_PRESENT** is not selected runtime execution.
- The checkpoint Attempt 03 `orcarouter-h38-checkpoint-metadata-order-attempt03-revisit-ownership-20261009.md` remains **VALID / ORDER_GATE=FAIL / exit 3**: base-model routed layer 8 crosses numbered shards 4→5; layer 11 crosses 5→6; an MTP-namespace layer 0 collides only in the broad numeric classifier. Base-only revisit diagnostic **[8,11]**. The two **6,448,748,544-byte** hypothetical routed-retention peaks are on-disk offset accounting, not observed RAM or NVIDIA RM allocations.
- The earlier H38 Attempt 04 itself remains **valid protected stop** with `FUNCTIONAL=NOT_REACHED`, `HOST-STABILITY=INCONCLUSIVE`, strict RM OOM none observed *in that valid measured window*, and protection intervened. Removing speculative MTP did not avoid the protection boundary. This launch-config archive analysis does not revise those outcomes.

## Decision and next discriminator

**Closed for the historical Attempt 04:** explicit `safetensors` checkpoint load format, `mp` executor, TP=1, archived consistency/lineage, and observed auto-prefetch-disabled startup marker.

**Still unproven:** resolved `LoadConfig`/strategy and multithread default, exact `get_tensor`→mapping→weight-loader event ordering, EP/MTP I/O decisions, CT `ModelWeightParameter` and `w13_weight_packed`/`w2_weight_packed` scale/alias completion and buffers for split layers 8 and 11.

Before any CT deferred-w13 implementation, perform a **source-only, no-model** CT per-parameter lifecycle review: map exact packed shapes, component scales, weight_loader calls and `get_numel_loaded` semantics to the installed H38 source. The existing archived checkpoint/flags are not a sufficient buffer bound or justification for transplanting historical ModelOpt M1 `device="meta"`.

No unchanged checkpoint rescan, new H38 model/GPU run, protection tuning, `drop_caches`, image/source mutation, R33, PR Ready/merge or managed promotion is authorized. PR #259 stays **Draft/Open**.
