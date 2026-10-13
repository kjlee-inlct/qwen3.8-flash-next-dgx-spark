# DGX staged validation — operator runbook (2026-10-13)

## Physical S3 reference check completed without model start (2026-10-13)

[Scoped ACTUAL_DGX S3 evidence](../scripts/benchmark/evidence/dgx-hybrid-runtime-references-readonly-20261013.md) at source `d14915549667e196356b8511526f9bfd4db42cd6`: `S3_REFERENCE_SURVEY=COLLECTED_READ_ONLY`, 0 unmapped indexed references, all 81 H6 index shards via known virtual ancestor aliases. No payload reading, benchmark, Docker/container startup or deletion. Source review confirms the H6 ancestor :ro mounts declared in `serve.sh` but does not verify live Docker mount realization. S4 all symlink targets + physical FS characteristics is the next non-mutating review. Historical S2/S3 pending text below must not override this newer dated scope.


## S2 physical host allocation-block audit PASS (2026-10-13)

At exact source `14c67135f94b3c507a90c3a0702c83b9f3bfcda7`, actual DGX operator output returned **`RECLAIM_BLOCK_ACCOUNTING=COLLECTED_READ_ONLY`**. [Evidence](../scripts/benchmark/evidence/dgx-hybrid-block-accounting-readonly-20261013.md): six model directories 515623661568 allocated bytes; H3+H4 145557426176 bytes, zero observed hardlink file entries and 319 symlinks. Next **S3 read-only container-alias/safetensors index dependency** survey is not run. No model was started, no benchmark was measured, no file/Docker asset was removed. Never claim real reclaimable capacity from `du` alone. This newer scoped S2 result supersedes previous S2 `NOT_RUN` labels but does not change M1/M2/M3/M4/D0 protections.


> **Decision:** A is appropriate now on the sole DGX; B follows A; independent disposable-host D0 and D1–D5 must never run on the sole DGX; H38 live remains blocked.

## Evidence and distinction

