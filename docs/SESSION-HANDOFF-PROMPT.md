# Session handoff — compact entrypoint

**Updated:** 2026-10-15 KST. **Repository:** https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark

## How to resume (source of truth; no snapshot trust)

This is an **entrypoint**, not an archive. When starting a new conversation, read the latest versions of these canonical files from GitHub, in order:

1. [Project mission and model scope](PROJECT-MISSION-AND-MODEL-SCOPE.md) — permanent goals, full model registry vs candidates.
2. [Current status](CURRENT-STATUS.md) — latest decisions, actual DGX results, blockers, outstanding work; historical dated entries may be superseded.
3. [Architecture](ARCHITECTURE.md), [operations](../OPERATIONS.md), [managed lifecycle acceptance](MANAGED-LIFECYCLE-ACCEPTANCE.md), and [staged DGX validation](DGX-STAGED-VALIDATION.md) — invariants/acceptance.
4. [Scripts and dependency rules](../scripts/README.md) and current implementation/tests — operational APIs and CI rules.
5. [Hybrid plan](HYBRID-BENCH-REBUILD-CYCLE.md), [physical H6 evidence](../scripts/benchmark/evidence/dgx-hybrid-h6-m1-protection-stop-physical-20261014.md) and [evidence index](../scripts/benchmark/evidence/README.md) — only if relevant.
6. [Model-specific reports](model-reports/README.md) and [lychee888 integration](LYCHEE888-WIZARD-INTEGRATION.md) — model-specific proof/gates.

Inspect actual remote branch HEAD, open PRs and their exact-HEAD CI. Never assume a SHA, Draft state or result in an old chat is current. Distinguish GitHub source, DGX local checkout, installed release, Docker/image IDs and checkpoint SHA. GitHub CI and synthetic tests **do not** establish physical DGX READY or stability.

## Current live delta (2026-10-15)

- **Multi-model development:** defer mazinb-first Wizard completion; research lychee888 FP8PLE and `catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed` and incrementally improve reusable Wizard support. Catplusplus is proposed only; do not claim installed/registered. mazinb physical M1 benchmark exists as comparison evidence.
- **Hybrid H6:** first GPU experiment ended via watchdog memory-protection before READY. A complete first 81-shard pass was followed by a second pass; stopped during the second pass. Terminal `KeyboardInterrupt("terminated")` matches shutdown rather than proving independent GPU failure. Watchdog stop confirmed; necessity and RM allocation health unresolved. First benchmark NOT_MEASURED. Perform **read-only static feasibility analysis** before the keep/retire decision.
- **Deletion:** H3–H6 retirement blocked by historical H7/H20 aliases and other Docker mount references. H6 raw evidence only on-host verified (SHA256 7/7), off-host backup NOT_VERIFIED. Do not remove assets, relax watchdog, change managed startup, run new GPU trials, or prune Docker on a diagnostic pretext. Retire only after separate exact-target dependency/evidence review and explicit approval.
- **PR gate:** PR #261 and #259 remain Draft/unmerged unless independently reverified; never ready/merge these without separate explicit authorization. Starting working branch at prior snapshot `feature/wizard-modular-phase1-20261014`; recheck live SHA.

## Permanent working contract

Prefer direct GitHub connector changes for accessible repository tasks: inspect → implement/reuse existing scripts → add tests → commit → verify exact-head Push/PR CI → update canonical docs. Keep immutable dated physical evidence. For physical DGX actions provide safe, bounded commands and STOP conditions; never represent source-only validation as live GPU qualification. Fail closed on EOF/invalid operator input; exact resource identity, previews, no silent destructive defaults, recovery/rollback and ownership protection are mandatory. Avoid duplicated one-off scripts when a maintained script can be extended. Do not assume GitHub access permits host access. Consult the linked canonical docs for expanded rules rather than pasting them here.

## Reusable new-chat prompt

> Continue `kjlee-inlct/qwen3.8-flash-next-dgx-spark` using the **latest GitHub** `docs/SESSION-HANDOFF-PROMPT.md`, `docs/PROJECT-MISSION-AND-MODEL-SCOPE.md` and `docs/CURRENT-STATUS.md`. Follow linked canonical docs and actual evidence; verify remote HEAD/PR/CI first. Work through the next safe step, update permanent docs and tests, and use GitHub connector commits where possible. No unapproved DGX mutation or merging protected PRs. Do not repeat historical handoff logs.

**History:** the previous long-form handoff (including dated historical notices) is preserved in Git history; substantive H6 details and source-of-truth results remain in the linked canonical evidence and status documents. This entrypoint is deliberately concise.
