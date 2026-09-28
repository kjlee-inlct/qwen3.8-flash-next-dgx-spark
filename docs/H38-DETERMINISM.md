# H38 determinism repair status

This document is the concise operational status for the OrcaRouter NVFP4
determinism repair on one NVIDIA DGX Spark GB10 using vLLM v0.29.

The canonical experiment log remains `scripts/benchmark/README.md`. This file
summarizes the current supported conclusion, runtime roles, validation gates,
and known integration gap.

## Supported root-cause statement

Under the tested OrcaRouter NVFP4 / vLLM v0.29 / GB10 conditions, legal
physical within-expert routed-token ordering can vary, and the Marlin MoE output
is sensitive to that physical ordering.

Canonicalizing the valid routed-token ordering immediately after
`moe_align_block_size()` removes the captured local W13-to-final-MoE
divergence. The intervention changes ordering only; routed membership, expert
IDs, padding semantics, weights, and GEMM implementation remain unchanged.

Do not generalize this into claims that CUDA is racy or that every Marlin
kernel is intrinsically nondeterministic.

## Production scope decision

Matched scope validation completed for decoder-only and all-call
canonicalization.

Each scope passed:

- fresh-container cycle 1;
- fresh-container cycle 2;
- one isolated fresh-compile lifecycle;
- 1K / 128 x20 standalone;
- 32K / 128 x10 standalone;
- forward QSA sweep 1K -> 2K -> 4K -> 8K -> 32K, five repeats per size;
- reverse QSA sweep 32K -> 8K -> 4K -> 2K -> 1K, five repeats per size.

Every validated gate reported `unique_hashes=1` and every QSA sweep reported
`first_failure_tokens=null`.

Stable standalone hashes were the same across both scopes:

```text
1K:
44867e5c36d54b5bbec26f7c4f7c500783602a4bbc1b1545758929fc1c763670

32K:
d6fa888525cd888595d9c51c2a24aa248cce55cfd35d16bdc0ddbba0a8e78d39
```

No determinism advantage was observed for all-call canonicalization.
Decoder-only is therefore preferred under the minimum-change principle.

## Runtime role mapping

| Role | Runtime profile | Image | Scope |
|---|---|---|---|
| H38 production runtime | `hybrid-h38-deterministic` | `vllm-orcarouter-v029-h38-decoder-scope:v1` | decoder |
| decoder A/B control | `hybrid-h38-decoder-scope` | `vllm-orcarouter-v029-h38-decoder-scope:v1` | decoder |
| fallback/regression control | `hybrid-h38-all-scope` | `vllm-orcarouter-v029-h38-deterministic:v1` | all calls |

The profile names are runtime roles. The all-call image keeps its historical
name for regression continuity; do not infer its preferred production role from
the image tag.

## Production-alias gate

After scope promotion, validate the production alias itself with:

```bash
bash scripts/benchmark/run-h38-production-gate.sh
```

This runs the same 1K, 32K, forward-QSA, and reverse-QSA gates against:

```text
hybrid-h38-deterministic/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

The production alias has already been observed to start successfully with the
decoder-scope image and runtime revision `runtime-production-decoder-scope`.
The final alias matrix result must be recorded in
`scripts/benchmark/README.md` when completed.

## Managed-service integration gap

The H38 runtime qualification above is for
`scripts/runtime/orcarouter-v029.sh`.

The transactional managed-service path is still separate:

- `install.sh`
- `scripts/model/model-profiles.sh`
- installation manifest image defaults
- `scripts/serve.sh`
- `scripts/runtime/service-runner.sh`
- systemd replacement / rollback / runtime attestation

That path currently does not select the H38 decoder image as its OrcaRouter
default. Do not describe the installer-managed service as H38 production until
that integration is implemented and requalified through its lifecycle,
rollback, doctor, determinism, and performance gates.

This gap is intentionally documented rather than silently changing the managed
runtime based only on the experimental-runtime qualification.

## Remaining limitations

The supported conclusion is limited to:

- OrcaRouter checkpoint revision
  `c1209bda15a6bbc4c68b585e93d40c0d85f50306`;
- single DGX Spark GB10;
- vLLM v0.29;
- tested runtime controls including exact QSA, MTP k=2,
  `max_num_seqs=3`, prefix caching disabled, and PLE mmap;
- the benchmark matrix documented above.

It does not prove universal determinism across different checkpoints, GPUs,
vLLM versions, kernels, scheduling modes, or prompt distributions.

## Preserve for regression

Do not delete while the H38/H20 evidence remains operationally relevant:

- H12 base image;
- H20 diagnostic images and instrumentation;
- H38 decoder and all-call images;
- retained model directories and PLE files;
- prior benchmark reports and failed experiments.

Failed hypotheses, instrumentation failures, and superseded scope conclusions
remain part of the canonical history in `scripts/benchmark/README.md`.