- Historical **actual DGX** bounded synthetic: 77/77 PASS at `1283b1a9252f1ff53d51659049ca42f9449e5ccd` (2026-10-12).
- Latest **GitHub-only** source: `3aae0bb7de518704dd7b0c20af361105fa409905`, [CI #38319566009](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38319566009), 863/863 full Python + 134/134 bounded synthetic PASS.
- New bounded selection is 77 original fixture cases plus 57 **fake/offline D0** cases (10 policy, 22 fake-host crosscheck, 10 receipt, 15 external artifact). None authorizes or executes a real host D0 check.
- A passing fixture run does not qualify M1 health, M2 destructive operations, M3 actual all-pairs or M4 H38.

## A. At the next quiet DGX opportunity — exact-SHA fixtures

Review any local edits first. Repository synchronization is an **explicit operator action**, not done by the verifier. Never reset, clean, force-pull or auto-stash local work. Managed releases and protected runtime must remain unchanged.

```bash
cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark
git status --short
# STOP if any existing work needs preserving.
git fetch --prune origin
git switch feat/h38-managed-integration
git pull --ff-only origin feat/h38-managed-integration
git status --short
git rev-parse HEAD
git remote get-url origin
```

Only continue when this **exact final 40-character SHA** has a completed SUCCESS GitHub CI and the worktree is clean. Do not copy a historic SHA from this page after later commits:

```bash
TARGET='<exact-full-successful-GitHub-HEAD>'
test "$(git rev-parse HEAD)" = "$TARGET"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
bash scripts/lifecycle/verify-synthetic.sh "$TARGET"
```

Accept A only with the canonical Origin marker, exact target SHA, `LOCAL_SYNTHETIC_RESULT=PASS` and **134/134 selected fixtures**; record ShellCheck as PASS or SKIPPED_NOT_INSTALLED. The script uses a disposable HOME/XDG/TMPDIR and PATH-deny stubs, **not** a privileged OS sandbox. It may write/remove files under its temporary sandbox only. No Docker/model/systemd start, uninstall, swap or monitor-protection change is part of A. Preserve sanitized evidence outside the checkout.

## B. After A PASS — read-only DGX observation

Use the **real operator HOME/XDG** (not the temporary fixture HOME). Start with the compact selected-profile snapshot:

```bash
python3 scripts/lifecycle/inspect-selected-profile.py
```

Check manifest/phase, pending transactions, artifacts, Docker status, service state, attestation and memory protection. Selected profile is configuration intent, not the actually served API identity. Unknown or mismatched values are **STOP/PARTIAL**, not an invitation to repair. If the previous container is stopped, leave it stopped.

Only when the operator accepts additional **read-only** Doctor and host-status probes:

```bash
QWEN38_LIFECYCLE_AUDIT_TARGET_SHA="$TARGET" \
  bash scripts/lifecycle/inspect-readonly-lifecycle.sh
```

The exit code only indicates diagnostics collection, not M1 qualification or H38 readiness. Do not auto-recover, start a service, alter swap or relax monitor thresholds.

## C. D0 and D1–D5 — independent disposable host only

Independent owner identity and permission, exclusivity of Docker daemon/volumes/users/credentials and externally witnessed test-data restore remain **NOT_VERIFIED**. Offline D0 receipt and artifact checks report structurally consistent **UNTRUSTED** data, not D0 approval. D1–D5 destructive E2E and actual M3 profile-pair E2E require a separately owned disposable machine, independently verified D0 and separate explicit authorization. **Never use the sole protected DGX as this disposable host.**

## D. H38 DGX live run — blocked pending prerequisites

Past H38 attempts encountered monitor-protected stops and strict RM memory errors. Checkpoint metadata/order remains FAIL and host stability INCONCLUSIVE. Do not schedule H38 live until independent M1/recovery and isolation prerequisites, specific RM hypothesis/stop criteria, immutable runtime/metadata verification, unchanged protections and explicit operator-approved maintenance window are demonstrated. A/B SUCCESS alone does not authorize D.

## Status before new operator logs

```text
LAST_ACTUAL_DGX_SYNTHETIC=PASS_77_AT_1283B1A
NEW_134_CASE_DGX_RUN=NOT_RUN
CURRENT_HEAD_REAL_DGX_READONLY=NOT_RUN
INDEPENDENT_D0_ADMISSION=NOT_GRANTED
D1_D5=NOT_RUN
M1=NOT_QUALIFIED
M2=NOT_RUN
M3=NOT_QUALIFIED
M4=BLOCKED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
HOST_STABILITY=INCONCLUSIVE
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN_UNMERGED
READY_FOR_REVIEW=BLOCKED
MERGE=BLOCKED
```

Update each status only from scoped evidence at the exact source SHA; this document itself grants no runtime authorization.


## Actual DGX 134/134 PASS and solo-owner test authorization boundary (2026-10-13)

User-supplied terminal evidence establishes **actual local 134/134 bounded synthetic PASS at exact b35d0f3d7840d00c55f4c633813e88ac367c6373** (Bash PASS; ShellCheck SKIPPED_NOT_INSTALLED). The immediately following real-HOME selected-profile snapshot showed a VALID complete OrcaRouter manifest, four transactions IDLE, no stale artifacts, monitor/protection both `1`, Docker container EXITED, service INACTIVE and runtime attestation MISSING. This is **A=PASS and B1=COLLECTED**, not M1 health or H38 acceptance. [Actual operator evidence](../scripts/benchmark/evidence/dgx-local-134-pass-readonly-snapshot-20261013.md).

The sole DGX owner reports testing can occur at any time without disrupting other human users. **Bounded, reversible, owner-approved live runtime tests on this one DGX may be considered after B2 full read-only Doctor and recovery review**; a second physical DGX is not mandatory for every runtime test. This revises the former blanket schedule restriction but does **not** approve deleting resources, assume Docker exclusivity, upgrade independent disposable D0 admission, run destructive D1-D5 on the only host, or launch H38 against the unresolved checkpoint/RM gates. Immediate B2: use the existing read-only lifecycle inspector at the **already checked out b35d0f3**; do not sync Git merely to run it. PR #259 remains Draft/Open/Unmerged; Ready/Merge BLOCKED.

### Risk-tier clarification

- **Stage A**: DONE on DGX, 134/134 fixture PASS at b35d0f3.
- **Stage B1**: DONE, compact real-host profile snapshot; not health-qualified. **B2** full read-only Doctor is next.
- **Owner-scoped reversible tests**: may use the actual solo-owned DGX after B2 checks, saved baseline, unchanged memory protection, explicit stop and rollback criteria; any downtime is acceptable to the owner. This is not D0 admission.
- **Destructive fresh-install / purge / true D1-D5**: demand independent disposable semantics or demonstrably restorable separate data/release state and distinct explicit authorization. The present host is not independently disposable simply because the owner is alone.
- **Live H38**: remains blocked by checkpoint metadata/order FAIL and historical strict RM/monitor-stop evidence until a bounded recovery/stop plan and host stability prerequisites are established.


## Actual DGX B2 collected — partial Doctor, not live qualification (2026-10-13)

Exact operator checkout `b35d0f3d7840d00c55f4c633813e88ac367c6373` completed the full read-only lifecycle inspection. **Seven sections returned rc=0; Doctor returned rc=1 (5 FAIL, 2 WARN)** and the aggregate reported `PARTIAL_CHECK_FAILURE`. The Manifest, immutable releases, ownership registry, four idle transaction states, 18 referenced model shards, active monitor/protection configuration, and host reserves passed. The inactive/EXITED managed runtime had no health endpoint, matching live attestation, monitor PID or published running port. The legacy-image and inactive-service warnings remain. [Permanent scoped B2 operator evidence](../scripts/benchmark/evidence/dgx-b2-readonly-lifecycle-doctor-partial-20261013.md).

**Gate updates:** `A=PASS_134` (earlier), `B1=COLLECTED` (earlier), `B2=COLLECTED_PARTIAL` (new); `M1=NOT_QUALIFIED`, `M2=NOT_RUN`, `M3=NOT_QUALIFIED`, `M4=BLOCKED`, `D0=NOT_GRANTED`, `D1-D5=NOT_RUN`. No model or GPU was launched and no service was restarted during B2. This later observation supersedes only the B2 `NOT_RUN` labels above; historical runbook text is retained.

### Next: bound a reversible legacy OrcaRouter baseline before launching

Use the existing immutable-service operational flow and historical October 7 protected-stop evidence; **do not** force-start the old Docker container or run `--refresh-profile-defaults` to make Doctor green. Before authorizing a live trial, establish (1) exact installed `current` release/manifest/service unit lineage and an unchanged `vllm-skinny-tp1:v1` legacy identity, (2) no pending or stale transactions/stop or adoption markers, (3) unchanged monitor protection and adequate non-CMA/swap/disk reserves, (4) bounded kernel RM and monitor log capture, (5) a known service stop/recovery boundary that preserves model, image, release and rollback artifacts. A successful start must independently show `/health`, expected `/v1/models`, container identity and runtime-commit attestation, then remain free of strict-RM failure/protected stop for a recorded observation window. Failure or protection stop preserves its evidence and remains NOT_QUALIFIED. The operator can test at any time as sole human user, but destructive cleanup is not approved and H38 remains separately blocked.


## Follow-up physical DGX immutable-release metadata — incomplete pager-limited collection (2026-10-13)

At DGX source `b35d0f3`, immutable `current` was `ff67bab3` and `previous` was `a8aeca47`. `INSTALL_ROOT` still pointed to the mutable source checkout. This is a **different role** from the service's immutable `current` runtime root; installed `ff67bab3` release-update code explicitly supplies `--runtime-root current` to the service installer. Do not treat `INSTALL_ROOT != current` as drift on its own. The partial unit showed the expected immutable `ExecStart` plus an older direct Docker `ExecStop`, also confirmed by the exact installed-release service generator. The unit's legacy stop semantics differ from the newer feature-branch attested helper and should inform later lifecycle safety review.

The operator's `systemctl show` entered a pager (`lines 1-6/6 (END)`), so the state markers and final sentinel were **not observed**. [Actual limited evidence](../scripts/benchmark/evidence/dgx-b3-release-path-and-systemd-partial-20261013.md). Prefer the repository's already available `scripts/lifecycle/inspect-readonly-runtime-offline.sh` read-only collector (its service query has `--no-pager`) rather than another ad hoc equality gate. Explicitly verify the installed release source before interpreting systemd behavior. No restart, attestation creation, metadata rewrite, forced recovery, H38 launch, or acceptance gate promotion is authorized by this metadata.


## Actual DGX B3 complete — stopped runtime/offline service metadata (2026-10-13)

Following the pager-limited attempt, the operator reran the existing exact-SHA
`scripts/lifecycle/inspect-readonly-runtime-offline.sh` at `b35d0f3`.
All three collector probes completed with rc=0 and final
`MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY` and
`IMMUTABLE_SERVICE_INSPECTION=COLLECTED_READ_ONLY`. Docker retained
predecessor: exited, exit 0, OOMKilled=false, declared loopback
`127.0.0.1:8888`, no runtime port map while exited. Systemd:
loaded / inactive / dead / Result=success; immutable `current`
ExecStart and legacy name-based Docker ExecStop, with restart-on-failure.
All eight inspected adoption/stop/commit/monitor/transition markers absent.
[Permanent evidence](../scripts/benchmark/evidence/dgx-b3-readonly-runtime-unit-complete-20261013.md).

**This supersedes the prior B3 PARTIAL_READONLY observation, not B2 Doctor
5 FAIL / 2 WARN.** The absence of a live attestation, live monitor
or health service remains expected in this stopped state and M1 is **not**
qualified by these metadata reads. Source-level inspection of installed
immutable release `ff67bab3` reveals ordinary rollback/recover branches
can restart the preserved predecessor, whereas memory-protection abort
deliberately leaves it stopped; service ExecStop is a legacy direct Docker
command. Consequently, no generic manual `docker start` or blind
`sudo systemctl restart` is the next automatically authorized step.
The next **source-only planning task** is to specify and verify the exact
preflight, container identity, reversible test boundary, monitor+strict-RM
STOP criteria, and recovery plan for a future **legacy OrcaRouter M1** test.
Protect H38/M4 blocking gates unchanged.

For a new chat or future session, start with
[the reusable handoff prompt skeleton](SESSION-HANDOFF-PROMPT.md), then
re-read this runbook, the current status and freshly queried PR/CI state.


## Actual DGX B4 — M1 pre-start inventory collected, live decision not yet promoted (2026-10-13)

Operator executed a bounded read-only pre-start command at clean checkout
`b35d0f3`, checked immutable release `ff67bab3` and the canonical
OrcaRouter `vllm-skinny-tp1:v1` image/retained container identity,
`MONITOR_PROTECT=1`, `MONITOR_ENABLED=1`, and absence of the rollback
container. The retained Docker ID `f6bfee5a4217...` was exited (exit0,
OOMKilled=false), systemd was inactive/dead; MemAvailable 118.2 GiB,
SwapFree 143.1 GiB; `/swap-ple.img` was active alongside `/swap.img`.
The `M1_PRESTART_READONLY=COLLECTED` marker confirms collection only.
[Actual B4 operator log and source-level hazard analysis](../scripts/benchmark/evidence/dgx-b4-m1-prestart-readonly-20261013.md).

**Reversibility gate**: the installed old-release transaction replaces the
canonical container and permanently removes the rollback predecessor on
successful commit; the old container ID is **not preserved** by managed
success. Normal rollback/recover may also actively restart a stopped
predecessor. A general `systemctl restart` therefore crosses a topology
change/identity boundary and is NOT an automatically safe next command.
Clarify whether exact old-container preservation is required before any
owner-scoped start. Missing checks include `SWAP_FILE` Manifest match,
current transaction/lock and port exclusivity, last-mile model identity
and disk/host headroom, and strict RM/kernel monitoring/stopping plan.
The installed legacy monitor's source lacks the earlier H38 candidate
swap-growth predicate; do not conflate those versions. No H38 model
rerun, no protection relaxation, and no gate promotion from B4.


## A5 — run wizard previews now on the actual DGX

[Exact-SHA, clean-worktree, real-HOME **dry-run only** operator command
and acceptance](DGX-WIZARD-A5-READONLY.md). This uses a detached source
worktree to avoid altering the previously installed release or current
operator source checkout. It is intended to run immediately once the
corresponding GitHub CI has succeeded. It does not start models, restart
systemd, remove resources, or promote M1/M2/M3/M4.


## A5 physical execution and lychee888 metadata result — PASS (2026-10-13)

Operator returned A5 `PREVIEW_AND_FIXTURES_PASS` with exact
`f2674f0` checkout and unchanged hashes; 14/14 command rc0 and
60/60 fixture tests. The same operator also returned
`lychee888` `INDEX_STRUCTURE_PASS_METADATA_ONLY` from actual
Hub revision `1b3c3cedc14fb3bee4294dea5e3515af74b8268a`.
[Scoped evidence](../scripts/benchmark/evidence/dgx-a5-wizard-and-lychee-l0-result-20261013.md).
**A5=ACTUAL_DGX_DRY_RUN_PASS; L0_INDEX_JSON=PASS**.
Earlier run instructions' `A5_NOT_RUN` text represents their
publication-time state only. Next B5 is a version-matched,
non-mutating preflight and preservation-decision gate for the
stopped legacy OrcaRouter service. No live model test has yet
been attempted or authorized by this result.


## B5 legacy OrcaRouter prestart — read-only actual DGX next step

[Exact identity, source SHA and Docker predecessor preservation boundary](DGX-LEGACY-M1-B5-PRESTART.md). The B5 collector contains no service start, rollback or container modification. A read-only PASS is **not permission** to run M1. Previous A5 and lychee888 L0 remain PASS, H38 blocked.
