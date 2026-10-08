# H38 exact installed-image source contract — static preflight plan — 2026-10-08

Status: **STAGED / STATIC SOURCE INSPECTOR ONLY / NO DGX EXECUTION YET**

## Motivation and strict evidence boundary

R23 directly observed the early physical burst carried by NVIDIA RM
`nv_alloc_pages` / `nv_alloc_system_pages` in its own experiment.
R29–R32 closed 48 repeated `800 -> 400 MiB` request pairs in the **R28**
diagnostic image, with 400 MiB events localized one-for-one to expert
packed `w13_weight` construction. The 800 MiB events occurred before
MoE `create_weights` started, and the R28 exact-image source review did
not find a distinct direct pre-create model-weight allocation.

H38 independently measured an approximately `+74,761.516 MiB` five-second
unexplained physical-page residual but did not capture its own RM-call
trace. H38 additionally uses the **H11/H12 patched compressed-tensors
source** and decoder-scoped runtime patches. The R28 source check must
not be treated as a completed H38 image check.

This plan adds the *lowest-risk, actionable source-contract preflight*,
not a model restart or a new R33 allocation experiment. It tests only
what the **exact already-installed H38 image's source** says; it cannot
prove that a tensor allocation causes the NVIDIA driver's 800 MiB event.

## Code and identity

- `scripts/benchmark/check-h38-exact-image-source.sh`
  validates a caller-specified 40-hex SHA and clean checkout,
  checks the exact `vllm-orcarouter-v029-h38-decoder-scope:v1` image
  and its inherited `qwen38.h11`, `qwen38.h12`, and `qwen38.h38scope`
  labels, and records image ID.
- `scripts/benchmark/inspect-h38-exact-image-source.py`
  parses the actual image-installed sources using Python stdlib AST
  without importing `vllm`, `torch`, or CUDA. It also invokes the
  existing R32 source inspector **on this very same H38 image**;
  a changed constructor/source order or an invalid R32 result fails closed.
- `tests/test_h38_exact_image_source.py` exercises pure synthetic
  H11/H12/H38 fixtures and invalid paths; static CI is **not** proof
  that the physical H38 image passed.

The image checker uses an **ephemeral Docker container for CPU-only
source inspection**, with `--runtime runc --network none --pull never
--read-only --user 65534:65534 --cap-drop ALL`, 512 MiB memory bound,
a single CPU bound and two read-only script mounts. It does not launch
vLLM, read model weights, access GPU, build/pull an image, change
systemd/managed lifecycle, or alter the memory monitor. A short-lived
isolated Docker container is created and removed, so `docker run` is
**not** literally a zero-Docker-state operation. No daemon/lifecycle
mutation beyond this ephemeral source inspector is authorized.

## Required static source assertions

1. Both `w13_weight` and `w2_weight` **still call
   `torch.empty`** inside the actual installed
   `CompressedTensorsW4A4Nvfp4MoEMethod.create_weights()`, now wrapped
   in `ModelWeightParameter`, with H11 attributes intact.
2. Their `*_packed` parameter registration persists; their H12
   post-load alias registration preserves the parameter object rather
   than rewrapping it as a new `torch.nn.Parameter`.
3. H38 CT decoder-index tagging and Marlin stable token
   canonicalization helper are present, and Humming FP8's
   `use_batch_invariant` source modification is present.
4. The original R32 pre-`create_weights()` ordering and negative
   *direct* tensor-allocation syntax check also passes when pointed at
   the exact H38 installed source. This does not exclude indirect
   allocations through helper/factory constructors.
5. Installed source file SHA256s, full image ID, checkout SHA and
   source-only verdict are included in the output. Neither kernel RM
   tracing nor allocator physical accounting is inferred.

A mismatch invalidates only the **exact-image source-contract
comparison**, not the historical valid R32 outcome. Do not patch the
container/source merely to force the check to pass; collect the
mismatch for separate review.

## One-time host command, after a passing static CI

From DGX Spark at the correct checked-out branch HEAD:

```bash
cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark
git fetch --prune origin
git switch feat/h38-managed-integration
git pull --ff-only origin feat/h38-managed-integration
test -z "$(git status --porcelain=v1 --untracked-files=all)" || exit 1

set -o pipefail
TARGET="$(git rev-parse HEAD)"
H38_EXACT_SOURCE_TARGET_SHA="$TARGET" \
  bash scripts/benchmark/check-h38-exact-image-source.sh \
  2>&1 | tee /tmp/h38-exact-image-source-contract.txt
RC=${PIPESTATUS[0]}
printf "source_check_rc=%s\n" "$RC"
test "$RC" -eq 0
```

This is a strictly source-only static check. Pass or fail, preserve
the full terminal output including docker errors, label mismatch,
R32 checker exit status and source checksums. Before treating the
result as canonical, confirm `H38_EXACT_IMAGE_SOURCE_PREFLIGHT=PASS`
and unchanged exact image identity. Do not claim the check ran
unless an operator provides its real output.

## Decision after static source preflight

- PASS: The *syntax/constructor path* under H38 matches the earlier
  R32 source-contract hypothesis. It still does **not** prove the
  NVIDIA RM ownership of a 75 GiB resident footprint nor establish
  that H11/H12/H38 mitigate host allocator pressure.
- INVALID: Investigate only the concrete source/label mismatch,
  without restarting the model or changing protection.
- In either case: continue to require **production-shape FUNCTIONAL
  PASS and HOST-STABILITY PASS** before managed promotion.
- **No R33 live tracing, no generic UVM/CUDA probes, no unchanged
  startup, no monitor weakening, no PR merge.**

## Static implementation CI qualification — 2026-10-08

- Implementation commit: `bf7153536f78b48222dbb68b611b1d31dfa9f7db`.
- GitHub Actions `37747053983`: **SUCCESS**, 606/606 tests; shell syntax,
  ShellCheck, Python compilation and whitespace PASS.
- This qualifies only the implementation and synthetic regressions.
  Installed-image source semantics require a separate operator-provided
  authentic DGX output before claiming an exact-image result.
- Host runtime remains in protected-stop state, no H38 candidate was
  launched and PR #259 is still Draft/Open.
