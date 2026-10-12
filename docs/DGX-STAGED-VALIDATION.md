# DGX staged validation — operator runbook (2026-10-13)

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
