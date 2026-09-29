# Runtime architecture and stability policy

This project treats the model checkpoint and serving engine as two independent axes.

```text
model profile
  ├─ orcarouter        stable / default / installable
  ├─ nvidia            experimental / installable
  ├─ mazinb            experimental / installable
  ├─ orcarouter-hybrid experimental / installable / generated H6
  └─ lychee888         planned / not installable

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

Profiles may be made selectable once their preparation/runtime path is defined, but
selectability is not itself a qualification claim. Experimental profiles can therefore be
installable while some or all DGX managed-lifecycle gates remain pending. Promotion to
stable still requires the full gate above.

## Model profiles

### OrcaRouter — stable/default

`orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` is the project's primary model.
All performance work is subordinate to stability and correctness on this profile.
Experimental image/kernel work must remain opt-in until it passes the qualification
gates above.

### NVIDIA — experimental

The NVIDIA profile is maintained as an optional comparison/compatibility path. Its
checkpoint-specific mixed-precision requirements must not leak into OrcaRouter defaults.

### mazinb — experimental/installable

`mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4` has a defined installer/runtime path,
but it has **not** completed the full managed DGX Spark lifecycle qualification. The
verified installer evidence so far is registry exposure plus a non-mutating dry-run with
the pinned `f2c21eb` revision and the local `vllm-orcarouter-v029:v1` image plan.

Actual checkpoint download, image build, systemd startup/readiness, doctor, restart,
uninstall preservation, API behavior, determinism/correctness, and performance remain
qualification work. Until those gates pass, mazinb stays experimental even though it is
selectable from `install.sh`.

### OrcaRouter hybrid — experimental/installable

`orcarouter-hybrid` is the installer-facing result of the checkpoint isolation
track, not an alias for the H38 runtime repair. The installed model is the H6
`h6-modelopt-w4a16` checkpoint produced by:

```text
pinned OrcaRouter + pinned mazinb
  -> H3 quant-layout-mazinb-experts
  -> H4 orca-all
  -> H5 neutral input_scale=1.0
  -> H6 ModelOpt W4A16_NVFP4
```

H6 changes only the final quantization configuration relative to H5; its tensor
payload is inherited through the validated parent-link chain. The managed
runtime therefore uses vLLM v0.29 with PLE mmap, exact QSA, MTP k=2, and
read-only mounts for the OrcaRouter base, H3, H4-all, and H5 parents.

This profile is experimental and non-default. The managed warm/reuse path has passed
functional/restart validation, the no-uninstall Hybrid -> OrcaRouter -> Hybrid round trip
has passed without checkpoint redownload/rebuild, and the 2026-09-29 CMA-aware
host-stability repair gate passed 30/30 repeated runtime validations. Those gates are
narrower than a clean-host qualification: the complete source-download + H3→H6 build +
managed-service lifecycle on a genuinely clean DGX Spark has not yet been qualified.
Historical checkpoint/determinism evidence also does not substitute for that clean-host
gate, and this installer profile remains distinct from the separate H38 decoder-only
runtime qualification track below.

### lychee888 — planned

`lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE` is a planned profile.
Its FP8 PLE materially changes the PLE loading/runtime requirements and therefore still
needs compatibility and lifecycle qualification before becoming selectable.

## Serving backends

### vLLM — stable

vLLM remains the only implemented backend. Existing lifecycle, doctor, benchmark,
proxy, service, and rollback behavior continue to target vLLM.

### SGLang — planned

SGLang is a future optional backend, not a replacement for vLLM. Backend integration
will be added behind a dedicated registry/adapter boundary. Do not add a manifest
`SERVING_BACKEND` field until an actual second backend can install, run, validate, and
uninstall end to end; doing so earlier would add migration risk without runtime value.

## Cumulative asset ownership

`install.env` remains the active runtime/profile manifest, but its historical
`MODEL_OWNED` and `IMAGE_OWNED` fields are necessarily single-asset views.
Profile switching therefore uses a separate
`~/.local/state/qwen38-spark/asset-ownership.json` registry for cumulative
destructive authority.

The registry is asset-centric rather than profile-centric. Each model directory
or Docker image is recorded independently with:

- explicit owned vs observed/unowned state;
- a claimed/ready state so interrupted creation is distinguishable;
- a model-manifest SHA-256 or Docker image ID once ready;
- exact dependency locators for linked Hybrid stages.

Ownership is claimed before the installer creates a previously absent asset and
is finalized only after the managed manifest or image ID exists. Reusing an
existing asset never upgrades it to owned. If an already-owned manifest or image
ID changes unexpectedly, install/purge fails closed rather than silently
adopting the drift.

For Hybrid H6 the retained runtime dependency graph is recorded explicitly:
H6 depends on H5/H4/H3/OrcaRouter, H5 on H4/H3/OrcaRouter, H4 on
H3/OrcaRouter, and H3 on OrcaRouter. `--purge-all` deletes dependents before
dependencies and refuses the entire purge if an unowned retained asset still
depends on an owned candidate. The mazinb checkpoint is a build-time input and
is not a retained H3-H6 runtime dependency.

Legacy migration is deliberately conservative. The current
`MODEL_OWNED=1`/`IMAGE_OWNED=1` values may seed the registry once, but assets
whose ownership was already lost by an older profile switch are not inferred
from filenames, managed manifests, or image tags.

## Persisted profile-switch lifecycle

Managed model-profile replacement is a transaction above the existing runtime
container transaction. Model preparation does not mutate the canonical
`install.env`; the target is built in
`install.env.profile-switch-candidate`. The durable profile state machine is:

```text
preparing
  -> activated
  -> runtime_committed
  -> committing
  -> idle
```

`preparing` is written before target preparation. `activated` records both
the previous manifest backup and the digest of the service-ready target before
the target manifest becomes the live service input. The nested runtime
transaction then preserves the old container, starts and validates the target,
and writes `runtime-commit.env`. The profile transaction accepts the target
only when the attestation matches the current container ID, immutable runtime
root, image, model mount, and exact served-model name.

Recovery follows proof rather than process-exit traps. If target commit evidence
is complete, recovery finishes the target manifest. If the target is not
committed and the old runtime still matches the backed-up manifest, recovery
restores the previous profile. A boundary that cannot prove either side remains
persisted and fails closed; doctor reports it and uninstall refuses mutation.
This includes the deliberately ambiguous interval after a runtime transaction
commit but before its runtime attestation is durable.

The installer recovers this transaction at startup. The systemd service also
checks it before parsing the install manifest, but defers while the installer
holds the global lifecycle operation lock so a normal in-flight cutover is not
mistaken for a crash.

## Promotion flow

```text
planned
   │  define checkpoint/runtime path
   ▼
in-progress
   │  integration + qualification
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
