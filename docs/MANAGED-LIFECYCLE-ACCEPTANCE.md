# Managed installer, uninstaller, and model-switch acceptance

## OrcaRouter A/B trial wizard implementation — SOURCE ONLY (2026-10-13)

**Progress since A/B preview:** A separate, experimental installed-setup
**menu 6** now offers **status / start Legacy / start v0.29 / stop**,
plus a plan-only response under `./install.sh --dry-run`.
A fresh DGX Spark OS with working NVIDIA driver/Docker/Git/Python/curl/sudo
still uses `./install.sh` to select v0.29 (default) or press
`L` (Legacy), automatically download pinned checkpoint and
locally build the selected runtime image if absent. These are
distinct workflows: neither is a pretext to change the existing
managed manifest, immutable release or stopped predecessor.

The A/B trial is **source-implemented but NOT ACTUAL_DGX
qualified**. Safety boundary: interactive choice and explicit
old Docker ID confirmation; shared lifecycle lock; complete
OrcaRouter manifest; service inactive; no conflicting lifecycle
transaction; protected predecessor exact 64-character ID,
`exited`, non-OOM and unchanged; original release and manifest
SHA retained; present pinned checkpoint/config/image; swap and
non-CMA memory margins; exclusive localhost trial API 18888.

Launch uses a new `qwen38-ab-legacy` or `qwen38-ab-v029`
container with immutable predecessor/variant labels, initially
**docker create, not start**; a separately persisted state
watchdog must be **armed to that exact Docker ID** before the
trial can be started. The watchdog uses its own stop journal and
non-CMA/swap monitoring. Failure/stop targets only the exact new
trial ID; Docker container/logs are preserved for evidence.
After stopping A, B can start only if A is cleanly stopped with
proper provenance. Neither trial changes installed image,
manifest, service, old Docker object or release pointer.
Ref: [isolated trial source runbook](DGX-ORCAROUTER-AB-ISOLATED-TRIAL.md).

**Crucial:** A successful GitHub Python/ShellCheck CI tests
source and synthetic mocks, NOT actual GPU load, model READY,
NVIDIA RM correctness, stability or benchmark. No actual
model start, pause or deletion has been performed in this chat.
The host's earlier read-only OrcaRouter wizard dry-run remains
the only verified physical wizard event. A/B results,
raw llama-benchy JSON/Markdown/SHA256 and off-host backup
remain **NOT_MEASURED/NOT_CAPTURED**. Before live use,
conduct an owner-approved exact-SHA read-only menu 6 preview,
check all host prerequisites and watchdog behavior; any
physical launch is a separate explicit operator decision.
OrcaRouter deletion HOLD applies **only during this test**,
not permanently. PR #259 remains Draft/Open/Unmerged.


## OrcaRouter legacy / v0.29 A/B wizard plan staged (2026-10-13)

**Owner's new choice:** do not decide the final runtime image from source inspection alone. Benchmark **both** `vllm-skinny-tp1:v1` (legacy CPU-offload) and `vllm-orcarouter-v029:v1` (official vLLM v0.29 + PLE mmap/GB10 FLA/exact QSA) **sequentially** on the same OrcaRouter checkpoint/revision and a **16 GiB KV cache** starting point. These represent whole-runtime differences, not an image-only isolation. Measure actual load/READY, TTFT/TTFR, PP/TG, concurrency, failure rate and strict NVIDIA RM/non-CMA/swap stability with the same pinned `llama-benchy` workload, separate cold/warm repeats and preserved JSON/Markdown/SHA256/off-host backup. Prefer a stable image only **after** real qualification; both reports are NOT_MEASURED.

**Source implementation** at `394805e62999186afd56d085f279d87f4e4742af` (GitHub workflow pending at the time of documentation): A *newly provisioned DGX Spark OS with functional NVIDIA GPU/Docker* can use `./install.sh` to choose OrcaRouter baseline **v0.29** (provisional new-install default), or press **L** for Legacy; image builds locally if absent and the wizard handles pinned checkpoint download, compatible config, 128 GiB PLE swap, immutable release/service, monitor/protect (fresh OrcaRouter defaults enabled). The normalized equivalent CLI `--orcarouter-runtime legacy` reproduces L, only on fresh OrcaRouter installations. Missing OS/GPU driver/Docker/network prerequisites are **not** silently installed. Full real empty-host online installation has NOT_RUN.

**Existing protected DGX:** `./install.sh` → management menu **5** is a **read-only A/B plan preview**; **4 still cancels**. The installed legacy `vllm-skinny-tp1:v1` manifest/release and historical stopped Docker exact ID are never silently migrated or removed. The preview explicitly prints `WIZARD_ISOLATED_START=NOT_IMPLEMENTED`, no live API or RM acceptance, no benchmark. Actual dual-image isolated wizard launch/stop and exact-ID host safety is **NOT IMPLEMENTED**; never use direct experiment start or `systemctl restart` as a bypass. H38 is separately gated, not the fresh default. See [A/B comparison protocol](DGX-ORCAROUTER-AB-BENCHMARK.md) and [isolated trial design](DGX-ORCAROUTER-WIZARD-TRIAL-DESIGN.md). OrcaRouter checkpoint deletion is held **only for this test**; later review requires explicit approval and benchmark backups. PR #259 stays Draft/Open/Unmerged.


## Actual DGX OrcaRouter existing-install interactive wizard DRY-RUN PASS (2026-10-13)

At exact source `a61b4569c5a6865dbeb9aa4ba4b21aeea12424e2`, operator entered existing wizard manager, selected OrcaRouter and accepted `--dry-run` plan; **RC=0**, original Docker `Id|Status|Image` and `install.env` SHA256 identical before/after. [Original physical output evidence](../scripts/benchmark/evidence/dgx-orcarouter-wizard-actual-dry-run-20261013.md). Plan: OrcaRouter checkpoint revision pinned, installed legacy image `vllm-skinny-tp1:v1`, enabled monitor+protection, PLE swap=128 GiB, managed systemd/remote API configured. This is not a running/healthy API, model validation or wizard live acceptance. Next P0 needed: [wizard-contained isolated trial](DGX-ORCAROUTER-WIZARD-TRIAL-DESIGN.md) to preserve exact old stopped Docker object despite legacy transition commit/delete; monitor isolation and exact-ID abort. No live start/cleanup authorized. Bench 5/5 NOT_MEASURED.


## Owner clarification: OrcaRouter first, deletion freeze scoped to this test (2026-10-13)

OrcaRouter is the initial wizard-selected performance target and
must be preserved **during this test and until evidence is safely
stored**; it is NOT permanently ineligible for future deletion.
The temporary absolute ban and associated source-level
`ORCAROUTER_PROTECTED` checks were an overinterpretation and
have been withdrawn. No current model/Docker deletion is allowed.
Later cleanup can include OrcaRouter as an **owner-approved**
candidate only after actual benchmark + archived proof (or an
explicit approved exception), dependencies, storage ownership,
exact Docker identity/recovery review and wizard plan.

Managed default uninstall can remove the old canonical Docker
object even without purging a model; M1 live requires a reviewed
identity-preserving wizard route. Actual v0.29 OrcaRouter read-only
preflight RC=0, checkpoint/image ready; API still stopped.
No live wizard E2E, benchmark, M1/RM stability acceptance yet;
five report templates remain NOT_MEASURED. Two-terminal
management-vs-benchmark isolation remains required.

## Owner P0 workflow update: all model lifecycle via wizard, bench in second terminal (2026-10-13)

[Two-terminal wizard/benchmark operating specification](DGX-TWO-TERMINAL-WIZARD-BENCHMARK.md):
Terminal A for interactive installer/profile switch/uninstaller and
read-only storage plans, Terminal B for benchmark-only workloads on an
already wizard-activated, health/model-verified and host-qualified API.
No A mutating operation while B is benchmarking; the existing wizard
flock does NOT alone serialize upstream llama-benchy.
Uninstall actually removes the managed canonical Docker object;
switch can delete a stopped predecessor on successful commit.
Therefore current owner protected-ID rule blocks actual mutation
until a reviewed isolation/rollback design and explicit approval.
The wizard currently does not expose every individual inactive
H3/H4 asset-retirement action; do not use low-level direct deletion
as an implicit fallback. The product acceptance must cover wizard
selection/install/switch/cleanup preview/realistic guarded teardown
and exclusion of concurrent benchmark work.

ACTUAL_DGX v0.29 OrcaRouter **read-only preflight** RC=0
([dated evidence](../scripts/benchmark/evidence/dgx-orcarouter-m1-isolated-preflight-20261013.md)):
image/checkpoint ready, port 8888 free, old Docker identity preserved;
MODEL_START=NOT_PERFORMED. M1/M3 full live acceptance NOT_QUALIFIED,
5/5 benchmark reports NOT_MEASURED; no deletion authorized.


## S4 actual DGX Hybrid links PASS; M1 live and wizard E2E not qualified (2026-10-13)

[Physical S4 read-only scope](../scripts/benchmark/evidence/dgx-hybrid-all-link-closure-readonly-20261013.md)
resolved all 319 Hybrid symlinks through known aliases, source-mount
contract STATIC_PASS, `ALL_LINK_REFERENCE_GAPS=0`, ext4, snapshot
available 112103874560 bytes. **Actual Docker mounts/model start,
M1 live host-stability, M3 pairwise switch, destructive M2/D0,
and wizard full E2E remain NOT_QUALIFIED/NOT_RUN as before**. The
protected stopped Docker predecessor/immutable release cannot be
trivially replaced by the managed service in order to run benchmark.
Benchmarks remain 5/5 NOT_MEASURED, deletion NOT_AUTHORIZED. The
P0 bilingual terminal wizard stays the product priority.


**Status: implementation and simulation substantially complete; full live E2E NOT QUALIFIED.**

This is the current-facing acceptance checklist for the Qwen3.8 Flash Next single-DGX-Spark managed lifecycle. It separates **implemented**, **CI/synthetic**, **historical operator functional**, and **new live end-to-end** proof. An installable model profile is not automatically host-stable. Use `docs/CURRENT-STATUS.md` and `scripts/benchmark/evidence/README.md` as the authority for exact historical gate outcomes; dated source records are not automatically production approval.

## Actual physical DGX B5 read-only result and future model benchmark (2026-10-13)

B5 physical host result: **15/15 read-only guards PASS**,
`B5_READONLY=COLLECTED_READ_ONLY`, source `c2a7317`,
immutable `ff67bab3`, exact old Docker ID unchanged, inactive
runtime, protections/swap retained.
[Scoped evidence](../scripts/benchmark/evidence/dgx-b5-legacy-orcarouter-prestart-readonly-20261013.md).
M1 remains NOT_QUALIFIED; explicit exact container-object ID
decision and failure/rollback plan are required.
Benchmark report templates for all five tracked profiles use
`NOT_MEASURED` until actual validated
[llama-benchy protocol](model-reports/README.md) is run against a
separately qualified healthy API. No metric inferred from B5.

