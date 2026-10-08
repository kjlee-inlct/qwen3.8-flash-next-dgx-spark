# H38 CT deferred-w13 mitigation — M1 transfer feasibility / static gate — 2026-10-08

Status: **DESIGN / GUARDED CPU-ONLY SOURCE PREFLIGHT STAGED** — **NO H38 PATCH, NO CHECKPOINT SCAN, NO DGX RUN, NO LIVE MITIGATION TEST**.

## Decision: do not transplant historical M1

The separate historical branch `exp/m1-deferred-meta-w13` at
`4d72f8750e8a7beaec96a869e2dbfeaa7d4c747a`
contains an **unqualified** M1 prototype:

- `scripts/patch-v029-m1-deferred-meta-w13.py`
- `scripts/Dockerfile.v029-m1-deferred-meta-w13`
- `scripts/benchmark/check-orcarouter-m1-deferred-meta-w13-image.sh`
- `scripts/benchmark/inspect-orcarouter-m1-checkpoint-order.py`
- `scripts/benchmark/evidence/orcarouter-m1-deferred-meta-w13-plan-20261006.md`

The prototype inherits the **R28 diagnostic image**, modifies
`ModelOptNvFp4FusedMoE`, creates its `w13_weight` on
`device="meta"`, and installs native `initialize_online_processing(layer)`
so materialization can happen during checkpoint loading instead of the
~3-second model constructor. It does not directly target the preceding
800 MiB logical RM request family. M1 was **excluded from PR #244's
canonical main merge** and there is no accepted M1 live mitigation
result in that branch's evidence catalog.

**The production H38 image uses a different class and patch ancestry.**
It inherits H11/H12 packed `ModelWeightParameter` on
`CompressedTensorsW4A4Nvfp4MoEMethod`, with stored names
`w13_weight_packed` / `w2_weight_packed` and H12 post-load alias
registration. The actual H38 installed-image source contract is
recorded as PASS at:
`orcarouter-h38-exact-image-source-contract-result-20261008.md`
(image `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`).

The M1 string-anchored ModelOpt patch cannot be applied directly to
this H38 compressed-tensors class. Its *concept* of deferring w13
storage can only become a new CT-specific candidate after its
loader/materialization and checkpoint-order prerequisites are proven.
No H38 CT meta patch was made here.

## Evidence-based opportunity, not guaranteed savings

Historical R28/R29 order-4 **logical RM activity** inside its chosen
constructor interval (H6 ModelOpt diagnostic) was
`76,846.375 MiB`, including:

| Observed R28 repeated request family | Logical volume | Direct evidence |
|---|---:|---|
| 400 MiB × 48 | 19,200 MiB | R30: exact one-per-w13 construction interval |
| 800 MiB × 48 | 38,400 MiB | R31: all 48 precede `ModelOptNvFp4FusedMoE.create_weights()` |
| Other constructor request activity | 19,246.375 MiB | R29: remaining sizes, not a unique tensor owner |

A hypothetical deferral of all 48 **400 MiB requests** might remove
up to `19,200 MiB` of **that diagnostic constructor's** logical
request volume if the allocator does not compensate elsewhere, but
may simply move the requests to checkpoint loading, causing a later
peak. It **does not** predict a 19.2 GiB resident-memory reduction
or say that H38 has the identical request-size histogram.

H38 attempt 01 independently showed `+74,761.516 MiB` approximate
5-s physical-page accounting residual. The H38 exact-image source
check confirmed `h11_tensor_allocations_retained=YES`. The H38
original CUDA/RM allocation cause remains unmeasured. No safe
watermark or monitor relaxation follows from these figures.

## Static source prerequisites — safely inspect installed H38

New staged (not yet executed) tooling:

- `scripts/benchmark/inspect-h38-ct-meta-prerequisites.py`:
  Python stdlib AST/source reader; never imports `torch` or vLLM.
- `scripts/benchmark/check-h38-ct-meta-prerequisites.sh`:
  exact checkout/clean tree/image ID and inherited H11/H12/H38
  label guards, CPU-only ephemeral unprivileged runc container
  with no network, no image pull/build, no GPU/model load.
- `tests/test_h38_ct_meta_prerequisites.py`: synthetic
  positive/negative source structure and guarded-runner tests.

The inspector reads and SHA256-fingerprints **six installed source
files**, then checks the following prerequisites:

1. H38 CT `create_weights()` still uses
   `ModelWeightParameter(data=torch.empty(...))` for packed
   `w13_weight` and `w2_weight`; the untouched baseline
   has no explicit `device` parameter on either `torch.empty`.
2. The H11 `weight_loader` attribute and H12 packed registration
   plus post-load object alias are present.
3. `BaseModelLoader` has the native `uses_meta_device` online
   quantization/finalization gate.
