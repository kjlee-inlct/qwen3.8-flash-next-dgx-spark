## 2026-10-16 — Actual Hybrid research retirement supersedes previous pending plan

The owner **completed** the exact-17 stopped research Docker retirement and
the subsequent exact H3/H4/H5/H6 local checkpoint deletion on the single DGX
Spark. Independent host checks confirmed all four directories absent,
the original OrcaRouter checkpoint present, and the private archived evidence
checksum valid. The model phase recovered a measured 145,637,814,272 bytes
of available filesystem space; details and ID-level evidence:
[Hybrid local retirement evidence](../scripts/benchmark/evidence/dgx-hybrid-local-retirement-scope-20261015.md).
Earlier sections in this document discussing an undecided Hybrid retirement
are **historical as of 2026-10-15**, not the current operator decision.
The original `orcarouter-hybrid` profile must not be advertised as a
ready installed/qualified local model after retirement. Preserve its
historical registry and experiment provenance, but do not reinterpret old
failed/stopped H6 tests as a successful inference/benchmark.

The active direction is to finalize a small modular Wizard status/cleanup
guide and **move on promptly to research the lychee888 FP8-PLE and
catplusplus mixed-NVFP4 candidates**, initially read-only and without GPU
start or large downloads.


# Project mission — wizard-first install / uninstall / switch

**Primary product goal (P0):** Make checkpoint installation, removal/uninstall and switching easy and reliable for an operator on a single NVIDIA DGX Spark, principally through the interactive **terminal wizard** `./install.sh` and `./uninstall.sh`. The wizard is not a GUI application. The intended everyday user workflow must not require manually stitching together a long sequence of Docker, vLLM and systemd commands.

A working GPU runtime, memory protection, NVIDIA RM analysis, lifecycle state files, deterministic H38 candidate and benchmark/evidence infrastructure are **supporting engineering constraints**, not replacement top-level product goals. Continue safe wizard engineering when the separate H38 rollout remains blocked.

## Active development policy — 2026-10-15

The operator explicitly **deferred finishing the Wizard around mazinb first**. Instead, validate multiple candidate checkpoints and improve shared installation, switching, monitoring, benchmarking, and removal Wizard flows incrementally as each model reveals requirements. This defers a mazinb-centered completion milestone, **not** the original wizard-first product mission. Do not treat any candidate as installable, GPU-ready, or benchmarked merely because it is listed here.

Additional research candidate: `catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed` (proposed key `catplusplus`, **research-only; no registry support claimed**). The originally planned `lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE` also remains a priority for compatibility and single-Spark feasibility research. Compare checkpoint tensor/config inventory and serving requirements before selecting trial order. Keep `mazinb` as an actual-DGX READY/benchmark reference, not a prerequisite for completing the whole Wizard.

Hybrid H6: first perform read-only static analysis of double checkpoint loading and memory behavior; make an explicit keep/retire decision. Do not retry GPU loading, weaken protection, delete H3–H6 or dependent H7/H20 assets, or change managed services without a separate gated approval. Retiring a profile means removing future exposure safely, not erasing immutable evidence or historical Git records.

## The original four model targets — later additions and candidates

| Timeline | Wizard key | Exact repository / checkpoint identity | Registry status |
|---|---|---|---|
| Original 1 | `orcarouter` | `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` | Stable default; installable |
| Original 2 | `nvidia` | `nvidia/Qwen3.8-Flash-Next-NVFP4` | Experimental; installable |
| Original 3 | `mazinb` | `mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4` | Experimental; installable |
| Original 4 | `lychee888` | `lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE` | Planned; **not installable** |
| Added later | `orcarouter-hybrid` | `local/orcarouter-mazinb-h6-w4a16` (OrcaRouter + mazinb experts, W4A16 NVFP4) | **Retired 2026-10-16; not installable; historical only** |
| Proposed candidate | `catplusplus` (proposed) | `catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed` | Research only; not in registry |

**Counts:** **4 original + 1 later-added Hybrid = 5 historical registry families**, plus 1 proposed research candidate not yet registered. **3/4 original installable** and **3/5 total installable** now that Hybrid has been retired. Do not rewrite history as four original models including Hybrid; do not claim all four originals are complete while lychee888 is planned. The Hybrid H3/H4/H5 build artifacts are prerequisites/intermediate stages, not additional user-selectable checkpoint families. **H38 is a candidate runtime implementation of the existing OrcaRouter profile, not a sixth wizard model.** Backend `vllm` (implemented) versus `sglang` (planned) is a separate axis.

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

**New-session instruction:** Begin with this mission and scope, then the latest status and compact handoff. Prioritize multi-model feasibility/validation and incremental reusable Wizard improvements; do not insist on mazinb-first Wizard completion.

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

## P0 model picker retry and explicit cancel (2026-10-13)

The interactive profile selector now has a **Cancel** item for fresh installs
as well as existing-install model switches. An invalid numeric choice or
unknown profile key produces a bilingual warning and re-prompts in the
**same wizard** instead of throwing the operator back to the shell.
The originally selected profile remains unchanged until a recognized
entry is chosen. Both explicit cancel and the shared reader's EOF
handling exit before any model/runtime actions. Current model order and
the `lychee888` non-installable candidate display remain registry-owned.

Host-free integration tests cover recovery from an incorrect number,
selecting a valid replacement afterwards, and cancelling a fresh/existing
wizard with the existing manifest unchanged. This does not change actual
DGX running service state or prove real live switching readiness.

Original fourth-model implementation gates: [lychee888 FP8-PLE roadmap](LYCHEE888-WIZARD-INTEGRATION.md). This is a source/research plan, not installed/live support.
