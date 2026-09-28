# Runtime architecture and stability policy

This project treats the model checkpoint and serving engine as two independent axes.

```text
model profile
  ├─ orcarouter  stable / default
  ├─ nvidia      experimental / optional
  ├─ mazinb      candidate / not installable
  └─ lychee888   candidate / not installable

serving backend
  ├─ vllm        stable / implemented
  └─ sglang      planned / not implemented
```

## Stability rule

The default installation path is always the most qualified OrcaRouter configuration.
A faster or smaller alternative is not promoted merely because it boots. Promotion
requires the same lifecycle and correctness gates used by the primary profile:

1. pinned model revision and complete checkpoint verification;
2. model-header/config compatibility inspection;
3. clean install/resume/uninstall ownership semantics;
4. managed systemd replacement and rollback;
5. doctor with zero failures and zero warnings after committed startup;
6. deterministic/correctness diagnostics appropriate to the runtime;
7. repeatable decode and prefill measurements;
8. documented profile-specific memory, PLE, quantization, and parser requirements.

Candidate profiles stay visible in the registry so they can be researched without
silently becoming installer choices.

## Model profiles

### OrcaRouter — stable/default

`orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` is the project's primary model.
All performance work is subordinate to stability and correctness on this profile.
Experimental image/kernel work must remain opt-in until it passes the qualification
gates above.

### NVIDIA — experimental

The NVIDIA profile is maintained as an optional comparison/compatibility path. Its
checkpoint-specific mixed-precision requirements must not leak into OrcaRouter defaults.

### mazinb — candidate

`mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4` is tracked as a candidate. It keeps a
BF16 PLE and uses an experts-focused NVFP4 layout, so it is useful as a future
checkpoint/quantization comparison. It is intentionally not installable until a pinned
revision and local DGX Spark qualification are recorded.

### lychee888 — candidate

`lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE` is tracked as a candidate.
Its FP8 PLE materially changes the PLE loading/runtime requirements and therefore needs
its own compatibility work and qualification before becoming selectable.

## Serving backends

### vLLM — stable

vLLM remains the only implemented backend. Existing lifecycle, doctor, benchmark,
proxy, service, and rollback behavior continue to target vLLM.

### SGLang — planned

SGLang is a future optional backend, not a replacement for vLLM. Backend integration
will be added behind a dedicated registry/adapter boundary. Do not add a manifest
`SERVING_BACKEND` field until an actual second backend can install, run, validate, and
uninstall end to end; doing so earlier would add migration risk without runtime value.

## Promotion flow

```text
candidate
   │  pin revision + compatibility work
   ▼
experimental
   │  install/lifecycle/correctness/performance qualification
   ▼
stable
```

There is exactly one default stable model profile at a time. Currently that is
`orcarouter`.


## OrcaRouter H38 runtime qualification track

The stable *model profile* and the qualified *runtime variant* are separate concepts.

For OrcaRouter NVFP4 on one DGX Spark GB10 with vLLM v0.29, the H38
determinism investigation qualified the following runtime roles:

| Runtime role | Profile | Marlin canonicalization scope |
|---|---|---|
| validated H38 production runtime | `hybrid-h38-deterministic` | decoder-only |
| explicit decoder A/B control | `hybrid-h38-decoder-scope` | decoder-only |
| broader fallback/regression control | `hybrid-h38-all-scope` | all Marlin calls |

The decoder-only and all-call variants each passed two fresh-container
determinism matrices plus one isolated fresh-compile matrix. No determinism
advantage was observed for all-call, so decoder-only is the preferred H38
runtime under the minimum-change principle.

This qualification currently applies to the dedicated v0.29 runtime helper
(`scripts/runtime/orcarouter-v029.sh`). It is **not yet the same thing as the
transactional installer/systemd-managed service path**. `install.sh`,
`scripts/serve.sh`, the installation manifest, rollback flow, and managed
service qualification still need an explicit H38 integration/requalification
before the managed service can be said to use the H38 production runtime.

The canonical experiment evidence remains in `scripts/benchmark/README.md`;
`docs/H38-DETERMINISM.md` is the concise operational summary.
