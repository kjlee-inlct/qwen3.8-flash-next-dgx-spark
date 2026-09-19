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