## B5 legacy OrcaRouter exact-identity prestart (2026-10-13)

A newly committed [source-only B5 runner](DGX-LEGACY-M1-B5-PRESTART.md)
can be executed on the actual DGX without changing service/container:
exact release `ff67bab3`, stopped predecessor
`f6bfee5a4217...`, monitor/protect, state, and memory/swap
snapshot. The old managed commit may **delete** the prior
Docker object; rollback may **restart** it. B5 success can
establish only read-only observations; live M1 still requires
explicit container-ID decision and fully reviewed stop plan.
B5 actual output NOT_RUN at this point.

## Actual DGX A5+lychee888 L0 result (2026-10-13)

The operator ran A5 from the verified exact source
`f2674f0`, obtaining **14/14 read-only commands rc0**
and 60/60 fixture tests, unchanged manifest/ownership SHA256,
unchanged immutable `current`, and
`WIZARD_DGX_READONLY=PREVIEW_AND_FIXTURES_PASS`.
`A5_REAL_DGX_DRY_RUN=PASS`. Immediately afterward an
actual remote-Hub L0 JSON call for `lychee888` returned pinned
revision `1b3c3cedc14fb3bee4294dea5e3515af74b8268a`
and `INDEX_STRUCTURE_PASS_METADATA_ONLY`.
[Scoped result](../scripts/benchmark/evidence/dgx-a5-wizard-and-lychee-l0-result-20261013.md).
These do NOT count as actual installed-model start, live
switching, destructive uninstallation, single-Spark FP8
loader verification or strict host-stability. M1/M2/M3/M4/D0
qualifications remain unchanged.

## Physical-DGX wizard A5 — now operator-ready, not yet observed (2026-10-13)

[Explicit bounded A5 runbook](DGX-WIZARD-A5-READONLY.md) uses an
exact-SHA source worktree, true installed manifest/ownership state,
read-only model inventory, four install/switch target `--dry-run`
previews and two uninstall `--dry-run` previews. It checks
manifest/asset registry/current-link fingerprints before and after.
A successful actual-host log is `ACTUAL_DGX_DRY_RUN_PASS`, **not**
M1 live READY, real M2 destructive uninstall, M3 actual managed
switch, H38/M4, or D0 independence. No actual new A5 host log yet.

## Shared wizard EOF cancellation guard (2026-10-13)

The interactive installer uses a shared reader for yes/no, text and secret
prompts. The previous reader could misclassify EOF as blank input in
conditional/AND-OR callers, selecting default-yes confirmation or a
safety-setting fallback. The reader now **exits 2 on EOF**, preserving the
separate semantics of an actual empty Enter, and adds regression tests in
`tests/test_wizard_ui.py`. This is a host-free wizard correctness fix,
**not** fresh-install, model-switch or actual deletion E2E acceptance.

## P0 wizard objective and original target model scope

The original target is **easy installation, removal and profile switching
through the interactive terminal wizard**.
Read the [project mission, original four models and added Hybrid](PROJECT-MISSION-AND-MODEL-SCOPE.md)
before interpreting lifecycle milestones. Originally approved:
`orcarouter`, `nvidia`, `mazinb`, `lychee888`.
Later addition: `orcarouter-hybrid` H6. The registry has 3/4
originally planned families installable, plus experimental Hybrid,
while `lychee888` remains planned/non-installable. H38/M4 is a
runtime rollout gate of OrcaRouter, not a sixth model.

A P0 PASS requires successful actual wizard journeys (fresh install,
existing installation/model switch, uninstall with previews, cancellation,
ownership protection and recovery) within qualified environments.
Passing mock/synthetic fixture tests alone or proving model runtimes
does not mean the product wizard has passed real installation/switch/
uninstall E2E. Safe wizard work is not blocked by H38 investigations;
real destructive operations remain gated to independently disposable
systems and risky live model startup remains separately gated.

## Current qualification matrix

| Area | Implemented | Evidence available | Outstanding acceptance / classification |
|---|---|---|---|
| Fresh install wizard (ko/en, six steps, registry, model roots, runtime/API/service review) | YES | `tests/test_model_profiles.py`, `tests/test_installer_option_parity.py`, `tests/test_installer_plan_parity.py`, `tests/test_wizard_ui.py` synthetic/dry-run | Truly empty-host selected-model download/build→supported backend→service READY→doctor→restart NOT QUALIFIED; H38 candidate separately blocked |
| Existing-install wizard (active model, switch preview, settings/default refresh, resume) | YES | `tests/test_installer_profile_manager.py`, `tests/test_settings_transition.py`, `tests/test_model_profiles.py` synthetic preview/transaction | Full live supported-profile × configuration matrix NOT QUALIFIED |
| Uninstall bilingual preview (normal, selected purge, all purge) | YES | `tests/test_uninstall_wizard_preview.py` runs real `uninstall.sh --dry-run` against disposable manifests; no live resources touched | Actual destructive default uninstall, preserve/reinstall, selected/full purge in disposable realistic host NOT QUALIFIED |
| Asset ownership and dependent model safety | YES | `tests/test_asset_ownership.py`, `tests/test_lifecycle_integration.py` — ownership/fingerprint, unowned-dependent refusal, Hybrid H6→parent order | All combinations with imported older manifests/external containers during actual deletion NOT QUALIFIED |
| Profile-switch transaction/recover/rollback and operation lock | YES | `tests/test_profile_switch_transition.py`, `tests/test_operation_lock.py`, `tests/test_model_profiles.py` — synthetic crash boundaries and fail-closed invariants | Complete actual profile pairwise matrix and power-interruption recovery NOT QUALIFIED |
| Atomic cross-release same-profile image refresh | YES, candidate | `tests/test_release_profile_refresh_transition.py` and documented actual H38 guarded candidate startup/rollback | H38 managed service acceptance **BLOCKED** until model and strict host-stability gates clear |
| Hybrid H6 → OrcaRouter → Hybrid H6 | YES | Historical managed round-trip: **FUNCTIONAL PASS** | Strict **HOST-STABILITY FAIL** when NVIDIA RM failure present; not production-ready |
| mazinb managed activation | YES | Historical managed readiness/functional operation | **HOST-STABILITY FAIL**, repeated full lifecycle and correctness/performance missing |
| NVIDIA managed profile | YES (experimental) | Registry/dry-run and comparison path | Complete managed live switch/strict host-stability matrix NOT QUALIFIED |
| OrcaRouter H38 managed profile | YES (candidate) | Static CI, exact-image source-only and checkpoint index-only gates, guarded migration rollback | `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`; **GPU/MODEL RERUN BLOCKED** |
| `lychee888` | NO | Visible registry status = planned/non-installable | Not selectable; no production promise |

### Non-negotiable separation of result classes

1. **`CI_PASS`** means the code and disposable-fixture tests passed. It does not imply live DGX E2E pass.
2. **`DRY_RUN_PASS`** means a proposed installer/uninstaller plan/preview executes without applying it. The uninstall preview exits before the destructive path's operation lock and transition checks; it must **not** be used as proof the real action would succeed.
3. **`FUNCTIONAL_PASS`** means the specified historical model/transaction function passed during that run. It does not imply host stability.
4. **`HOST_STABILITY_PASS`** requires a strict monitored window and no recorded NVIDIA RM `NV_ERR_NO_MEMORY`. READY / monitor rollback alone is never proof of host stability.
5. **`PRODUCTION_READY`** requires the particular profile's clean-host, runtime, rollback, maintenance, and stability gates; no such blanket claim is made here.

## Milestones, acceptance ownership, and stop criteria

### M1 — Release-safe, non-destructive lifecycle coverage (do now)

- Keep `install.sh` and `uninstall.sh` wizard tests on **disposable synthetic `HOME`/`XDG_STATE_HOME`/`XDG_DATA_HOME`** fixture roots in CI; never run real `--purge-all` on the active DGX.
- Confirm Korean/English full uninstall dry-run, normal preserve, explicit purge flags, and cumulative purge preview leave model, release, and install manifest bytes untouched. Use the output of `tests/test_uninstall_wizard_preview.py` as a synthetic-only gate.
- Confirm tests for selector inventory; completed-install settings, profile default refresh, cancel/resume, wizard/CLI plan parity, ownership protection, transitions/locks, and rollback.
- For DGX operator read-only status only, run the exact-SHA guarded `scripts/lifecycle/inspect-readonly-lifecycle.sh` with `QWEN38_LIFECYCLE_AUDIT_TARGET_SHA` set to the CI-qualified checkout. It invokes **only** `install.sh --list-models`, `install.sh --list-backends`, four transaction `status` commands and `scripts/doctor.sh`. It performs no download, installation, uninstall, profile switch, service action or GPU/model launch. Its `COLLECTED_READ_ONLY` means only that inventory/status collection succeeded; **not** a complete live E2E or host-stability PASS. A `PARTIAL_CHECK_FAILURE` requires reviewing the captured per-command exit codes and details, not coercing the host.
- Milestone may become **`M1_SIMULATED_PASS`** after qualifying CI and a read-only DGX inventory/status snapshot. Without that snapshot, classify only **`M1_CI_ONLY`**.

### M2 — Rehearse destructive lifecycle safely (dedicated disposable host only)

Use an independent clean host or disposable VM compatible with the installer to run: clean install→health/model identity→stop/restart→normal uninstall with model retained→reinstall using retained model→targeted purge→ownership-dependent full purge. Capture before/after manifests, release pointers, recorded resource fingerprints, protected user files, exit codes and explicit deletion lists. The single production DGX Spark must **never** be used as the disposable host.

**No host/machine is currently qualified as a disposable environment**, so M2 = NOT RUN. Mock tests alone do not close it.

### M3 — Managed profile switch acceptance (only safe/qualified profiles)

Exercise every allowed pair and crash boundary with reversible controls and stable-host metrics, without deleting model assets. Existing Hybrid↔OrcaRouter historical functional proof is **not** an all-pairs matrix. Reject live attempts involving unsafe H38, and separately flag mazinb/Hybrid strict RM failures. In case of ambiguous rollback state, **fail closed, preserve manifests/attestation, stop** rather than guessing.

M3 = PARTIAL HISTORICAL EVIDENCE / NO ALL-PAIR QUALIFICATION.

### M4 — H38 managed rollout (blocked independent workstream)

The recent actual fixed-image checks establish CT eight-parameter source registration, input-scale postload consumer and possible counted-numel target inclusion, and a complete 221,184-name checkpoint index key grid. They do **not** prove actual initialized input-global-scale values, loader callbacks, unique destination writes, counted-numel correctness or shard buffer lifetime. The strict metadata order gate remains FAIL.

No H38 model/GPU launch, image rebuild, checkpoint tensor payload scan, managed service mutation, host-protection relaxation, CT meta patch, PR Ready or Merge until a separate qualified safety/production acceptance gate permits it. This blocker does **not** prevent M1 synthetic/live-read-only lifecycle validation.

