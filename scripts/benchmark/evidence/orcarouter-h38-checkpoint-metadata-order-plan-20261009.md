# H38 production 18-shard checkpoint metadata/order gate — 2026-10-09

Status: **STAGED READ-ONLY METADATA ANALYZER / NO DGX EXECUTION; NO LOADER EQUIVALENCE OR MEMORY STABILITY CLAIM**

## Why this separate gate is necessary

H38's exact installed CT/source prerequisite gate passed from an operator-run
DGX inspection on 2026-10-09; canonical result:
`orcarouter-h38-ct-meta-w13-source-prerequisites-result-20261009.md`.
That result confirms the presence of a native `uses_meta_device` detection,
a layerwise weight-loader wrapper, materialize-and-process logic, and H11/H12 CT
weight/alias syntax. It **does not** validate the production checkpoint
safetensors iterator ordering or the dynamic loader's buffered tensor peak.

The historical M1 ModelOpt/R28 prototype used a checkpoint name-order gate,
but H38 has a separate compressed-tensors implementation and an 18-shard
production OrcaRouter checkpoint. Applying M1's checkpoint findings to H38 is
not justified.

## New tool, scope and provenance

- `scripts/benchmark/inspect-h38-checkpoint-metadata-order.py`:
  reads exactly the safetensors **8-byte length prefix and JSON header**
  from each indexed shard. It uses `safetensors.safe_open(...).keys()` to
  reproduce the *declared default* single-thread per-file key sequence and
  validates header/index key coverage. It **never calls get_tensor or
  get_slice and never reads a tensor payload**.
- `scripts/benchmark/check-h38-checkpoint-metadata-order.sh`:
  guards clean checkout, explicit 40-hex SHA and explicit existing absolute
  checkpoint folder, pinned exact H38 image ID
  `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`,
  and creates only an ephemeral unprivileged **runc, CPU-only,
  no-network, read-only filesystem** container. Mounts precisely the
  caller-provided model directory as read-only plus the source inspector.
  No Docker image build/pull, vLLM model launch or managed state change.
- `tests/test_h38_checkpoint_metadata_order.py`:
  synthetic 18-file/48-layer index and header fixtures,
  including interleaved layers, invalid index and header, traversal paths,
  unexpected files, no-payload/source and runner safety checks.

### Output distinctions

1. Requires precisely **18** shards referenced by
   `model.safetensors.index.json`, with no unindexed shards, duplicate keys
   or missing indexed tensor names, verifies header offsets and
   `safe_open().keys()` membership consistency.
2. Reports the number of routed-expert keys and decoder layers, layer revisits,
   unexpected/missing layer IDs, maximum overlapping expert intervals in the
   full tensor stream and per-shard counts.
3. Reports **two hypothetical** routed-expert byte retention scenarios:
   release at last routed key of each layer, or at the last *any-layer*
   tensor key. Both are **static on-disk bytes from `data_offsets`**, not
   measured pinned-RAM or GPU allocations, and neither bounds all possible
   runtime layerwise buffers.
4. The result deliberately prints:
   `exact_h38_loader_order_contract_verified=false`,
   `all_layerwise_weight_buffers_bounded=false`,
   `meta_materialization_proven=false`, and
   `host_stability_qualified=false`. Even an
   `H38_CKPT_METADATA_ORDER_GATE=PASS` establishes **only the
   metadata order under the declared default loader assumption**, not
   safe dynamic CT meta processing.

### Important unknowns / fail-closed semantics

- The actual installed H38 loader must be separately checked for
  default single-thread/natural-sorted shard order and
  `safe_open().keys()` iteration. Custom streaming, parallel loader, or
  other iterator changes make the metadata-order comparison
  **not transferable**. The analyzer does not assert equivalence.
- The `.experts.` routed-name classifier is a narrow name heuristic,
  not a fully proven mapping of every H38 CT packed parameter and
  associated scale. It rejects missing 48 decoder layers and repeated
  routed layer intervals, rather than silently treating missing evidence
  as PASS. A PASS does not prove scale arrival/completion behavior.
- If the installed container cannot access the chosen source directory
  as UID 65534, the read-only check is INVALID. Do not rerun as
  root or change checkpoint permissions for this experiment.
- No memory-budget threshold is made up: the tool reports static
  byte scenarios but does not call peak-runtime-memory
  qualification PASS/FAIL based on an arbitrary cut-off.

## Operator command (only after repository CI success)

First locate the **actual production OrcaRouter checkpoint**, without
assuming the historical M1/H6 model path:

```bash
find "$HOME/models" -maxdepth 4 -name model.safetensors.index.json -print
```

Select the directory holding the correct H38 production checkpoint
(index plus exactly 18 shards). Do not point the scan at the previous
H6/R28 diagnostic checkpoint or a BF16 Hybrid. Set the real path:

```bash
(
  set -Eeuo pipefail
  cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark
  git fetch --prune origin
  git switch feat/h38-managed-integration
  git pull --ff-only origin feat/h38-managed-integration

  TARGET="$(git rev-parse HEAD)"
  test -z "$(git status --porcelain=v1 --untracked-files=all)"

  MODEL_DIR="/ABSOLUTE/PATH/TO/VERIFIED/ORCAROUTER/CHECKPOINT"
  H38_CKPT_METADATA_TARGET_SHA="$TARGET" \
  H38_CKPT_METADATA_MODEL_DIR="$MODEL_DIR" \
    bash scripts/benchmark/check-h38-checkpoint-metadata-order.sh \
    2>&1 | tee /tmp/h38-checkpoint-metadata-order.txt
)
```

The strict bash subshell with `pipefail` preserves failure of
the guard or metadata inspector. This creates a small original operator-side
text log, but does **not** modify model bytes or commit checkpoint content.
Share the actual terminal output for a separately dated result. No PASS is
claimed for the H38 checkpoint until that output exists.

## Acceptance and next steps

A metadata-order PASS, if obtained, is a **necessary but not sufficient**
condition for considering CT-specific deferred w13:
1. Independently confirm installed-H38 loader iterator semantics
   (not automatically established by old M1 design notes).
2. Confirm CT `ModelWeightParameter` weight-loader wrapping, packed
   parameter completeness, H12 aliasing, exact scale loader
   dependencies and parameter device/dtype behavior through offline
   synthetic dynamic tests **before any live model**.
3. Specify an actual bounded peak-weight buffering strategy before
   allowing a model-start discriminator.
4. Maintain unchanged external protection, strict RM OOM accounting,
   `FUNCTIONAL` and `HOST-STABILITY` classification.

**No CT meta patch, checkpoint payload read, R33, production restart,
monitor relaxation, managed promotion, PR Ready or merge is authorized
by this metadata-only static gate.**
