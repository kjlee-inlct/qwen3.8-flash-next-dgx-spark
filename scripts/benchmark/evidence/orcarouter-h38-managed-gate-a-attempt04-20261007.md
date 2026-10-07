# OrcaRouter H38 managed-service Gate A attempt 04 — 2026-10-07

Status: CUTOVER BLOCKED — BASELINE-MAIN MEMORY-PROTECTION POLICY STOPPED LEGACY CPU-OFFLOAD RESTART

## Provenance

- repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- branch under qualification: `feat/h38-managed-integration`
- attempted target: `c4a8c543bc62add17a76048758032d9bf9a53af4`
- PR base main: `a7c563705edba780747bf815278f6b77c8a41b08`
- installed current release before the attempt: `ff67bab3c94d6992f61b9535836df97f03b9c022`
- installed profile: `orcarouter`
- pre-H38 managed image: `vllm-skinny-tp1:v1`

## Preflight and baseline

The executable-mode remediation from attempt 03 was confirmed both in the Git tree and
in the staged immutable release:

```text
scripts/serve.sh mode: 100755
mode=-rwxrwxr-x numeric=775 .../releases/c4a8c543.../scripts/serve.sh
```

Before cutover:

- `PHASE=complete`
- profile `orcarouter`
- legacy image `vllm-skinny-tp1:v1`
- update/runtime/profile-switch transitions all idle
- service installed/enabled/active
- container running with `oom=false`

Baseline decode:

- workload: 384 tokens x5
- status: PASS
- median decode throughput: `34.3389 tok/s`
- managed KV: 16 GiB

## Qualification

The full DGX release qualification passed with the new executable-mode regression test:

```text
Ran 537 tests in 31.236s

OK
Release qualified for cutover: c4a8c543bc62add17a76048758032d9bf9a53af4
```

The manifest-bound update dry-run passed.

## Cutover observation

The target release pointer was activated and the replacement legacy OrcaRouter runtime
started with the intended pre-H38 controls:

```text
profile=orcarouter
PLE=cpu-offload
SPEC=mtp k=2
qsa_det_topk=0
qsa_exact_topk=0
maxlen=262144
util=0.85
```

The current monitor policy then observed high reclaimable available memory but very low
immediately-free non-CMA memory plus rapid swap consumption. Five consecutive protection
samples were recorded:

```text
16:05:29 protect=0/5 ... noncmafree=1226MiB swapgrowth=0MiB
16:05:32 protect=1/5 ... noncmafree=900MiB  swapgrowth=4741MiB
16:05:34 protect=2/5 ... noncmafree=900MiB  swapgrowth=8070MiB
16:05:37 protect=3/5 ... noncmafree=900MiB  swapgrowth=11490MiB
16:05:39 protect=4/5 ... noncmafree=899MiB  swapgrowth=15018MiB
16:05:42 protect=5/5 ... noncmafree=901MiB  swapgrowth=16377MiB
16:05:42 PROTECT stopping qwen38-flash-next gracefully to preserve host stability
```

The service runner recognized the protected stop, aborted the runtime transition, and the
release update rolled back. The previous release was then restarted and eventually returned
to the committed healthy state.

The target legacy runtime therefore never reached READY and the target release was not
committed.

## Strict RM boundary

The supplied attempt log contains no `NV_ERR_NO_MEMORY` or
`_memdescAllocInternal` text. That does **not** establish HOST-STABILITY PASS because
the canonical kernel window was not reached/collected by the outer Gate A script after
the protected-stop failure.

The protected stop is a real safety intervention and must not be silently ignored or
converted into a pass.

## Delta attribution

Repository comparison materially changes the interpretation of this failure.

Between PR base main `a7c563705edba780747bf815278f6b77c8a41b08` and attempt-04 head:

- `scripts/runtime/monitor-runtime.sh`: identical
- `scripts/runtime/service-runner.sh`: identical
- `scripts/manage-service.sh`: identical
- only `scripts/serve.sh` changes in this lifecycle surface

For a persisted legacy `VLLM_IMAGE=vllm-skinny-tp1:v1`, the H38 branch preserves the
base-main legacy controls. H38-only controls activate only when the image is exactly
`vllm-orcarouter-v029-h38-decoder-scope:v1`.

The installed old release `ff67bab...` predates the current monitor's
high-available/low-free + swap-growth protection rule. Therefore attempt 04 exposed a
compatibility boundary between the old installed release and already-existing base-main
monitor policy; the evidence does not attribute the protected stop to the H38 delta.

## Classification

- executable-mode remediation: PASS
- release qualification: PASS (537/537)
- update dry-run: PASS
- target legacy runtime start: REACHED
- target legacy READY: FAIL / protected stop
- immutable release commit: FAIL / rolled back
- H38 migration: NOT REACHED
- H38 determinism/performance/restart: NOT REACHED
- H38 HOST-STABILITY: NOT TESTED

Gate A remains blocked. This is not a managed-H38 functional or host-stability result.

## Next discriminator

Do not weaken or disable memory protection.

Run a matched immutable-update control using the exact PR base-main release
`a7c563705edba780747bf815278f6b77c8a41b08` with the same persisted legacy manifest and
the same monitor policy. The purpose is to determine whether the old-installed-release ->
base-main cutover reproduces the same protected stop.

- if base main reproduces it, the Gate A legacy restart criterion is baseline-blocked by a
  pre-existing lifecycle/monitor compatibility boundary and must be redesigned rather than
  blamed on H38;
- if base main reaches READY under matched conditions while the PR head does not, the H38
  branch still has a real legacy-compatibility regression that must be isolated.

No Gate B migration is authorized until this discriminator is recorded.
