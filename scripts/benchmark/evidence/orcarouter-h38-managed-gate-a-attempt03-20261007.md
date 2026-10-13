# OrcaRouter H38 managed-service Gate A attempt 03 — 2026-10-07

Status: CUTOVER BLOCKED — IMMUTABLE RELEASE LOST SERVE-HELPER EXECUTABLE MODE

## Provenance

- repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- branch under qualification: `feat/h38-managed-integration`
- attempted target: `46d429438df39d98fb4c40e33b17ac2b664dabbb`
- installed profile: `orcarouter`
- pre-H38 managed image: `vllm-skinny-tp1:v1`
- installed current release before the attempt: `ff67bab3c94d6992f61b9535836df97f03b9c022`

## Baseline result

The pre-H38 managed runtime was active, enabled, and not OOM-killed before the run.
All three lifecycle transaction guards were idle.

Baseline decode workload:

- mode: decode
- max tokens: 384
- repeats: 5
- status: PASS
- median decode throughput: `35.0773 tok/s`
- runtime image: `vllm-skinny-tp1:v1`
- managed KV cache: `17179869184` bytes
- served model: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`

## Qualification result

Attempt 03 is the first DGX Gate A run to pass the full release qualification suite:

```text
Ran 536 tests in 31.091s

OK
Release qualified for cutover: 46d429438df39d98fb4c40e33b17ac2b664dabbb
```

The manifest-bound dry-run also passed.

## Cutover failure

The real immutable release cutover was reached. After the current release pointer moved to the
qualified target, managed-service creation failed before target runtime startup:

```text
Current release pointer updated: 46d429438df39d98fb4c40e33b17ac2b664dabbb
Update release staged for runtime cutover: 46d429438df39d98fb4c40e33b17ac2b664dabbb
ERROR: runtime root has no serve helper: /home/inlc/.local/share/qwen38-spark/current
Release cutover failed; restoring previous release pointer and service.
Update release pointers rolled back.
```

The rollback path then restarted the previous managed runtime and eventually reported it
enabled, committed, and healthy. Because `update-release.sh` returned through its failure
rollback path, the outer Gate A script stopped before the post-cutover image/transaction
assertions.

## Root cause

The target Git tree stored `scripts/serve.sh` with mode `100644`.

`release-manager.sh stage` deliberately exports committed content using `git archive`, so the
immutable release correctly preserved that non-executable mode. `manage-service.sh` correctly
requires the serve helper to be executable, and the canonical service runner executes
`scripts/serve.sh` directly.

Therefore this was a repository file-mode defect that the immutable-release path exposed; it
was not a reason to weaken the managed-service safety check.

## Classification boundary

- release qualification: PASS
- manifest-bound update dry-run: PASS
- immutable code cutover: FAIL / rolled back
- target managed runtime startup: NOT REACHED
- legacy-to-H38 image migration: NOT REACHED
- managed H38 determinism/performance/restart/RM acceptance: NOT REACHED

No managed-H38 PASS or FAIL classification is asserted from this attempt.

## Remediation

- `5d5120ebc765db80aa2306f16432dca0c550abee`
  - changes the Git mode of `scripts/serve.sh` from `100644` to `100755`
  - does not weaken `manage-service.sh` executable validation
- `cf59eee698925eafdf4b7275fa985c28d64062e4`
  - adds a regression test asserting the immutable-release serve helper retains its executable bit

Gate A must be restarted from the exact new qualified head after CI passes.
Attempt 03 remains immutable failure evidence.
