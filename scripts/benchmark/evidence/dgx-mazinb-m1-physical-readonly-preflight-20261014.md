# ACTUAL DGX Spark — mazinb M1 physical read-only preflight (2026-10-14 KST)

## Source and scope

This is a **user-provided actual DGX terminal transcript**, observed through
the root `wizard.sh` at exact Git commit
`2dfa74dacedfe50fe1c28ca309939ed9d61b8123` on
`feature/wizard-modular-phase1-20261014` (Draft PR #261).

The operator safely fetched the Git ref, verified detached HEAD, and ran
`wizard.sh`. The installed manager reported:

- `Manifest: valid (phase=complete)`
- `Profile: orcarouter`
- `Image: vllm-skinny-tp1:v1`
- `Runtime: NOT_PROBED` — the manager did NOT assert a running service.

At **Wizard -> 5 Benchmark**:
- Option **6** returned `M1_PLAN=NEW_ISOLATED_MAZINB_16G`,
  `M1_PORT=127.0.0.1:18889`,
  `M1_WATCHDOG=ARM_EXACT_ID_BEFORE_START`,
  `M1_SESSION_MAX_SECONDS=5400`, `M1_KEEP_OLD_AB_AND_MANAGED=YES`,
  `M1_START=ONLY_INTERACTIVE_WIZARD_OPT_IN`,
  and `M1_BENCHMARK=NOT_MEASURED`.
- Option **7** returned `M1_SESSION=ABSENT`.
- Option **8** displayed the managed protected Docker ID and required exact
  64-character typed confirmation. The operator confirmed it and approved
  sudo credentials for read-only NVIDIA RM evidence access.

### Exact physical output

```text
M1_PROTECTED_PREDECESSOR_ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24
M1_PREFLIGHT=PASS_READ_ONLY
M1_OLD_DOCKER_ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24
M1_IMMUTABLE_RELEASE=/home/inlc/.local/share/qwen38-spark/releases/ff67bab3c94d6992f61b9535836df97f03b9c022
M1_IMAGE_ID=sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734
M1_CANDIDATE_START=NOT_PERFORMED
```

These image/release/container identities were the verified *read-only*
snapshot at the time of the run; re-check all identities at the start of
any later M1 session. The output contains no model-token throughput,
memory benchmark, runtime READY, exact live model JSON, or new M1 Docker ID.

## Interpretation and gates

**PASS:** M1 plan/status inspection and current-host read-only admission,
with the exact predecessor ID, current manifest/release, mazinb image,
checkpoint and filesystem/lifecycle/memory preflight evaluated by source.
This is meaningful ACTUAL_DGX evidence, **not** synthetic GitHub CI.

**NOT RUN:** New `docker create`, watchdog arming on a real new candidate,
`docker start`, API /health, strict /v1/models response,
180-second post-READY soak, actual inference smoke, strict live RM
window, any measured llama-benchy work, external benchmark backup.

**PRESERVATION:** The preflight path does not remove or restart the managed
OrcaRouter, delete or restart historical mazinb A/B Docker objects,
remove model checkpoints or clear raw evidence.

**Next source hardening before physical startup:** The new M1 controller
must use a unique per-candidate `HOME` to ensure vLLM and FlashInfer
cache mounts do not touch the user's previous experimental or canonical
cache directories. Re-run source CI and perform exact-SHA verification of
that hardening commit. Do not launch live M1 on the older preflight SHA.

**Do not infer guaranteed host stability from preflight success.** The
historical managed 16-GiB mazinb run had an NVIDIA
`NV_ERR_NO_MEMORY` event despite successfully reaching READY; the
new M1 physical strict RM gate remains mandatory.

## Second current-host read-only review — user transcript (2026-10-14 KST)

After the source-only per-trial cache isolation change at
`72982e0e1bb53cdf8bb66a641356eb4a7e743320`, the operator
submitted a second root Wizard 5 -> 8 output confirming again:

- `M1_PREFLIGHT=PASS_READ_ONLY`
- `M1_CANDIDATE_START=NOT_PERFORMED`
- protected predecessor ID `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
- identical release `ff67bab3c94d6992f61b9535836df97f03b9c022`
- identical image `sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734`

The operator subsequently opened historical evidence via 5 -> 5 and chose
0 (Back). This did **not** re-inspect or mutate either historical case.

**Provenance qualification:** This second pasted output did *not* include a
`git rev-parse HEAD` line. The operator had been given instructions to
switch to the hardening commit, but the text alone is not an independent
cryptographic confirmation that the second preflight ran that exact SHA.
Before authorizing a physical M1 load, recheck the live worktree HEAD
against the pinned runtime source SHA and ensure the worktree is clean.
No M1 Docker creation, API READY, inference smoke or benchmark is reported.

