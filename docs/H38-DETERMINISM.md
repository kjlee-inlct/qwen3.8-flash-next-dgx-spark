# H38 determinism repair status

This document is the concise operator-facing status for the OrcaRouter NVFP4
determinism investigation on one DGX Spark GB10 with vLLM v0.29.

The detailed experiment chronology remains in
`scripts/benchmark/README.md`. This file records the current supported
conclusion and the boundary between the validated H38 runtime candidate and the
repository's managed stable/default installation path.

## Supported conclusion

Under the tested OrcaRouter NVFP4 / vLLM v0.29 / GB10 conditions, legal
within-expert routed-token ordering can vary and the Marlin MoE output can be
sensitive to that physical ordering.

The H38 repair canonicalizes routed-token order before Marlin MoE GEMM
execution. Matched validation compared two scopes:

- decoder-only: canonicalize tagged decoder Marlin MoE calls;
- all-call: canonicalize every Marlin MoE call.

Both scopes passed two fresh-container matrices and one isolated fresh-compile
matrix. Each matrix contained:

- 1024-token / 128-output determinism x20;
- 32768-token / 128-output determinism x10;
- forward QSA sweep: 1K, 2K, 4K, 8K, 32K x5;
- reverse QSA sweep: 32K, 8K, 4K, 2K, 1K x5.

No determinism advantage was observed for all-call canonicalization. The
preferred H38 repair scope is therefore **decoder-only**, following the
minimum-change principle.

The stable regression markers in the successful matched runs were:

```text
1K:
44867e5c36d54b5bbec26f7c4f7c500783602a4bbc1b1545758929fc1c763670

32K:
d6fa888525cd888595d9c51c2a24aa248cce55cfd35d16bdc0ddbba0a8e78d39
```

These hashes are regression markers for the tested controls, not universal
correctness oracles.

## Runtime roles

| Role | Runtime profile | Image | Scope |
|---|---|---|---|
| preferred H38 candidate alias | `hybrid-h38-deterministic` | `vllm-orcarouter-v029-h38-decoder-scope:v1` | decoder |
| explicit decoder A/B control | `hybrid-h38-decoder-scope` | `vllm-orcarouter-v029-h38-decoder-scope:v1` | decoder |
| broader fallback/control | `hybrid-h38-all-scope` | `vllm-orcarouter-v029-h38-deterministic:v1` | all |

The historical all-call image filename is retained so existing results and
Docker caches remain traceable.

## Important: managed stable/default has not moved yet

The H38 scope-selection question is closed for the tested matrix. The
repository-wide **managed stable/default installation has not yet been promoted
to H38**.

Today, the install/service path is still defined by the `orcarouter` model
profile in `scripts/model/model-profiles.sh`, `install.sh`, and
`scripts/serve.sh`. That path has separate lifecycle, systemd, rollback,
doctor, and ownership contracts.

Before H38 can replace that managed path, the repository promotion rules in
`docs/ARCHITECTURE.md` require at least:

1. installer image build/refresh integration;
2. managed `serve.sh` parity with the validated H38 v0.29 controls;
3. install/resume/uninstall ownership tests;
4. systemd replacement and rollback qualification;
5. doctor with zero failures and zero warnings after committed startup;
6. production-alias correctness gate;
7. matched decode and prefill regression measurements;
8. documentation of the resulting memory/PLE/cache/runtime contract.

Do not change only `PROFILE_IMAGE` to the H38 image. The current managed
OrcaRouter runtime and H38 v0.29 candidate differ in PLE handling and runtime
arguments, so an image-only switch would not reproduce the validated H38
configuration.

## Reproducible candidate gate

Start the H38 candidate using:

```bash
./scripts/runtime/orcarouter-v029.sh start \
  --profile hybrid-h38-deterministic

./scripts/wait-ready.sh \
  --container qwen38-h38-deterministic-v029 \
  --model hybrid-h38-deterministic/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --timeout 3600
```

Then run the canonical alias gate:

```bash
bash scripts/benchmark/run-h38-production-gate.sh candidate1
```

Results are retained under
`scripts/benchmark/results/local/h38-production-gate/`.

## Evidence boundary

The evidence supports the decoder-only repair scope under the tested
configuration. It does not prove universal determinism for all checkpoints,
GPU architectures, prompt distributions, kernels, or future vLLM versions.
It also does not establish a generic CUDA race or a universally nondeterministic
Marlin implementation.
