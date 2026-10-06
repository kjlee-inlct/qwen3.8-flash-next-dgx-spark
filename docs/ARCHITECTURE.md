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

The project additionally keeps **FUNCTIONAL** and **HOST-STABILITY** classifications
separate. Any confirmed NVIDIA RM `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a
valid measured run is HOST-STABILITY FAIL even if fallback recovers and the runtime
reaches READY. Managed defaults such as the 16 GiB KV resilience setting do not override
that strict evidence rule.

Current host-stability and allocator closure is indexed in
`scripts/benchmark/evidence/README.md`. Historical experiment documents preserve what
was known at the time and must not be read as the current project-state summary.

## Model profiles

### OrcaRouter — stable/default

`orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` is the project's primary model.
All performance work is subordinate to stability and correctness on this profile.
Experimental image/kernel work must remain opt-in until it passes the qualification
gates above.

The managed OrcaRouter profile currently uses the 16 GiB KV resilience default.
That setting reduces one controllable pressure source but is not itself a proof that
driver-level RM allocation failure has been eliminated.

### NVIDIA — experimental

The NVIDIA profile is maintained as an optional comparison/compatibility path. Its
checkpoint-specific mixed-precision requirements must not leak into OrcaRouter defaults.

### mazinb — experimental/installable

`mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4` has a defined installer/runtime path and
has now been exercised through live managed activation, but it has **not** completed a
clean HOST-STABILITY qualification.

The checkpoint is pinned to the verified source revision
`f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f` and remains exposed as
experimental/installable. The original 2026-10-02 managed activation used a 24 GiB KV
cache and failed the strict host-stability gate. A controlled temporary 16 GiB run showed
that reduced KV can improve the outcome under one allocator state, but that contrast did
not prove a deterministic fix. The managed profile was subsequently moved to the 16 GiB
resilience value and reached READY, yet a valid managed run still recorded confirmed RM
`NV_ERR_NO_MEMORY`, so the classification remained **FUNCTIONAL PASS /
HOST-STABILITY FAIL**.

Therefore:

- mazinb is installable and can participate in the managed profile-switch lifecycle;
- 16 GiB is the current managed KV resilience value, not a qualification certificate;
- READY, runtime commit, or successful fallback must never be promoted to HOST-STABILITY
  PASS when strict RM failure evidence is present;
- clean-host lifecycle, restart/doctor, correctness/performance, and host-stability
  qualification remain required before any stable promotion.

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

This profile is experimental and non-default. The managed warm/reuse path and
Hybrid -> OrcaRouter -> Hybrid round trip passed functionally. A 2026-09-29
CMA-aware monitor/protection repair also passed its then-defined 30/30 validation
gate; that historical PASS must not be treated as the current host-stability
classification.

Subsequent profile-switch/restart acceptance and the R8–R32 investigation
reproduced NVIDIA RM `NV_ERR_NO_MEMORY` while the runtime could still reach READY,
so the strict classification remains **FUNCTIONAL PASS / HOST-STABILITY FAIL**.

The allocator investigation is no longer open at the R9 level. The current closure is:

- R11 localized the failed host allocation to node0 Normal-zone Unmovable order-4
  demand, Movable fallback/pageblock stealing, high-order acquisition failure,
  rollback, and immediate order-0 retry;
- R21/R22 isolated the common early physical-page burst to roughly 75 GiB in about
  five seconds and separated it from later PLE/swap pressure;
- R23 attributed the measured burst endpoint to direct NVIDIA RM system-memory
  allocation through `nv_alloc_pages` / `nv_alloc_system_pages`, not the selected UVM
  allocation boundaries;
- R24 showed that the H6 W4A16/16 GiB candidate did **not** remove the structural burst;
- R25–R32 localized the dominant userspace timing to first model construction and then
  to the Qwen4Exp decoder construction cadence. The repeated 400 MiB family is closed
  exactly to packed `w13_weight` construction, while the paired 800 MiB family occurs
  before ModelOpt-MoE create-weights and spans mixed userspace placements, supporting a
  lower/global backing-growth event rather than direct ownership by those model-prefix
  markers.

The observed chain is therefore:

```text
model construction
  -> direct NVIDIA RM 64 KiB system-page demand
  -> node0 Normal/Unmovable order-4 depletion/fallback pressure
  -> failed high-order acquisition
  -> rollback
  -> immediate order-0 fallback
  -> recoverable NV_ERR_NO_MEMORY
```

This is a localization/engineering closure, not a claim that every internal proprietary
RM allocation policy is known. Marker overlap remains temporal localization, not causal
ownership, and RM requested bytes remain allocation-activity volume rather than exact
resident ownership.

The repository documents a narrow optional `RECOVERABLE_RM_SYSMEM_FALLBACK`
warning exception for the exact recoverable pattern, but it is not implicitly enabled.
Unless that exception is explicitly adopted for an acceptance leg, any observed RM
`NV_ERR_NO_MEMORY` keeps the Hybrid host classification at FAIL.

These gates are still narrower than a clean-host qualification: the complete
source-download + H3→H6 build + managed-service lifecycle on a genuinely clean
DGX Spark has not yet been qualified. Historical checkpoint/determinism evidence
also does not substitute for that clean-host gate, and this installer profile
remains distinct from the separate H38 decoder-only runtime qualification track
below.

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
