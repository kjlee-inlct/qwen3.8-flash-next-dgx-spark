# Permanent session rules and handoff interface

This file contains **stable, accepted operating rules** and a document
navigation contract. It must **not** become a chronological log of unfinished
tasks, today's blockers, transient HEADs, or per-session experiment output.
Do not append a new dated "current live delta" section at every handoff.

## Project continuity

- Project: [qwen3.8-flash-next-dgx-spark](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark), on **one** NVIDIA DGX Spark / GB10.
- Product mission: operator-friendly `./install.sh` and `./uninstall.sh` Wizards for install, switch, inspect and safe removal. See [project mission and model scope](PROJECT-MISSION-AND-MODEL-SCOPE.md).
- **Accepted direction:** do not make mazinb-first Wizard completion a prerequisite. Validate model candidates individually while improving the shared Wizard and lifecycle incrementally. Specific pending investigations belong in the **conversation handoff**, not here; accepted changes in model scope belong in the mission document.
- Distinguish candidate, source implementation, registry-installable, DGX READY, inference PASS, measured benchmark and long-term host qualification. None implies the next.
- The full fixed architecture, safety and acceptance rules are maintained in their canonical documents; do not reprint them in this file.

## Authoritative documentation map

Read the latest repository copies, selecting additional documents only when relevant:

| Subject | Permanent authority |
|---|---|
| Objective, model IDs, model-vs-backend scope | [PROJECT-MISSION-AND-MODEL-SCOPE.md](PROJECT-MISSION-AND-MODEL-SCOPE.md) |
| Verified outcomes, dated status record | [CURRENT-STATUS.md](CURRENT-STATUS.md) |
| Architecture and lifecycle semantics | [ARCHITECTURE.md](ARCHITECTURE.md), [MANAGED-LIFECYCLE-ACCEPTANCE.md](MANAGED-LIFECYCLE-ACCEPTANCE.md) |
| Host operations, deletion, rollback | [OPERATIONS.md](../OPERATIONS.md), [DGX-STAGED-VALIDATION.md](DGX-STAGED-VALIDATION.md) |
| Maintained scripts, dependency directions, tests | [scripts/README.md](../scripts/README.md) |
| Hybrid research/runbook and immutable physical proof | [HYBRID-BENCH-REBUILD-CYCLE.md](HYBRID-BENCH-REBUILD-CYCLE.md), [H6 evidence](../scripts/benchmark/evidence/dgx-hybrid-h6-m1-protection-stop-physical-20261014.md), [evidence index](../scripts/benchmark/evidence/README.md) |
| Model-specific evaluations and plans | [model reports](model-reports/README.md), [lychee888 plan](LYCHEE888-WIZARD-INTEGRATION.md), [mazinb R2 staged restore/bench](MAZINB-REINSTALL-R2-WIZARD.md), [catplusplus GB10 gated install/serve/bench](CATPLUSPLUS-SINGLE-GB10-INSTALL-SERVE-BENCH.md), [catplusplus vLLM versus SGLang evidence](CATPLUSPLUS-VLLM-SGLANG-COMPARISON.md) |

Historical evidence remains historical. Where a newer verified result supersedes
an older `NOT_CAPTURED` or `NOT_VERIFIED`, preserve both with provenance; do
not silently rewrite physical history.

## Invariant working rules

1. **Read before action:** check current canonical documents, exact remote
   branch HEAD, PR state and CI. Confirm local DGX checkout, installed
   immutable release, model revision, images and Docker IDs separately.
2. **Act on repository where possible:** use the connected GitHub tools to
   inspect code, implement reusable scripts/tests, commit and verify the
   **exact resulting HEAD** and Push/PR CI. Source-only or CI PASS is never a
   physical DGX PASS. Respect repository layout tests and dependency rules.
3. **Physical DGX boundaries:** no claim of host execution without actual
   operator/tool evidence. Do not start GPU trials, modify watchdog thresholds,
   restart services, change boot behavior, remove model data, prune Docker,
   change swap or alter protected objects without a separate reviewed,
   explicitly authorized procedure. Give bounded commands with STOP criteria.
4. **Fail-closed lifecycle:** preview affected exact resources, verify
   ownership/dependencies/rollback, preserve immutable evidence, and require
   explicit consent for destructive action. EOF/invalid input cannot count as
   affirmative consent. Reuse and extend maintained scripts before creating
   redundant one-offs.
5. **PR safety:** never auto-merge or mark a protected Draft PR ready merely
   because tests pass. Reverify each PR live; honor its documented consent
   boundary (including historical #259/#261 unless explicitly released).
6. **Documentation on substantive completion:** update the relevant canonical
   source when a decision becomes accepted, a test result becomes verified,
   safety constraints change, or a technical conclusion is established.
   Record actual deletion, protected-asset postchecks, data provenance and
   measured recovered space in dated status/evidence documents; link them
   from the stable handoff index rather than pasting chronological logs here.
   Keep Wizard routing screens thin and dedicated lifecycle logic in separate
   testable modules; do not reuse historical exact-ID cleanup scripts as
   generic operations. Avoid copying active task checklists or transient
   discussions into this permanent handoff file.
7. **Independent implementations, Wizard-managed operation:** implement reusable
   inspection, analysis, download, validation and lifecycle capabilities in
   small, independently testable role modules. Keep the terminal Wizard as
   the preferred, discoverable operator-facing control plane for meaningful
   model/host management actions: route to maintained modules, display clear
   preview, state, evidence, errors and cancel/back behavior, and distinguish
   read-only checks from mutations. Do **not** expose every internal helper
   as a menu item or force developer-only debugging, CI or scripted automation
   through the Wizard; direct module execution is appropriate in those cases.
   Separate module tests from Wizard routing/consent tests. Do not make a
   one-off manual command the default operator workflow when a suitable
   Wizard path exists. Update this stable rule here when changed; record
   specific features/results only in their canonical implementation/status docs.
   When a research-only workflow is conclusively retired, remove obsolete
   operator menu routes while preserving its historical source, immutable
   evidence, safeguards and registry retirement status unless a separately
   authorized removal applies. Do not expose dead-end launch/deletion actions
   to ordinary operators after that research lifecycle has closed.

## What belongs in the conversation-to-conversation prompt

Each session handoff message (outside this file) contains only the **live,
unresolved delta**:

- active goal and exact point reached;
- latest verified branch/commit/PR/CI and host identities *as a dated snapshot*;
- new evidence acquired during that session, with links to canonical evidence;
- pending blockers/uncertainties and the next safe concrete action;
- explicitly approved or prohibited actions specific to the live task.

Do not repeat the permanent rules or complete historical experiment log. When
the active task finishes, retire its handoff text; preserve only validated
outcomes and accepted policy in the proper permanent documents.

### Short reusable starter

> Continue the existing GitHub project
> `kjlee-inlct/qwen3.8-flash-next-dgx-spark`. First read the latest
> `docs/SESSION-HANDOFF-PROMPT.md` and its canonical links. Then use
> the **live task handoff pasted below** to resume where work stopped.
> Check actual HEAD/PR/CI and separate GitHub proof from physical DGX evidence.
> Update permanent docs for verified conclusions, not for every transient
> step. Do not perform unapproved host mutation or PR merge.

Append the latest **live task handoff text** only when changing conversations.
This file should rarely need updating after the operating contract stabilizes.