## Go/no-go for this phase

The objective is **operator-lifecycle correctness**, not indefinite H38 loader archaeology. Close the present lifecycle phase when the independent M1 synthetic gate passes, operator read-only state/inventory is attached as evidence, and all remaining M2/M3/M4 live or destructive actions are clearly marked **NOT QUALIFIED/BLOCKED**. Do not label the full installer/uninstaller/model-switch product complete on M1 alone.

See `OPERATIONS.md` for supported commands, `docs/CURRENT-STATUS.md` for H38/RM safety, and `scripts/benchmark/evidence/README.md` for immutable dated observations.

## M1 actual DGX inventory/status snapshot — PARTIAL, do not call healthy (2026-10-12)

**Actual operator execution** at pinned clean HEAD `bbeceaf16c0c4bba4385c38cfead32e5dc243769` collected all seven non-mutating inventory/status/Doctor commands. Model inventory (active OrcaRouter, installed mazinb and Hybrid H6, absent NVIDIA, non-installable lychee888) and backend registry `rc=0`; all **four lifecycle transitions idle**, each `rc=0`. But Doctor `rc=1`: **5 FAIL** (runtime commit attestation missing/unsafe, exited container, no published API port, missing memory-protection monitor PID file, dead health endpoint) and **2 WARN** (legacy runtime image, inactive systemd service). Overall `MANAGED_LIFECYCLE_READONLY=PARTIAL_CHECK_FAILURE`, `lifecycle_audit_rc=3`; **M1 LIVE HOST HEALTH = NOT QUALIFIED**, even though 748 CI tests passed.

[Actual DGX evidence](../scripts/benchmark/evidence/managed-lifecycle-readonly-attempt01-doctor-partial-20261012.md) preserves the state and strict blockers without claiming independent causes. Doctor observed verified immutable current+previous releases, ownership, model 18-shard checkpoint, installed API sockets, healthy point-in-time memory/swap/disk margins, and valid model/container manifest identity. No actual model ran. In particular, Docker `docker port` on the **exited** runtime reported no published port; a wrong port binding is **not established**. Missing monitor PID or runtime-commit attestation is not permission to alter or regenerate them.

**New M1.1 safe offline follow-up**: `scripts/lifecycle/inspect-readonly-runtime-offline.sh` needs an exact clean checked-out SHA and reads only Docker container state/exit/OOM flags/declared port binding, systemd service result and existence/type/mtime of `runtime-commit.env`, `runtime-stop.env`, `monitor.pid`. No service start/restart, cleanup, model/GPU execution, checkpoint loading, or host protection edits; `COLLECTED_READ_ONLY` qualifies **data collection only**. Source guard: `tests/test_managed_runtime_offline_readonly.py`. The next operator evidence must distinguish intentional stopped state from service/runtime failure where feasible; absent logs or ambiguous states remain UNKNOWN.

Until this follow-up resolves the cause and separate live acceptance exists, **do not promote M1 to fully healthy or declare installation, uninstallation, and model switching completely validated**. M2 destructive E2E requires an isolated disposable host. M3 profile all-pairs are unqualified; M4 H38 model is still BLOCKED; the strict RM stability outcome cannot be inferred from temporary healthy memory numbers or absence of an active model process.

## Actual M1.1 offline metadata — status collection PASS, host acceptance still BLOCKED (2026-10-12)

Actual DGX operator ran the offline no-restart inspector at clean `6ce45561640f4069d534cbe04f5064a39095a88a`: `MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY`, `offline_diagnostic_rc=0`. The managed OrcaRouter container is **exited**, `exit_code=0`, `oom_killed=false`, Docker `state_error=""`. It began 2026-10-07 **16:35:45 KST** and ended **22:08:34 KST**. The declared Docker `HostConfig.PortBindings` map is **correct** `8888/tcp → 127.0.0.1:8888`; actual network port map is empty in the exited state. The prior Doctor's `docker port` failure is a **current-runtime readiness** failure, not proof of an erroneous configured binding.

Systemd `Result=success`, `ExecMainCode=1` (systemd process-exit class, **not exit status one**), `ExecMainStatus=0`, but service **inactive/dead**. ActiveEnterTimestamp **22:08:29 KST**, InactiveEnterTimestamp **22:18:17 KST**. Files `runtime-commit.env`, `runtime-stop.env`, and `monitor.pid` were all **ABSENT** at audit time. These point-in-time fields do **not** prove whether operator/protection/managed-transition stop occurred; stopped reason remains `NOT_YET_PROVEN`. The earlier Doctor **5 FAIL / 2 WARN** and M1 full-live-health **NOT_QUALIFIED** classifications are unchanged. [Canonical operator evidence](../scripts/benchmark/evidence/managed-runtime-offline-attempt01-exit0-no-oom-20261012.md).

**Next minimum gate:** the immutable, exact-SHA `scripts/lifecycle/inspect-readonly-runtime-stop-journal.sh` reads only a bounded 160-line historical unit journal window on **2026-10-07 21:55–22:25 KST**; no runtime launch, restart, purge, attestation reconstruction or protection changes. CI/source-only guard `tests/test_managed_runtime_stop_journal_readonly.py`. Journal contents may have sensitive environment/log details; inspect and redact before public sharing. Source/read-only inspector has **not** yet been run on DGX. If journal entries are absent or ambiguous, preserve STOP_REASON=UNVERIFIED and avoid repeating indefinite read-only probes.

This is a decision boundary: after the bounded journal check (or an inconclusive result) resume focus on lifecycle test coverage, UI acceptance, and off-host destructive rehearsal, while H38 model runtime remains independently blocked. A successful journal data collection cannot upgrade M1 host health, model correctness, RM safety or all-profile live E2E.

## M1.2 actual service journal: candidate aborted by memory protection, previous runtime retained stopped (2026-10-12)

The actual bounded `qwen38-flash-next.service` journal at pinned DGX checkout `efafe36fcc2e477e9d0cd110e4db275ba40dc489` **reclassified the managed stop path from unknown to observed**:

- Earlier **22:06:57–22:08:29 KST** `/health`, `/v1/models` and chat API HTTP 200 requests were logged for the **previous** runtime only.
- **22:08:30** explicit `Stopping current runtime container gracefully`, **22:08:35** runtime transition prepared with previous retained and **new candidate** started. Monitor started `protect=1`.
- Candidate readiness wait remained ongoing up to **540/1800 seconds**.
- **22:18:16** exact `Candidate runtime was stopped by memory protection during startup; leaving managed runtime stopped`; **22:18:17** `Previous runtime container restored but left stopped after memory protection`; `Runtime transition aborted by memory protection (state=idle)`.

The earlier canonical Docker zero exit / no OOM kill reflects a **graceful previous-container transition stop**; the recorded memory-protection intervention applied to the candidate and rollback workflow. Thus the current inactive runtime is an expected **fail-closed result of the logged protection abort**, not evidence of a bad Docker loopback binding. Do not infer that real host memory went OOM: **the particular monitor counter/threshold, possible cold-load false positive, and strict NVIDIA RM stability remain UNVERIFIED**.

[Canonical actual bounded journal evidence](../scripts/benchmark/evidence/managed-runtime-stop-journal-attempt01-protected-abort-20261012.md). The original reporter logfile was not byte-hashed. The helper's literal `RUNTIME_STOP_CAUSE=NOT_YET_CLASSIFIED` is a **static data-collection marker**; human review of explicit journal lines supports only `CANDIDATE_PROTECTION_ABORT_CONFIRMED`, not `MONITOR_TRIGGER_PREDICATE_PROVEN`.

**M1 acceptance remains PARTIAL**: inventory/schema/checkpoint/assets/transition status PASS, Doctor's earlier 5 FAIL and 2 WARN remain, actual live service readiness NOT_QUALIFIED. We will not restart or change monitor thresholds to produce green Doctor/CI. Exactly one final read-only monitor numerical-sample probe (`scripts/lifecycle/inspect-readonly-monitor-trigger.sh`) is staged with fail-closed SHA/file-size/type checks; it reads only structured local Oct07 monitor messages, not arbitrary container logs. Its actual host result is PENDING. If it cannot explain the trigger, stop probing and preserve `UNKNOWN`, returning work to lifecycle install/uninstall/profile-switch verification in synthetic/disposable environments. M2 destructive E2E NOT_RUN, M3 all-profiles E2E NOT_QUALIFIED, M4 H38 managed BLOCKED.

## M1.3 Actual protected-stop numeric threshold RESOLVED — return to lifecycle verification (2026-10-12)

The last bounded read-only monitor numeric probe **ran** on DGX at exact clean `7e4580bdca4054a788715bdf141e006bbb6b3f59`, reporting `MONITOR_TRIGGER_READONLY=COLLECTED_READ_ONLY`, `monitor_audit_rc=0`, **17** structured historical Oct07 messages from a ~2.24MB local monitor log. This operator result **supersedes "monitor probe pending / trigger numeric UNKNOWN" earlier in this document**.

Actual monitor startup threshold settings at **22:08:35 KST**: protect mode, non-CMA free floor **2GiB**, low-available/free gate **10GiB**, swap-growth gate **256MiB**, swapfree floor **8GiB**, and logged protection count `N/5`. At **22:17:33** non-CMA free **2,017 MiB** was marginally below 2GiB but swapgrowth only **17 MiB** and protect remained `0/5`. From **22:17:35** non-CMA free dropped to **1,151 MiB** and swapgrowth jumped to **654 MiB**, beginning `protect=1/5`. At **22:17:37, :39, :41, :43** the counter reached **2/5, 3/5, 4/5, 5/5**. At **22:17:43** a monitor entry says **`PROTECT stopping qwen38-flash-next gracefully to preserve host stability`**. Throughout these five samples non-CMA available was **well over 10GiB** and swapfree was **well over 8GiB**. Consequently the **actual observed branch was non-CMA immediate-free below 2GiB AND swap-growth greater than 256MiB, five consecutive samples**; **not** the low-available or low-swapfree branch. The managed service reported the protected candidate abort and stopped rollback at **22:18:16–22:18:17**.

[Canonical real numeric evidence](../scripts/benchmark/evidence/managed-monitor-trigger-attempt01-low-free-swap-growth-pass-20261012.md) is a grounded operator transcript; original /tmp logfile hash not independently verified. **This does not prove the monitor's heuristic is optimal, nor candidate model correctness, actual NVIDIA RM error or strict host stability.** A true host OOM, harmful vs benign PLE paging, and possible false-positive remain UNVERIFIED. No model was launched for this verification.

