# Fresh DGX Spark: one-Wizard Hybrid H6 installation acceptance

Updated: 2026-10-14 (KST). Status: **SOURCE PATH PRESENT; FRESH HOST E2E NOT QUALIFIED**.

## User requirement and boundary

On a newly provisioned DGX Spark with its supported Ubuntu/NVIDIA GPU and Docker
prerequisites available, selecting `orcarouter-hybrid` through the installer
Wizard must prepare every project-owned dependency and proceed through installation
and managed runtime startup without requiring the operator to run a separate
H3/H4/H5/H6 builder. Do not confuse the existence of an installer path with a
completed clean-host acceptance test. This requirement does not approve
mutations on the existing protected one-DGX managed installation.

The selectable Hybrid is **H6 ModelOpt W4A16** (`local/orcarouter-mazinb-h6-w4a16`),
not the separate H38 runtime candidate. Its registry is
[`scripts/model/model-profiles.sh`](../scripts/model/model-profiles.sh).

## Existing source route (verified by source inspection)

1. `wizard.sh` delegates installation/resume to the existing `install.sh`,
   which resolves the selected `orcarouter-hybrid` profile with
   `PROFILE_LOCAL_BUILD=1`.
2. A complete, provenanced H3 may be reused. Otherwise, the installer checks
   disk capacity and gated access for the pinned **OrcaRouter and mazinb**
   checkpoint inputs, then downloads and verifies both.
3. The installer checks/creates the project PLE swap using the existing swap
   manager, builds the `vllm-orcarouter-v029:v1` builder/runtime image when
   absent, and invokes `scripts/model/prepare-orcarouter-hybrid.sh build`.
4. That builder reuses valid stages or generates H3 quant-layout, H4 orca-all,
   H5 neutral input-scale, and H6 W4A16 in order; nonempty invalid stages
   are **not automatically deleted**.
5. The installer invokes `validate-orcarouter-hybrid.py` before continuing
   with its existing image, managed immutable-release, API, service and
   startup flow. The runtime safety watchdog and NVIDIA RM gates still apply.

This is a source-level description of intent and conditional code branches.
It does **not** prove Docker build success, complete Hugging Face access,
sufficient space for all generated stages, GPU compatibility or model startup.

## Host-free source acceptance

Regression tests in `tests/test_installer_plan_parity.py` exercise a
disposable-HOME, brand-new `orcarouter-hybrid` **dry-run**, confirm the H6
model/revision/image/parent paths, mandatory memory protection, equivalent CLI
preview/replay and the absence of model/state creation. They also pin the
source dependency-download, H6 build and validation call chain.

CI PASS is necessary but **not sufficient** for a freshly installed DGX.
It intentionally does not download weights, build images, write swap,
start/stop containers, alter systemd or exercise the GPU.

## Actual clean-host acceptance gate (pending)

A future operator-approved validation on a truly fresh DGX must separately
record: source SHA, clean host baseline, NVIDIA driver/GPU and Docker runtime
health, available disk (including **intermediate generated stages and reserve**),
HF gated-access entitlement, memory/swap state and any unrelated services.
Then follow the real Wizard installation under supervision and preserve
one log and exact identities for each checkpoint, builder image, generated
stage manifest, managed release, Docker container and service.

After installation, verify `/health`, exact `/v1/models`, real inference,
memory-watchdog heartbeats, non-CMA and swap pressure, NVIDIA RM/Xid events,
and an explicit safely supervised stop/restart path. Record source identity,
Docker image digest, errors, retries and stage manifests. On a failure, retain
forensic evidence and avoid automatic deletion or an uncontrolled retry.

No real fresh-DGX Hybrid E2E run, functional PASS, host-stability PASS,
or performance benchmark may be claimed until its actual physical results
are captured. Benchmark-before-reclaim and Hybrid H3/H4/H5 dependencies remain
binding; OrcaRouter A/B benchmarking is deferred by current operator priority.

## Safe inspection command (no downloads or host mutations)

```bash
./install.sh --lang en --model orcarouter-hybrid \
  --model-root "$HOME/Workspace/llm/models" \
  --no-start --yes --dry-run
```

This only verifies the normalized plan on that checkout. It is not the
physical installation acceptance test, and must not be used to imply one.
