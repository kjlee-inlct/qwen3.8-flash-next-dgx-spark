# Project mission — wizard-first install / uninstall / switch

**Primary product goal (P0):** Make checkpoint installation, removal/uninstall and switching easy and reliable for an operator on a single NVIDIA DGX Spark, principally through the interactive **terminal wizard** `./install.sh` and `./uninstall.sh`. The wizard is not a GUI application. The intended everyday user workflow must not require manually stitching together a long sequence of Docker, vLLM and systemd commands.

A working GPU runtime, memory protection, NVIDIA RM analysis, lifecycle state files, deterministic H38 candidate and benchmark/evidence infrastructure are **supporting engineering constraints**, not replacement top-level product goals. Continue safe wizard engineering when the separate H38 rollout remains blocked.

## The original four model targets — plus one added later

| Timeline | Wizard key | Exact repository / checkpoint identity | Registry status |
|---|---|---|---|
| Original 1 | `orcarouter` | `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` | Stable default; installable |
| Original 2 | `nvidia` | `nvidia/Qwen3.8-Flash-Next-NVFP4` | Experimental; installable |
| Original 3 | `mazinb` | `mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4` | Experimental; installable |
| Original 4 | `lychee888` | `lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE` | Planned; **not installable** |
| Added later | `orcarouter-hybrid` | `local/orcarouter-mazinb-h6-w4a16` (OrcaRouter + mazinb experts, W4A16 NVFP4) | Experimental; installable |

**Counts:** **4 original + 1 later-added Hybrid = 5 tracked families**. **3/4 original installable** and **4/5 total installable** according to the current registry. Do not rewrite history as four original models including Hybrid; do not claim all four originals are complete while lychee888 is planned. The Hybrid H3/H4/H5 build artifacts are prerequisites/intermediate stages, not additional user-selectable checkpoint families. **H38 is a candidate runtime implementation of the existing OrcaRouter profile, not a sixth wizard model.** Backend `vllm` (implemented) versus `sglang` (planned) is a separate axis.

Registry truth: [model-profiles.sh](../scripts/model/model-profiles.sh), exposed by `./install.sh --list-models`. “Installable” means an implementation path exists, not completed live or host-stable E2E validation.

## P0 operator journeys

### 1. Initial install — `./install.sh`

- An interactive Korean/English operator flow should select supported checkpoint, storage location, runtime/backend, resource policy, access/service options, then **review before applying**.
- Clearly show both selectable models and why planned `lychee888` is not yet selectable; display Hybrid parent/dependency and additional build/storage requirements.
- Use pinned model artifacts, record ownership, protect existing data, and support meaningful failure and resumed/retried work.
- A full real success needs completed checkpoint/image, sound manifest, owned release/service, `/health`, expected `/v1/models` and verified runtime stability. A wizard success message or synthetic CI alone is not enough.

### 2. Existing install and profile switch — `./install.sh`

- Detect the currently installed profile; offer another supported profile and settings changes through the wizard, with before/after preview and confirmation.
- Reuse existing checkpoint/images where qualified; track cumulative asset ownership and preserve other models, Hybrid parents and unrelated Docker assets.
- Stage/update transaction and ensure failure can be explained and recovered, distinguishing actual functional readiness, strict NVIDIA RM host stability, and intentionally protected-stop behavior.
- On older installed releases, successful managed replacement **may delete the previous Docker container ID**, and ordinary rollback may restart an intentionally stopped predecessor: do not imply exact-ID preservation or execute blind restarts to make a test pass.
- Test all allowed directional model pairs in disposable fixture/safe live contexts separately. Experimental selectable is not live-qualified.

### 3. Guided uninstall / optional purge — `./uninstall.sh`

- Bilingual wizard previews precisely which managed resources remain/are removed. Default removal must preserve unmanaged and user-owned checkpoints/images/files.
- Selected/full purge requires explicit consent and ownership/dependency preflight; cancellation and failure must not create a fake successful completed state.
- Preserve recovery evidence, do not erase unrelated resources, and never treat `--dry-run` as proof real purge is safe. Real destructive M2/D1–D5 acceptance requires **independent disposable-host authorization**, not merely that the operator is sole user of the DGX.

### 4. Maintainable extension to the remaining original model

- Implement missing original `lychee888` via the existing model registry + downloader/preparation + backend/runtime adapter + wizard tests. It should remain disabled until verified installability.
- Keep install, update, switch, uninstall and recovery entry points consistent across supported model families; do not duplicate one custom script stack per model.
- The primary completion criterion is an operator who can finish ordinary installed-model tasks through the wizard rather than bespoke manual intervention.

## Priority and acceptance hierarchy

1. **P0:** Finish initial-install, existing-install/switch, uninstall and cancellation/preview/error UX; maintain truthful selection for the original four and added Hybrid. Implement original remaining `lychee888` through the safe staged model path.
2. **P1:** Demonstrate correctness through source/static, synthetic isolated-fixture tests, then properly bounded actual system tests with separate functional and strict RM host-stability evidence.
3. **Safety gates:** immutable release identity, ownership and rollback semantics, monitor protection, and independent disposable-host requirement for destructive E2E. Do not relax safety merely to advance the wizard.
4. **Independent blocked track:** H38/M4 rollout and metadata/RM qualification. These block an unsafe live path, **not all wizard work**.

Current bounds: actual DGX B4 is a collected stopped-runtime read-only prestart, **not M1 LIVE PASS**; M2 destructive live E2E not run; M3 live all-pairs unqualified; M4 H38 blocked; D0 independent disposable admission not granted; PR #259 Draft/Open/Unmerged. The current state may change: always re-read [CURRENT-STATUS.md](CURRENT-STATUS.md), [MANAGED-LIFECYCLE-ACCEPTANCE.md](MANAGED-LIFECYCLE-ACCEPTANCE.md), [OPERATIONS.md](../OPERATIONS.md) and [dated evidence](../scripts/benchmark/evidence/README.md).

**New-session instruction:** Begin with this mission and scope. Then inspect recent operator state/CI/PR and pick the next **highest-value safe wizard deliverable**, not the deepest unresolved GPU experiment by default.

## Wizard consent and closed-input safety regression (2026-10-13)

The shared terminal wizard previously treated an exhausted input stream (EOF)
like an empty Enter under callers that suppressed Bash `errexit`. That could
select a default-`yes` confirmation or flow through an AND/OR fallback to
turn off a default-enabled memory protection option. The updated shared
wizard reader **terminates the wizard (exit code 2)** if reading a full
newline-terminated answer fails, in both terminal and non-TTY modes.
A **real newline-terminated empty answer** continues to select the documented
default, and explicit `yes`/`no` remains supported. `wizard_input`,
`wizard_secret` and `wizard_yes_no` share the fail-closed behavior.

Regression tests exercise EOF in a conditional, an AND/OR safety setting,
a defaulted text input, a secret input, and an unterminated consent answer.
This is **source/CI fixture acceptance only**: it does not constitute a
physical DGX install, uninstall or GPU startup test.