**STOP RULE achieved for this line of investigation:** no more DGX runtime/monitor probes for the historical event unless a new independent decision specifically requires them. The operator's primary goal is managed **installer/uninstaller/model/profile switch** completion. Continue existing safe implementation/test acceptance and restrict destructive E2E to an independently disposable host, with real GPU/H38 activation blocked. M1 **CI/synthetic passed**, but M1 **live host Doctor still FAIL_5/WARN_2 and service stopped by fail-closed protection**; M2 destructive live E2E NOT_RUN; M3 model all-pairs NOT_QUALIFIED; M4 H38 BLOCKED. The historic monitor explanation is not an entitlement to restart model, weaken protection, manufacture runtime-commit attestation, mark PR Ready or Merge.


## Early swap-ownership refusal for destructive uninstall (2026-10-12)

**Safety contract:** `uninstall.sh --purge-swap` and `--purge-all` (which implies swap purge) now reject a manifest with `SWAP_OWNED!=1` **after dry-run preview but before** acquiring the operation lock, bootstrapping asset ownership, stopping Docker/systemd, or deleting any installer data. The former check was positioned after teardown and, for full purge, after owned asset removal; an unowned swap could therefore leave a partially uninstalled deployment before refusing. `--dry-run` remains preview-only and does not certify real purge eligibility.

`tests/test_uninstall_wizard_preview.py::test_unowned_swap_purge_fails_before_host_or_fixture_mutation` exercises the real CLI on disposable HOME/XDG state for selected swap and full purge with daemon-command denial stubs and byte-for-byte fixture preservation. This is a **synthetic fail-closed regression**, not an authorized live DGX uninstall. M2 destructive E2E remains NOT_RUN; M1 actual host Doctor remains NOT_QUALIFIED and H38 runtime remains BLOCKED. PR #259 remains Draft/Open, merge blocked.


## Uninstall final-consent cancellation is read-only before lock/bootstrap (2026-10-12)

The real `uninstall.sh` previously ran `asset_bootstrap_install` and destructive-eligibility preflights before asking the operator to enter `DELETE`. A declined confirmation could create/update `asset-ownership.json` despite no authorized uninstall. The `DELETE` consent check is now **before** `acquire_operation_lock` and cumulative-ownership registry writes, but **after** strict manifest parsing and early unowned-swap refusal. EOF is an explicit cancellation error. `--yes` bypasses only interactive consent; post-lock transaction guards and asset preflights remain mandatory. This is not a guarantee of rollback **after** destructive steps begin.

New `tests/test_uninstall_wizard_preview.py::test_cancel_or_eof_preserves_ownership_and_install_state` calls the real non-dry-run CLI with a disposable HOME/XDG fixture. English default, Korean selected purge, full purge refusal and full purge EOF must reject before host command execution and preserve fixture bytes without creating `asset-ownership.json` or `operation.lock`. External Docker/systemd/sudo/swapoff commands are denied by PATH stubs. Initial [CI 38186275070](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38186275070) SUCCESS (766/766 synthetic tests) at commit `2e86ed4fa75a28bd585ff932cffdd4c4afab59ef`; final CI for the extended pre-existing-registry fixture tracked in PR #259. No actual DGX state was touched. M1 host NOT_QUALIFIED; M2 destructive E2E NOT_RUN; M3 all-profile E2E NOT_QUALIFIED; M4 H38 BLOCKED; PR #259 Draft/Open, Merge BLOCKED.

Existing cumulative-registry preservation is additionally tested by `test_cancel_preserves_existing_ownership_registry_bytes`: a pre-existing valid `asset-ownership.json` must retain its exact bytes on operator cancellation, with an owned-model manifest that would otherwise trigger legacy bootstrap migration. No host-side daemon calls are allowed. A confirmed, actively executing uninstall still requires independent destructive E2E qualification.


## Preflight-staged ownership registry for approved uninstall (2026-10-12)

The approved real `uninstall.sh` previously bootstrapped the **canonical** cumulative ownership registry before `preflight-one`, `preflight-purge`, external-container references and unowned-service checks. A failure could leave an altered `asset-ownership.json` without any authorized teardown. The revised flow, under the existing operation lock, copies the registry into a private same-filesystem `.uninstall-preflight.*` directory, runs the **existing** legacy bootstrap and eligibility checks against that staged copy, and publishes it only if all checks succeed; on a handled failure, an EXIT trap deletes the staged directory. An unchanged original registry is not needlessly replaced. Symlink/non-regular canonical registry paths are rejected. The operation lock file may remain after refusal. A process killed without running EXIT traps may leave a private staging directory for later inspection; no claim of crash-atomicity is made.

The new `test_approved_purge_preflight_failure_preserves_cumulative_registry` uses the real CLI with `--yes` on disposable HOME/XDG synthetic owned base + retained unowned dependent, exercising both `--purge-model` and `--purge-all`. It asserts blocked deletion, identical canonical registry/manifest/model bytes, no external host mutator calls and no left-behind staging directory. The actual DGX was not touched; this is synthetic failure-preflight coverage, not destructive-install/uninstall E2E or proof of post-teardown recovery. M1 live Doctor still NOT_QUALIFIED; M2 destructive E2E NOT_RUN; M3 all-pairs NOT_QUALIFIED; M4 H38 BLOCKED. PR #259 Draft/Open, merge blocked.


An additional `test_external_container_image_refusal_preserves_registry` exercises a synthetic `IMAGE_OWNED=1` with an external Docker-container reference. Read-only Docker image inspection and `ps` are stubbed; `docker rm`, image deletion, sudo/systemctl/swapoff, real host data access and model load are not allowed. The installer-owned image is refused at the **external-container preflight**, and the canonical registry and fixture bytes remain unchanged. This expands synthetic eligibility refusal coverage without asserting successful destructive uninstall.


### Synthetic approved-uninstall preflight result — CI verified (2026-10-12)