4. `reload/layerwise.py` has the native online weight-loader wrapper
   and materialize/process sequence, with `materialize_layer`
   and `get_layer_size` sources installed.
5. `RoutedExperts` resolves its quant method before calling
   `create_weights()`.

**A source-prerequisite PASS is deliberately NOT a meta-w13
implementation PASS.** It does not validate dynamic loader wrapping,
buffer ownership, per-layer `load_numel_total`, device affinity,
parameter subclass restoration, or H12 post-load correctness after
meta materialization. The 18-shard checkpoint key order has not been
examined for this proposed H38 CT variant. All these are independent
required gates; the check outputs explicit `..._proven=NO` fields.

### One-time CPU-only preflight after static CI PASS

```bash
(
  set -Eeuo pipefail
  cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark
  git fetch --prune origin
  git switch feat/h38-managed-integration
  git pull --ff-only origin feat/h38-managed-integration
  TARGET="$(git rev-parse HEAD)"
  test -z "$(git status --porcelain=v1 --untracked-files=all)"
  H38_CT_META_SOURCE_TARGET_SHA="$TARGET" \
    bash scripts/benchmark/check-h38-ct-meta-prerequisites.sh \
    2>&1 | tee /tmp/h38-ct-meta-source-prerequisites.txt
)
```

The subshell's `pipefail` propagates any invalid source contract;
keep the original full stdout/stderr for review. No existing H38
candidate should be started to satisfy this preflight.

## Next discriminators before any actual CT patch

The new **CT-specific** candidate remains blocked until:

1. **Source/static**: the exact H38 image prerequisite checker PASS,
   and exact H38 installed layerwise code independently reviewed for
   `meta` Parameter subclass materialization and preservation of
   H11 `weight_loader`, H12 alias behavior, parameter dtype/shape,
   scale processing and TP metadata.
2. **Actual checkpoint order/peak-buffer risk**: metadata-only
   inspection of the **OrcaRouter production checkpoint**'s
   18 safetensors shards, as consumed by H38's pinned loader
   (not the H6 checkpoint used by M1). Confirm ordering and whether
   all required weights/scales for one layer arrive before later
   layers; measure conservative *simultaneously buffered tensor
   bytes*, not merely a count of contiguous `.experts.` keys.
   Failure or unknown must block a live model-load experiment.
3. **Offline implementation**: separately scoped CT-specific
   `w13`-only `meta` prototype with synthetic layerwise
   load/alias/shape tests; preserve w2, scales, expert count, config,
   checkpoint content, H38 determinism kernels and provenance.
   No unreviewed global `uses_meta_device` class toggle that
   changes other CT layers.
4. **Later measured acceptance** (not authorized now): if a
   single guarded matched-shape experiment is explicitly justified,
   record 400 and 800 MiB **logical RM request families separately**
   before and after first weight fill, independently measured
   node0 Normal and whole-host physical accounting, peak buffer/swap,
   `FUNCTIONAL` and `HOST-STABILITY` with **unchanged** strict
   RM/fatal protection semantics. No single READY or zero-OOM
   observation can replace these gates.

## Explicitly rejected shortcuts

- **Do not** paste `patch-v029-m1-deferred-meta-w13.py` into H38:
  it targets `ModelOptNvFp4FusedMoE`, not H38 CT.
- **Do not** use generic `--cpu-offload-gb`, direct CPU/UVA
  `get_cuda_view_from_cpu_tensor`, or huge `cudaHostAllocMapped`
  as a proxy for delaying backing; M1 source review already rejected
  these due to host pinned-memory pressure risk.
- **Do not** call a materialization timing shift a total memory
  reduction; later buffered checkpoint weights can make peak worse.
- **Do not** silently broaden R33 RM/UVM/CUDA tracing or change
  watermarks, swap, compaction, drop-caches or monitor settings.
- **Do not** merge M1 or promote PR #259.

**Decision:** M1's approach is a **conditional CT-specific research
candidate**, not an accepted or directly portable H38 mitigation.
Current H38 managed state remains `PROTECTED_STOP`,
`FUNCTIONAL=NOT_REACHED`, `HOST-STABILITY=INCONCLUSIVE`.

## Static implementation CI result — 2026-10-08

- Implementation commit: `96f2aafff2297760595962b64a0ae981c66bc400`.
- GitHub Actions `37778807130`: **SUCCESS / 613 of 613 unit tests**, with
  shell syntax, ShellCheck, Python compile and whitespace PASS.
- These are repository-level synthetic/static test results only. No
  operator-provided actual H38 CT meta prerequisite checker output
  exists yet, no checkpoint-key-order feasibility gate ran, and no
  CT meta-w13 patch, new image or host memory experiment was made.