Exact tested code HEAD `c332959df7676d3d87a69eb628b94fa5af862e41`: [GitHub Actions CI #38188708849](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38188708849) **SUCCESS, 769/769 Python unit tests**, Bash syntax PASS, ShellCheck PASS, Python compilation PASS, whitespace PASS. Earlier base staging code HEAD `6186294fda78d9fed5d5bac8f35029b52c4a2856`: [CI #38188545527](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38188545527) **SUCCESS, 768/768**. This evidence covers synthetic failure branches for retained dependent model and externally referenced image; it is **not** evidence of successful real deletion or crash-atomicity. No DGX host operations were executed. All M1 host-health, M2 destructive E2E, M3 all-pairs, M4 H38, and PR #259 merge blockers remain.


## Docker removal failure and partial-uninstall retry safety (2026-10-12)

Previously `uninstall.sh` ignored **every** `docker rm -f` failure with `|| true`, risking model/image/release deletion when the Docker daemon or authorization was broken and the managed container could still exist. Now arbitrary Docker errors are **fail-closed before asset purge**; only an exact Docker `No such container: <managed name>` message permits idempotent continuation. `PHASE=complete` remains when service/container removal fails, allowing an operator-directed retry. `asset-ownership.json` may already reflect the successful preflight; the service may already have been disabled or removed. Neither rollback of completed teardown nor crash-atomicity is claimed. Real managed host and H38 model remain untouched. New disposable synthetic fault-injection regressions cover service-remove failure, Docker-remove failure, retry-after-recovery and already-absent Docker container; final CI result to be recorded in PR #259. M1 live host NOT_QUALIFIED, M2 destructive E2E NOT_RUN, M3 profile all-pairs NOT_QUALIFIED, M4 H38 BLOCKED, PR Draft/Open, Merge BLOCKED.


### Post-teardown failure and safe retry: synthetic CI acceptance (2026-10-12)

**Evidence:** [CI #38189466067](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38189466067) **SUCCESS, 771/771** at `09527d81121ad6fe820400382a12eb9a443318b6`; [CI #38189596217](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38189596217) **SUCCESS, 772/772** at `69df950fc4a7f1c6038ab8aff9f5e3ee45dc80b7`, including Bash syntax, ShellCheck, Python compilation and whitespace checks.

A synthetic real-CLI sequence using only disposable HOME/XDG and command denial/stubs shows:
1. Managed service-removal fault => no Docker removal attempt, owned synthetic model intact, manifest `PHASE=complete`.
2. Service removal succeeds, Docker daemon removal fails => script exits nonzero **before** model/image/release purge, records no completed uninstall, owned model and release preserved; published registry retains ownership evidence.
3. After fault clearance, retry completes, removes the **synthetic owned model only**, retains release data and sets `PHASE=uninstalled`.
4. An exact Docker `No such container` diagnostic is idempotent; unowned model and release remain.
5. On `--purge-all`, after **synthetic model and image removal** a simulated swap-remove failure exits nonzero with remaining fake swap and release preserved, manifest still `PHASE=complete` and cumulative registry reflecting completed asset removal. On retry after fault clearance, the script tolerates the already absent owned model/image, removes only the fake swap and synthetic release/manifest, and completes.

This proves bounded **synthetic retry behavior**, NOT rollback of previously removed components, interruption/crash durability, actual systemd/Docker/PLE behavior, independent disposable-host install/remove/reinstall E2E, or single-DGX host qualification. Actual DGX was untouched. M1 actual host NOT_QUALIFIED; M2 destructive E2E NOT_RUN; M3 all-profile E2E NOT_QUALIFIED; M4 H38 BLOCKED. PR #259 remains Draft/Open, Ready/Merge BLOCKED.


## SIGKILL interrupted-uninstall preflight recovery (2026-10-12)

Under the lifecycle operation lock and before creating a staged ownership copy or doing any teardown, `uninstall.sh` now refuses existing `.uninstall-preflight.*` artifacts, including symlinks. A `SIGKILL` or power loss bypasses shell EXIT traps, so these private staging snapshots may survive. Do **not** automatically delete them or treat them as canonical ownership evidence. Inspect each exact stale path, verify ownership and contents, confirm no concurrent lifecycle operation, and handle its removal/quarantine only as a separately authorized maintenance action. No blanket wildcard deletion on the active DGX. This guard is fail-closed: the install manifest and canonical ownership registry remain authoritative, and model/image/swap removal cannot proceed while an unreviewed preflight snapshot exists. Synthetic SIGKILL crash tests and exact GitHub CI evidence are tracked in PR #259; actual power-loss durability is NOT_QUALIFIED. PR remains Draft/Open and merge blocked.


### Interrupted uninstall recovery procedure and validation boundaries (2026-10-12)

**Stop condition:** a `.uninstall-preflight.*` artifact, missing model ownership manifest, drifted registry fingerprint, interrupted model deletion, or a state/host mismatch is **not** permission to resume unattended `uninstall.sh --yes`. Leave all host protection and stopped runtime settings intact.

1. Preserve evidence before any repair: read the canonical `install.env`, `asset-ownership.json`, exact `.uninstall-preflight.*` entries, file owner/mode and applicable logs **without executing the staged file or running host mutators**. The canonical registry is the only ownership authority; staged snapshots are untrusted. Acquire or confirm exclusive lifecycle maintenance ownership before any later mutation.
2. Reconcile actual read-only service/container/swap state with the recorded manifest. `PHASE=complete` after a crash **does not** mean the service is still installed, container still exists, model remains complete or swap is intact. Never infer successful teardown from parent process exit status alone; child deletion commands may outlive a killed parent.
3. For a verified orphan staging directory, document its exact path and integrity, quarantine/clear **only that exact path** after operator review, and rerun preflight before resuming; never use broad `rm -rf` globs or follow symlinks. Unreviewed staging blocks the real uninstaller.
4. For a partially deleted model with a missing/drifted `.qwen38-model-manifest.json` or `.qwen38-hybrid-manifest.json`, keep the original cumulative registry and the surviving model data; **do not invent a marker or weaken preflight**. Recovery requires independent trusted backup/provenance verification, otherwise quarantine and a separately authorized reinstall on an isolated disposable host.
5. If a fully removed owned model is already absent but a dedicated swap/release remains, a repeat purge is eligible **only after** checking the original model path, ownership history, live host state, swap provenance and pending lifecycle artifacts. No automated or live sole-DGX destructive recovery is authorized by the synthetic tests.
6. Preserve an interruption evidence report (files/hashes, timeline, host-command results, whether child process survived, repair decision). Host power-loss filesystem ordering/fsync, SIGKILL of the whole process group, real teardown replay and install→remove→reinstall remain unverified separately.

Synthetic `test_sigkill_during_stage_requires_manual_stale_recovery`, `test_sigkill_partway_through_model_delete_requires_verified_recovery`, and `test_sigkill_at_swap_after_model_purge_can_resume` use the **real** CLI with disposable HOME/XDG, fake owned model/swap and PATH-denied Docker/sudo/systemctl/swapoff. Their SIGKILL is injected from a child stub and the stub must exit immediately rather than completing its own deletion after killing the parent. These tests do not simulate power loss or provide live-host authorization. Previous failing CI attempts due to a child-stub execution bug are retained as historical failures; the corrected commit and its CI outcome are recorded in PR #259. All M1 actual-host/M2 real-destructive/M3 all-profile/H38 gates remain blocked or unqualified; PR #259 remains Draft/Open, Ready/Merge BLOCKED.


## Guarded DGX code synchronization and synthetic-only local verification (2026-10-12)

The previous 775/775 GitHub Actions result was **CI**, not evidence that the operator's single DGX had fetched the latest branch or run any tests locally. To close this handoff gap without touching live host resources, `scripts/lifecycle/verify-synthetic.sh` now validates an explicitly supplied 40-character checkout SHA, clean Git worktree, exact `feat/h38-managed-integration` branch and matching `origin/feat/h38-managed-integration` tracking ref **without any Git mutation**. It then runs bounded Python synthetic lifecycle suites inside a disposable HOME/XDG_STATE_HOME/XDG_DATA_HOME/TMPDIR, with a first-in-PATH deny wrapper for Docker, sudo, systemctl, swapoff/swapon, mount/umount and nvidia-smi. Tests are restricted to installer/uninstaller preview, ownership, operation lock, lifecycle integration and non-mutating lifecycle snapshot tests; no actual install/uninstall, Docker, service change, runtime startup, model download or host Doctor is invoked. The test wrapper is itself exercised on GitHub Actions in `--ci` mode and refuses `--ci` outside `GITHUB_ACTIONS=true`.

**Operator sync procedure, not executed by ChatGPT:** on the actual DGX working checkout, require `git status --porcelain=v1 --untracked-files=all` empty and the expected feature branch already selected; `git fetch --prune origin`; confirm `origin/feat/h38-managed-integration` equals the **exact tested target SHA**; then `git merge --ff-only origin/feat/h38-managed-integration`, confirm HEAD and worktree, and invoke the new verifier with that SHA. No `git reset --hard`, stash/pop, force merge or automatic checkout switching. Sync/test modifies the local Git checkout and disposable test files only; no remote host access or DGX test was performed from ChatGPT. **Report DGX_LOCAL_SYNTHETIC=NOT_RUN until the operator supplies actual local output.** Keep `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, PR #259 Draft/Open; Ready/Merge BLOCKED.


### Verified safe Git sync and synthetic-only DGX test handoff (2026-10-12)

[CI #38192014751](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38192014751) **SUCCESS** for code commit `c915f805b7fe7abbc8a260379df69148ef5f54e6`: **780/780** full unit tests, Bash syntax, ShellCheck, Python compilation, whitespace, plus an actual execution of `scripts/lifecycle/verify-synthetic.sh` in the GitHub PR checkout with **48/48** bounded synthetic tests (16 uninstall wizard, 6 asset ownership, 8 operation lock, 14 lifecycle integration, 4 snapshot tests). The GitHub Actions checkout may be a PR merge SHA rather than the feature branch HEAD; the verifier checks the exact SHA **of the checkout it is given**. An earlier [CI #38191976973](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38191976973) failure was a missing-SHA message/test mismatch; corrected in `c915f80` with tests passing.

**DGX operator-only sync/test, not run by ChatGPT**: choose the latest verified GitHub branch head SHA as `TARGET`. Start on branch `feat/h38-managed-integration` with a clean worktree. Confirm remote `origin` points to the expected GitHub repository, fetch only the branch without tags, assert `origin/feat/h38-managed-integration` equals the pinned SHA, and fast-forward only with Git hooks disabled. Never reset/stash/force-overwrite local edits. Then run `bash scripts/lifecycle/verify-synthetic.sh "$TARGET"` to verify the exact local checkout. This tool **does not run fetch/merge**, Docker, service manager, install, uninstall, runtime/host Doctor or any model; it runs only the five synthetic test modules under disposable HOME/XDG/TMPDIR and intercepts host commands through PATH stubs. **PATH interception is not an OS-level sandbox**; tests are allowlisted after source review and GitHub CI qualification. If remote advanced beyond the pinned target or any preflight fails, stop without changing the checkout and reassess the SHA.

`DGX_LOCAL_SYNTHETIC=NOT_RUN` until the operator sends the **actual DGX output** (including exact SHA and `LOCAL_SYNTHETIC_RESULT=PASS`). `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, PR #259 Draft/Open and Ready/Merge BLOCKED.


## DGX-selected profile read-only snapshot and ordered operator verification (2026-10-12)

Operator-provided DGX log proves the earlier clean fast-forward through
`0e910a7e0ab6246228857cc9432c19b5787eb812` and the local **48/48
synthetic lifecycle tests PASS**, final `DGX_SYNTHETIC_VALIDATION_COMPLETE`.
The local command printed `SHELLCHECK=SKIPPED_NOT_INSTALLED` (ShellCheck
already passed GitHub CI), and did **not** qualify running model/runtime or
the destructive host E2E. This is historical exact-SHA local evidence only.

New `scripts/lifecycle/inspect-selected-profile.py` gives a compact,
read-only actual-host snapshot separately from the synthetic verifier:
strict `install-maintenance` manifest parsing reports selected model
profile/phase/repository/path/expected image/served name and monitor
protection; four strict transition status files and stale artifacts are
reported; read-only Docker inspect and systemctl show report runtime and
service observations. Docker/systemd probe errors remain UNKNOWN. A running
container with matching image/mount/served command is labeled
`MATCHED_NOT_READINESS`, **never actual serving/health qualified**.
Corrupt manifest or pending transition causes fail-closed nonzero exit.
Synthetic unit tests with temporary HOME/XDG and mocked host commands
verify stopped, missing, uninstalled, invalid, transition pending and
running-but-unqualified cases.

The expanded `inspect-readonly-lifecycle.sh` now prints selected-profile
snapshot **first**, before model inventory, other transitions and Doctor.
Operator sequencing: (1) safe exact-SHA Git synchronization, (2) actual
read-only selected-profile snapshot, (3) disposable synthetic tests, then
(4) optional comprehensive read-only Doctor. The disposable verifier
**must not be mistaken for an actual DGX runtime-status probe**.

Do not invoke install/uninstall, Docker mutation, systemd restart, model/GPU,
swap mutation, host monitor relaxation or H38. New actual-host snapshot
execution is **NOT_RUN** until its operator-provided DGX output is supplied.
M1 live host NOT_QUALIFIED, M2 destructive E2E NOT_RUN,
M3 model all-pairs NOT_QUALIFIED, M4 H38 BLOCKED; PR #259 Draft/Open,
Ready/Merge BLOCKED.


## DGX actual selected-profile and isolated test evidence (2026-10-12)

**Source:** operator-provided actual DGX transcript, fast-forward from `0e910a7`
to exact feature HEAD `87fb463984683f75435302eff5ffc3b3b9f941bf` with clean
post-test checkout and `DGX_PROFILE_AND_SYNTHETIC_VALIDATION_COMPLETE`.
`verify-synthetic.sh` reported `LOCAL_SYNTHETIC_RESULT=PASS` with **56/56**
disposable synthetic tests (16 uninstall, 6 ownership, 8 lock,
14 integration, 8 selected-profile snapshot, 4 read-only snapshot).
Local `BASH_SYNTAX=PASS`; `SHELLCHECK=SKIPPED_NOT_INSTALLED` (separately,
[GitHub CI #38194619518](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38194619518)
SUCCESS: 788/788 full unit tests and ShellCheck PASS). **DGX_LOCAL_SYNTHETIC=PASS at
this exact SHA only.**

Actual read-only DGX `inspect-selected-profile.py` reported:

| Observed field | Reported value / qualification |
|---|---|
| `MANIFEST_STATUS` / `INSTALL_PHASE` | `VALID` / `complete` |
| `SELECTED_PROFILE` | `orcarouter` (configuration intent) |
| `PROFILE_REPOSITORY` | `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` |
| `EXPECTED_IMAGE` and `CONTAINER_IMAGE` | `vllm-skinny-tp1:v1` (legacy installed tag; H38 not active) |
| `MODEL_PATH_STATUS` | `MARKER_PRESENT_NOT_VERIFIED` (not checksum/integrity) |
| `MONITOR_PROTECT` / `MONITOR_ENABLED` | `1` / `1` (configured, not verified running protection) |
| `PROFILE_SWITCH_STATE`, `RUNTIME_TRANSITION_STATE`, `UPDATE_STATE`, `RELEASE_PROFILE_REFRESH_STATE` | all `IDLE` |
| `STALE_TRANSACTION_ARTIFACTS` | `NONE` (only the configured tracked subset) |
| `CONTAINER_STATE` / `SERVICE_STATE` | `EXITED` / `INACTIVE` |
| `RUNTIME_ATTESTATION` | `MISSING`; do not manufacture it |
| `PROFILE_STATUS_SUMMARY` | `CONTAINER_NOT_RUNNING` |
| `ACTUAL_SERVED_PROFILE` | `NOT_VERIFIED` |
| `HOST_HEALTH_QUALIFICATION` | `NOT_ESTABLISHED_BY_THIS_SNAPSHOT` |

**Interpretation and next priority:** Git code/tests are synchronized and the
selected profile is `orcarouter`, but the runtime is stopped. Its stop cause
is **NOT YET DETERMINED** by this newly submitted output: an exited container
plus inactive service does not prove OOM, a protection-triggered stop,
deliberate administrative shutdown or a runtime error. Runtime commit
attestation is absent; never reconstruct an attestation without verified
provenance. H38 code is not an installed/serving H38 model. Retain host
monitor/protection and all stopped services as observed: **NO restart, H38 GPU
rerun, swap cleanup, reinstall, profile-switch or uninstall**.

**Next existing read-only tool (no new script or additional Git pull is
required at verified SHA `87fb463...`):**
```bash
(
  set -Eeuo pipefail
  cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark
  TARGET=87fb463984683f75435302eff5ffc3b3b9f941bf
  test "$(git rev-parse HEAD)" = "$TARGET"
  test -z "$(git status --porcelain=v1 --untracked-files=all)"
  QWEN38_OFFLINE_DIAGNOSTIC_TARGET_SHA="$TARGET" \
    bash scripts/lifecycle/inspect-readonly-runtime-offline.sh
)
```
This existing exact-SHA helper reads `docker inspect` (container exit
code, OOMKilled, start/finish timestamp, state error, declared ports),
`systemctl show` (ActiveState/Result/ExecMainCode/ExecMainStatus/timestamps),
and `stat` file metadata for `runtime-commit.env`, `runtime-stop.env` and
`monitor.pid`. It prints `RUNTIME_STOP_REASON=NOT_YET_PROVEN`; the output
is **evidence for triage**, not authorization to restart or proof of cause.
Historical Oct-07 journal/monitor scripts are time-window bound, so only use
them after checking whether the observed `FinishedAt` falls in their
documented window. If the offline command returns 3, preserve its partial
results and do not reinterpret failure as stop-cause evidence.

**Gates:** `DGX_LOCAL_SYNTHETIC=PASS` at specified SHA, but
`M1_HOST_HEALTH=NOT_QUALIFIED`, `HOST_STABILITY=INCONCLUSIVE`,
`M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`,
`M4_H38=BLOCKED`, `HOST_PROTECTION=UNCHANGED`; PR #259 Draft/Open,
Ready/Merge BLOCKED.


## Reconciled DGX offline repeat versus previously resolved Oct 7 protection stop (2026-10-12)

The operator's latest **actual DGX** read-only `inspect-readonly-runtime-offline.sh`
run at a clean exact checkout `87fb463984683f75435302eff5ffc3b3b9f941bf`
completed all three queries (`rc=0`) and returned `MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY`.
Docker `status=exited exit_code=0 oom_killed=false`, started **2026-10-07
16:35:45.800732 KST**, finished **22:08:34.847185 KST**; correct declared
loopback `127.0.0.1:8888` binding with no active port mapping while stopped.
Systemd `Result=success ExecMainCode=1 ExecMainStatus=0 inactive/dead`,
ActiveEnter **22:08:29 KST**, InactiveEnter **22:18:17 KST**.
`runtime-commit.env`, `runtime-stop.env`, and `monitor.pid` were **ABSENT**
at observation. The repeated values match the older exact-DGX
[offline Attempt 01](../scripts/benchmark/evidence/managed-runtime-offline-attempt01-exit0-no-oom-20261012.md)
recorded at a different checkout, not a new runtime or H38 test.

**Resolve chronology using existing historic evidence, not an additional
monitor experiment.** The already archived
[service journal](../scripts/benchmark/evidence/managed-runtime-stop-journal-attempt01-protected-abort-20261012.md)
explicitly records graceful stop of the **previous** container for candidate
handover **22:08:30**, candidate monitor/start at **22:08:35**, and candidate
abort by memory protection **22:18:16**, then **previous container restored
but left STOPPED 22:18:17**. The separately archived
[numeric monitor samples](../scripts/benchmark/evidence/managed-monitor-trigger-attempt01-low-free-swap-growth-pass-20261012.md)
confirm low non-CMA free memory **below 2 GiB** together with swap growth
**at least 256 MiB**, counted for **5 consecutive protection samples**
and `PROTECT stopping` at **22:17:43**. Thus the stopped canonical container's
`exit_code=0 oom_killed=false` correlates with the previous container's
handover/rollback, **not** with the candidate's unobserved Docker exit.
There is no candidate immutable ID or attestation proof in the new snippet;
no kernel OOM/NVIDIA RM failure, false positive, safe memory peak or
candidate READY may be inferred.

This reconciliation supersedes earlier **intermediate** lines stating the
Oct 7 *managed transition's* stop cause or protection threshold branch were
still wholly undetermined. The inspector itself intentionally emits the
literal `RUNTIME_STOP_REASON=NOT_YET_PROVEN` as a collection marker, and
must remain unchanged. The **managed-service protection-abort sequence
and numeric trigger branch are confirmed by earlier evidence**, while
ultimate kernel/driver/model root cause and protective-policy appropriateness
are still **UNVERIFIED**. No new H38 GPU rerun or additional journal hunt.

Canonical new [repeat cross-check evidence](../scripts/benchmark/evidence/managed-runtime-offline-repeat-crosscheck-20261012.md)
preserves source, timestamps and limits. `DGX_LOCAL_SYNTHETIC=PASS` only
for the earlier 56/56 locally run at `87fb463`; the new docs-only GitHub
HEAD has **not** been pulled/tested on the DGX. Maintain
`M1_HOST_HEALTH=NOT_QUALIFIED`,
`M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`,
`M4_H38=BLOCKED`, `HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`,
PR #259 **DRAFT/OPEN, Ready/Merge BLOCKED**. Primary next engineering
priority is **host-independent installer/uninstaller/profile-switch acceptance**,
then independent disposable-host E2E. Do not restart or mutate the sole DGX.


## Fail-closed uninstall plan, Docker dependency, and image absence (2026-10-12)

GitHub source-only hardening captures an ownership `plan-purge` during staged
preflight with an explicit successful producer exit; partially output
nonzero plans cannot authorize teardown. External `docker ps` must succeed,
not merely return zero results; `docker image inspect` must explicitly
report `No such image/object` to authorize an absent image. Unexpected
Docker command failures stop the purge, including at final image-forget.
Fixture regressions exercise failures before registry publication and retain
the preexisting canonical manifest/registry and unowned assets.

Final qualifying CI for the code at
[GitHub Actions #38196834096](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38196834096)
**SUCCESS 792/792 Python, 60/60 bounded synthetic tests**, plus Bash,
ShellCheck, Python compilation, whitespace. Two intermediate CI failures
were test-stub representation problems, preserved in
[specific evidence](../scripts/benchmark/evidence/managed-uninstall-fail-closed-purge-plan-docker-20261012.md).
The independent [disposable-host E2E plan](DISPOSABLE-LIFECYCLE-E2E-PLAN.md)
is an **acceptance plan, NOT an executed test**.

Current sole DGX checkout was last operator-observed at `87fb463...`, with
56/56 synthetic PASS and service/container intentionally stopped after the
Oct 7 protection-abort sequence; new source not locally synchronized/tested.
`M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`,
`M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`,
`HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`.
Never run destructive lifecycle gates on the sole DGX. PR #259 Draft/Open,
Ready/Merge BLOCKED.


## DGX local synthetic acceptance at exact uninstall-hardening SHA (2026-10-12)

An actual operator-provided DGX terminal log confirms a clean guarded
fast-forward `87fb463 → 02e9c61`, exact checkout
`02e9c61d90c7f15484b0605dc872bbbb21ec253b`, final SHA/worktree
checks, and `DGX_SYNTHETIC_VALIDATION_COMPLETE`. The isolated
`verify-synthetic.sh` tests passed **60/60**:
19 uninstall, 7 asset-ownership, 8 operation-lock, 14 lifecycle integration,
8 selected-profile-readonly and 4 full-readonly-snapshot tests.
`LOCAL_SYNTHETIC_RESULT=PASS`, `BASH_SYNTAX=PASS`,
`LOCAL_SYNTHETIC_SCOPE=DISPOSABLE_FIXTURES_ONLY`, and
`LOCAL_SYNTHETIC_HOST_COMMANDS=PATH_DENY_STUBS` were observed.
Local `SHELLCHECK=SKIPPED_NOT_INSTALLED`; separately
[CI #38197243631](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38197243631)
was **SUCCESS, 792/792 full tests**, **60/60 synthetic**, ShellCheck PASS.
This explicitly upgrades the earlier statement that the uninstall-hardening
code had not been synchronized/tested on the DGX.

See [actual DGX synthetic acceptance evidence](../scripts/benchmark/evidence/dgx-synthetic-uninstall-hardening-pass-20261012.md).
The DGX log **does not contain a new live service/Doctor inspection**;
the prior `orcarouter` selected profile and stopped runtime observation
remain historical, not a new readiness claim. Keep
`M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`,
`M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`,
`HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`,
PR #259 Draft/Open and Ready/Merge BLOCKED.

## Full ordered profile-switch pair matrix — synthetic CI (2026-10-12)

Four state-schema profiles (`orcarouter`, `nvidia`, `mazinb`,
`orcarouter-hybrid`) yield **12 distinct ordered profile switches**. The
synthetic transaction suite now checks all 12 for (1) uncommitted
activation recovering exact source manifest, (2) attested target runtime
finalizing target manifest, and (3) mismatched candidate container-ID
attestation refusing commit then allowing provable source rollback.
Same-profile and wrong-source prepares are also refused for all four
starting profiles. Existing interrupted-state and lock fixtures remain.

[CI #38204508012](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38204508012)
**SUCCESS, 796/796 full tests, 70/70 allowlisted synthetic tests** and
Bash, ShellCheck, Python compile and whitespace PASS. The exact-SHA local
synthetic runner now includes the mocked profile-switch test module
(**10 tests**). [Pair matrix evidence](../scripts/benchmark/evidence/managed-profile-switch-pair-matrix-synthetic-20261012.md)
records subtest coverage and evidence boundaries. It is **NOT** a true
Docker/systemd profile-switch E2E, and does not qualify M3.

The operator's last actual DGX synthetic run was **60/60 at `02e9c61`**;
this newer pair-matrix source has not been synchronized/run locally on
the DGX. Preserve the stopped runtime/protection, do not run live
profile switches or model starts. `M1_HOST_HEALTH=NOT_QUALIFIED`,
`M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`,
`M4_H38=BLOCKED`, `HOST_STABILITY=INCONCLUSIVE`,
`HOST_PROTECTION=UNCHANGED`; PR #259 Draft/Open and Merge BLOCKED.

## Actual DGX 70/70 directed profile-pair synthetic acceptance — 2026-10-12

The operator supplied a successful exact-SHA guarded DGX fast-forward
`02e9c61 → d2e9a1d` and `verify-synthetic.sh` output proving **70/70
selected synthetic tests PASS**, **Bash syntax PASS**, and final exact clean
checkout `d2e9a1dc2b9759bc60915f2a7cda7b0cfd9d4914`. Breakdown:
19 uninstall + 7 assets + 8 locks + 14 lifecycle integration +
**10 profile-switch transaction** + 8 selected-profile snapshot +
4 lifecycle snapshot. Profile-switch synthetic cases include all 12
ordered pair directions with successful target attestation, uncommitted
rollback, and incorrect container-ID rejection/rollback.

DGX `SHELLCHECK=SKIPPED_NOT_INSTALLED`. Separately
[CI #38204845533](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38204845533)
**SUCCESS**, 796/796 full unit tests, 70/70 selected synthetic and
ShellCheck/Bash/Python/whitespace PASS. The previous 60/60 actual-DGX
local synthetic acceptance at `02e9c61` is superseded as **latest**
local synthetic evidence. See the
[actual-DGX 70/70 evidence](../scripts/benchmark/evidence/dgx-profile-pair-synthetic-pass-20261012.md).

This proves neither physical Docker/systemd transition nor readiness,
M1 host health, M2 destructive E2E, M3 actual all-pair qualification or
M4 H38. Selected `orcarouter` and stopped runtime are **historical** read-only
observations, not updated by this test. The current single DGX host's
service/monitor/swap/protection remain untouched. `HOST_STABILITY=INCONCLUSIVE`,
`HOST_PROTECTION=UNCHANGED`; PR #259 DRAFT/OPEN and Ready/Merge BLOCKED.

## New actual DGX 70/70 confirmation and GitHub-only profile-switch drift gates — 2026-10-12

The user-supplied **actual DGX** terminal log confirms exact-SHA
fast-forward `d2e9a1d → fb6e0ed`, final clean checkout
`fb6e0ed4075ac5fa8a3142137d068eb98d65e4bf` and
`verify-synthetic.sh` **70/70 PASS** (7 allowlisted modules including
10 profile-switch tests). The on-host `BASH_SYNTAX=PASS`; local
`SHELLCHECK=SKIPPED_NOT_INSTALLED`. GitHub CI #38207710548 at this
same source had **796/796 full and 70/70 selected PASS**, including
CI ShellCheck, not on-host ShellCheck. This supersedes `d2e9a1d` as
**latest actual DGX locally tested SHA**, without changing host readiness
or previously observed runtime state.

Additionally, GitHub-only source commit `8538c83` added **3
disposable profile-switch fault regressions**: tampered backup SHA
refuses rollback while preserving state; tampered candidate SHA refuses
target commit and can roll back to a provable old runtime; removal of
runtime attestation after a recorded commit refuses finalization until
proof is restored. [CI #38210907792](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38210907792)
**SUCCESS, 799/799 full Python tests, 73/73 synthetic, ShellCheck PASS**.
These 3 cases have **not been run on the actual DGX**.

Evidence: [actual DGX console](../scripts/benchmark/evidence/dgx-synthetic-doc-head-pass-20261012.md)
and [manifest/attestation fault injection](../scripts/benchmark/evidence/managed-profile-switch-drift-attestation-synthetic-20261012.md).
Neither result qualifies live M1, real D0–D5 M2, all-pairs service M3 or
H38 M4. `HOST_STABILITY=INCONCLUSIVE`,
`HOST_PROTECTION=UNCHANGED`. No model/service/swap/GPU change. PR #259
must remain Draft/Open/Unmerged and Ready/Merge BLOCKED.

## Actual DGX 73/73 and fail-closed profile-switch orphan-state hardening — 2026-10-12

Operator-supplied real DGX output confirms a clean, exact guarded
fast-forward `fb6e0ed → e18c56a` and **73/73 local isolated synthetic
tests PASS**, including **13 profile-switch transaction tests**.
`BASH_SYNTAX=PASS`, local `SHELLCHECK=SKIPPED_NOT_INSTALLED`,
`LOCAL_SYNTHETIC_RESULT=PASS` and final
`DGX_PROFILE_RECOVERY_SYNTHETIC_VALIDATION_COMPLETE` were observed.
Latest actual DGX verified SHA is
`e18c56aff008f717ad54ee787ab20c248e987e34`.

Subsequent GitHub-source-only review found a **false-idle fail-open**:
a dangling transition file link or orphan backup/candidate/staging
artifact could be hidden by the no-state branch of `recover`,
`rollback`, `service-recover` or `status`. The new code refuses to
claim idle while any such file or link remains, preserving normal truly
idle behavior. Three new fixture unittest methods exercise the
dangling/orphan/valid-idle matrix. [Source CI #38212223945](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38212223945)
**SUCCESS 802/802 full Python, 76/76 synthetic**, plus Bash,
ShellCheck, compile and whitespace PASS. **This new source is not yet
executed locally on the DGX.**

[Evidence details](../scripts/benchmark/evidence/dgx-73-and-profile-switch-false-idle-hardening-20261012.md).
No live host E2E, Docker/systemd profile changes or H38 reruns.
`M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`,
`M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`,
`HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`,
PR #259 Draft/Open, Ready/Merge BLOCKED.


## New actual DGX 76/76 synthetic acceptance and prepare fail-closed check — 2026-10-12

A newly supplied DGX console transcript confirms exact guarded fast-forward `e18c56a → 9220624` and **76/76 local isolated synthetic methods PASS** on `922062436b71353760c2323103e749ed6eaf6240`, including 16 profile-switch methods. `BASH_SYNTAX=PASS`, local `SHELLCHECK=SKIPPED_NOT_INSTALLED`, clean exact HEAD and worktree, `LOCAL_SYNTHETIC_RESULT=PASS` and final `DGX_PROFILE_IDLE_SAFETY_SYNTHETIC_COMPLETE` were observed. The matching GitHub [CI #38212708550](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38212708550) passed 802/802 full and 76/76 synthetic tests plus ShellCheck. This **supersedes 73/73 as the latest actual DGX local synthetic**, not as any live host qualification.

A subsequent safety review found that `prepare` did not apply the existing orphan `.tmp` fail-closed check used by idle/recovery actions. The source now applies the shared guard before publishing a new transaction, with a new seven-scenario (six artifacts and one dangling symlink) fixture regression method. **The new source change was not part of the completed DGX 76/76 run.** [New-source CI #38215072213](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215072213) **SUCCESS 803/803 full tests, 77/77 bounded synthetic (17 profile-switch), ShellCheck/Bash/compile/whitespace PASS** at `51e85f6578ee0694a13964f700f30e854f17c020`. This new source has not been tested on DGX.

[New DGX and source review evidence](../scripts/benchmark/evidence/dgx-76-and-prepare-orphan-guard-20261012.md). Actual Docker/systemd E2E, M1/M2/M3/M4 gates and host protection are unchanged: `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`; PR #259 stays Draft/Open, Ready/Merge BLOCKED.


## Actual DGX 77/77 profile-switch prepare guard acceptance — 2026-10-12

New operator-provided console evidence confirms guarded fast-forward `9220624 → 1283b1a` and **77/77 isolated local synthetic tests PASS** on exact DGX checkout `1283b1a9252f1ff53d51659049ca42f9449e5ccd`, including **17/17 profile-switch tests** and the new `prepare` orphan-staging preservation regression. Exact final HEAD, `LOCAL_SYNTHETIC_RESULT=PASS` and `DGX_PREPARE_ORPHAN_SYNTHETIC_COMPLETE` were observed. Bash syntax PASS; **local ShellCheck SKIPPED_NOT_INSTALLED**, distinct from [GitHub CI #38215504822](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215504822) **SUCCESS 803/803 full and 77/77 synthetic, ShellCheck PASS**.

[Canonical 77/77 operator evidence](../scripts/benchmark/evidence/dgx-77-prepare-orphan-synthetic-pass-20261012.md). This updates the latest *DGX-local isolated synthetic* source from `9220624` (76/76) to `1283b1a` (77/77), **not** any real Docker/systemd/model acceptance. `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`. PR #259 remains Draft/Open/Unmerged and Ready/Merge BLOCKED; no protected DGX runtime mutation.


## Disposable D0 offline evidence precheck — code staged, not host-qualified (2026-10-12)

A new **offline-only** reviewer, `disposable-d0-preflight.py`, validates two
explicit operator-provided JSON files using Python stdlib only. It never reads
live Docker, systemd, host identity, Git or model state; it never runs commands
on any host. Required policy: exact SHA and repository, **nonempty protected
machine-id hash and Docker daemon denysets**, forbidden production roots.
Required inventory: separately identified disposable machine/daemon, clean
exact SHA + origin, owner disposable declaration, restore point, isolated
non-default Docker context without external users, nonoverlapping throwaway
model/log/work roots, bounded owned synthetic model, non-production service
unit, and no pending lifecycle transactions.

Run **only against an independently assembled, reviewed inventory**:
`python3 scripts/lifecycle/disposable-d0-preflight.py --policy <policy.json> --inventory <inventory.json>`.
No real protected machine IDs, daemon IDs, credentials or private mount
inventories belong in Git history or CI logs. Inputs are treated as
**untrusted assertions**: success prints
`D0_STATIC_REVIEW=READY_FOR_INDEPENDENT_REVIEW` but always
`D0_ADMISSION=NOT_GRANTED` and `D0_LIVE_E2E=NOT_AUTHORIZED`.
Any incomplete/mismatched evidence fails closed with exit 2. A passing
offline check is **not** permission for D1–D5; independent operator
attestation, read-only on-host cross-check and explicit disposable-host
authorization remain mandatory. Neither current DGX nor M1/M2/M3/M4
qualification is changed.


### D0 offline evidence policy CI acceptance (2026-10-12)

Source `7acd15cc5a2d8f5603bdb82b08b1cee49da7d18a` introduced a stdlib-only JSON D0 policy evaluator and nine fixture regressions. [GitHub CI #38217170909](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38217170909) **SUCCESS 812/812 full tests, 77/77 existing bounded synthetic**, Bash syntax, ShellCheck, Python compile, whitespace PASS. The D0 test methods are **not** yet in the bounded DGX verifier; latest DGX actual local run remains `1283b1a` **77/77**. A policy-consistent response is `D0_STATIC_REVIEW=READY_FOR_INDEPENDENT_REVIEW` with `D0_ADMISSION=NOT_GRANTED`; it is not live host attestation or D0 acceptance. [Permanent source/limitation evidence](../scripts/benchmark/evidence/disposable-d0-offline-preflight-ci-20261012.md). M1/M2/M3/M4 remain NOT_QUALIFIED/NOT_RUN/BLOCKED and PR #259 stays Draft/Open/Unmerged.


## D0 independent-host on-host read-only cross-check (source only; 2026-10-12)

A new conservative `disposable-d0-readonly-crosscheck.py` requires the
`--ack-independent-disposable-host` flag plus the existing strict
`--policy` and `--inventory` JSON. The **sole protected DGX is not a
permitted target**. It first validates the offline D0 policy and compares a
hashed real machine identity against the inventory and protected denyset
**before** any Docker/systemd calls. It then performs bounded read-only
Git HEAD/origin/worktree, candidate path realpath and mountpoint, Docker
context/daemon/empty-container, and dedicated disposable service-unit checks.

The collector does not probe without the explicit independent-host
acknowledgement, does not ask for sudo, does not modify files or host
configuration, and never installs/uninstalls or starts models. Its JSON
output excludes raw host identities, secrets, mounts and container IDs.
The output is `ON_HOST_READ_ONLY_ASSERTION_CROSSCHECK`, with
`d0_admission=NOT_GRANTED` and `d1_d5=NOT_AUTHORIZED` **even after
all observed fields match**. A missing daemon, unknown service response,
realpath/mount drift, protected identity or unclean Git state fails closed.

This cross-check **does not independently prove** owner consent, absence of
external Docker users, isolation of the underlying daemon, mount sources
outside the selected roots, or restoration/snapshot viability. Independent
D0 trust review and explicit authorization remain necessary. Current status:
**source and fixture tests only; not executed on any physical disposable
host or the protected DGX; M1–M4 and D1–D5 unchanged**.


## D0 independent-host read-only crosscheck — GitHub source CI (2026-10-12)

The new on-host read-only D0 cross-check source was implemented at `b6d3188`. Its first [CI #38218386709](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38218386709) **FAILED 1 of 824 full tests**, because a Docker-outage *fixture* used an `AssertionError` instead of subprocess-style `OSError`. The test fake was corrected without relaxing safety guards. [Source CI #38218663210](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38218663210) **SUCCESS 824/824 full Python, 77/77 existing bounded synthetic**, Bash/ShellCheck/Python compile/whitespace PASS at `b99b510e89cc08d99d683dcbf77c75bb55941b2c`.

The 12 new fixture cases cover protected host/daemon identities, clean Git source, path and mount drift, Docker outage/contamination and nonexclusive service refusal. No actual Docker/systemd on a disposable host was inspected; the collector is **not approved for the sole protected DGX**. Its on-host result always keeps `d0_admission=NOT_GRANTED` and `d1_d5=NOT_AUTHORIZED`, even when supplied host observations match. [Permanent evidence and trust limitations](../scripts/benchmark/evidence/d0-onhost-readonly-crosscheck-ci-20261012.md). Latest *actual DGX local* isolated synthetic remains 77/77 at `1283b1a`. D0 independent real-host review and D1–D5 remain NOT_RUN; M1/M2/M3/M4, strict host protections and PR #259 Draft/Open/Unmerged are unchanged.


## D0 parent-mount and Docker-endpoint fail-closed refinement (2026-10-12)

The source-only read-only host observer now rejects **non-root ancestor mounts** overlapping proposed disposable roots, Docker environment overrides, TCP/SSH and default/shared Unix socket endpoints, aliased/missing sockets, and refuses to use an implicit Docker context for daemon reads. Git command probes set `GIT_OPTIONAL_LOCKS=0` to avoid optional Git index refresh. The four trust-boundary fixture methods and one Git no-optional-locks method extend the read-only D0 module to **17/17 synthetic tests**.

[CI #38266470002](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38266470002) at `4dfc2aed238ce96be0b5f3970256b8a2ce8cadf8` **SUCCESS 828/828 full, 77/77 selected**, and [CI #38267015272](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38267015272) at `b65c0142340d90d681c8f82d05294bb72d813687` **SUCCESS 829/829 full, 77/77 selected** plus Bash/ShellCheck/Python compile/whitespace PASS. [Canonical source evidence](../scripts/benchmark/evidence/d0-parent-mount-docker-endpoint-guards-20261012.md) explains remaining host-attestation gaps. The latest *actual DGX-local* isolated result remains **77/77 at `1283b1a`**. This source has not been run on either actual DGX or independent disposable host. D0 `NOT_GRANTED`; D1–D5 `NOT_RUN`; M1/M2/M3/M4 unchanged; PR #259 Draft/Open/Unmerged, Ready/Merge BLOCKED.


## D0 read-only command environment and protected-socket refusal (2026-10-13)

Source `f4e83d2ae3f17d82c5f7702497138c3431072358` hardens the on-host D0 read-only observer against redirected Git/Systemd/DBus environment selectors; removes unpinned default Docker info/container commands from the allowlist; refuses arbitrary populated Docker environment overrides; and blocks context endpoints inside forbidden production roots or on/under non-root mountpoints. `GIT_OPTIONAL_LOCKS=0` remains enforced. Five new fixture methods confirm refusal before unintended host commands. [GitHub CI #38315552300](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38315552300) **SUCCESS 834/834 full Python, 77/77 existing selected synthetic, 22/22 D0 crosscheck fixtures, ShellCheck/Bash/Python compile/whitespace PASS**.

[Permanent D0 environment and socket-source evidence](../scripts/benchmark/evidence/d0-env-redirection-and-socket-boundaries-20261013.md) records provenance, safety rationale and remaining host-attestation gaps. The **latest actual DGX-local** isolated synthetic result remains **77/77 at `1283b1a`**, not the newer GitHub source. No actual independent disposable host observation or live D0 qualification occurred. `D0_LIVE_ADMISSION=NOT_GRANTED`, `D1_D5=NOT_RUN`, M1/M2/M3/M4 unchanged, and PR #259 Draft/Open/Unmerged with Ready/Merge BLOCKED.


## D0 exact-input digest receipts and offline consistency review (2026-10-13)

At source SHA `e41a34f06887f526d0a7ac7cb605d263c226f8f6`, the strict JSON reader hashes the **same bounded no-symlink file-descriptor bytes it parsed**, the read-only host collector emits `policy_sha256` and `inventory_sha256`, and the new `disposable-d0-receipt-review.py` compares its receipt to the exact supplied policy/inventory JSON. Mismatched files, invalid receipt schema, changed Git SHA and forged admission markers are refused. Consistent input is only `D0_RECEIPT_REVIEW=CONSISTENT_UNTRUSTED`; external attestation and replay freshness remain `NOT_VERIFIED`.

[Source CI #38316973840](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38316973840) **SUCCESS: 845/845 full Python, 77/77 bounded synthetic, Bash/ShellCheck/Python compile/whitespace PASS**. [Permanent fixture evidence](../scripts/benchmark/evidence/d0-receipt-input-binding-ci-20261013.md) and [receipt workflow/limitations](D0-RECEIPT-CHAIN.md) preserve provenance and non-admission semantics. The new 11 tests are **outside** the 77-case bounded DGX synthetic verifier; latest **actual DGX-local** synthetic remains **77/77 at `1283b1a`**. No actual disposable host observation occurred; D0 admission NOT_GRANTED, D1–D5 NOT_RUN, M1/M2/M3/M4 remain unqualified/blocked, PR #259 remains Draft/Open/Unmerged.


## D0 external owner/isolation/restore evidence-chain consistency (2026-10-13)

Source `a52ae7f2985ce0f415134b848b6caeb6aefec348` adds `disposable-d0-external-evidence-review.py`, a strictly offline, read-only and fail-closed review of the previous exact-input D0 receipt and **three separately provided artifacts** for independent-owner consent claims, Docker isolation claims and controlled restore-drill claims. It requires the exact policy, inventory, receipt SHA256, host/daemon identifiers and restore point to match; refused evidence includes missing/overlapping role IDs, altered/missing/empty/symlink proofs, overlapping proof digests, contradictory scopes and forged admission. The artifact contents and claimed reviewer actor IDs are **not authenticated or independently witnessed**; success only reports `STRUCTURALLY_CONSISTENT_UNTRUSTED` and always `D0_ADMISSION=NOT_GRANTED`, `D1_D5=NOT_AUTHORIZED`.

[Exact-source GitHub CI #38317915217](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38317915217) **SUCCESS: 860/860 full Python (15 new external proof methods), 77/77 existing bounded synthetic, Bash/ShellCheck/Python compile/whitespace PASS**. See [permanent evidence](../scripts/benchmark/evidence/d0-external-owner-isolation-restore-evidence-ci-20261013.md) and [external review schema and workflow](D0-EXTERNAL-EVIDENCE-REVIEW.md). The latest **actual DGX-local** fixture acceptance remains `1283b1a` 77/77, not this source; no actual independent disposable host D0 verification or D1–D5 has occurred. M1/M2/M3/M4 and PR #259 Draft/Open/Unmerged gates unchanged.


## DGX staged A/B validation recommendation — 2026-10-13

**Run A now when DGX is quiet**: after review and fast-forward-only Git synchronization to exact successful GitHub SHA, invoke the pre-existing local synthetic verifier, now extended to **134/134** offline fixtures (77 original plus 57 D0). It additionally checks the canonical repository origin and refuses Git environment redirection. After A PASS, B is **real HOME/XDG read-only selected-profile and optional Doctor/status observation**, not an M1 acceptance. **C** D0 admission and destructive D1–D5 belong on a separately owned disposable host only; **D** live H38 on the sole protected DGX remains blocked pending RM/metadata/stability/recovery and explicit approval. Source [CI #38319566009](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38319566009) PASS 863/863 full and 134/134 selected; latest actual DGX remains 77/77 at 1283b1a. [Safe DGX operator instructions](DGX-STAGED-VALIDATION.md); [source evidence](../scripts/benchmark/evidence/dgx-stage-a-expanded-synthetic-ci-20261013.md). D0 NOT_GRANTED, D1–D5 NOT_RUN, M1–M4 unchanged, PR #259 Draft/Open/Unmerged.


## Actual DGX 134/134 PASS and solo-owner test authorization boundary (2026-10-13)

User-supplied terminal evidence establishes **actual local 134/134 bounded synthetic PASS at exact b35d0f3d7840d00c55f4c633813e88ac367c6373** (Bash PASS; ShellCheck SKIPPED_NOT_INSTALLED). The immediately following real-HOME selected-profile snapshot showed a VALID complete OrcaRouter manifest, four transactions IDLE, no stale artifacts, monitor/protection both `1`, Docker container EXITED, service INACTIVE and runtime attestation MISSING. This is **A=PASS and B1=COLLECTED**, not M1 health or H38 acceptance. [Actual operator evidence](../scripts/benchmark/evidence/dgx-local-134-pass-readonly-snapshot-20261013.md).

The sole DGX owner reports testing can occur at any time without disrupting other human users. **Bounded, reversible, owner-approved live runtime tests on this one DGX may be considered after B2 full read-only Doctor and recovery review**; a second physical DGX is not mandatory for every runtime test. This revises the former blanket schedule restriction but does **not** approve deleting resources, assume Docker exclusivity, upgrade independent disposable D0 admission, run destructive D1-D5 on the only host, or launch H38 against the unresolved checkpoint/RM gates. Immediate B2: use the existing read-only lifecycle inspector at the **already checked out b35d0f3**; do not sync Git merely to run it. PR #259 remains Draft/Open/Unmerged; Ready/Merge BLOCKED.
