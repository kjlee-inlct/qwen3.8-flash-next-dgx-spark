# Project-wide uninstall coverage and residual audit

**2026-10-20 status: read-only inventory implemented; complete destructive
uninstall NOT IMPLEMENTED and NOT HOST-QUALIFIED.** This tool never authorizes
deleting any currently protected DGX resource.

## Existing uninstall is not a full project reset

The current uninstall.sh manages the canonical Docker container, installer-owned
runtime service, API-access proxy, optional owned PLE swap and active model/image,
plus cumulative installer-owned assets with --purge-all. It does not claim
ownership lost in older profile switches and must refuse unmanaged or dependent
assets. The plain --dry-run preview does not exercise all mutation preflights.

Named research Docker experiments (including current R2), retained journals and
benchmark evidence, discovered model directories, Docker volumes, shared
Hugging Face caches and externally installed images are not necessarily in
--purge-all. The 2026-10-19 pinned mazinb R2 checkpoint restore did not call the
cumulative installer asset tracker; the presence of its manifest is not proof
that the restore was registered as installer-owned.

## Operator flow

The main Wizard's 2. Uninstall menu has independent actions:

1. Full-project resource inventory (READ ONLY).
2. Existing managed uninstaller (separate confirmation required).

The inventory is implemented in scripts/lifecycle/uninstall-inventory.py.
It checks the strict installation manifest, cumulative ownership registry,
bounded project state/release/model directory entries, exact full-ID project
Docker containers, project-tagged Docker images, project Docker volumes,
project runtime/service/proxy systemd unit files and LoadState/ActiveState,
dedicated PLE swap file and the exact # qwen38-ple-swap /etc/fstab marker.
It reports HF cache as EXCLUDED_SHARED and preserves system Docker/NVIDIA
components, unrelated swap, external apps and Git checkout.

A name, tag or label makes a resource a review *candidate*, never grants
ownership. Invalid state/registry, unreadable directory, Docker/systemd access
failure and scan limits fail closed. Neither model content nor experimental
journals are read. The module never creates, stops, starts, removes, changes
or downloads a Docker/image/service/model/swap.

### Invocation (no host mutation)

Read-only operator inventory:

    python3 -B scripts/lifecycle/uninstall-inventory.py plan

Optional baseline plan in JSON: the operator may redirect the emitted stdout
outside the project/teardown tree, for example:

    python3 -B scripts/lifecycle/uninstall-inventory.py plan --json > "$HOME/qwen38-uninstall-baseline.json"

After a *separately approved* future deletion procedure, inspect residuals
against that exact baseline:

    python3 -B scripts/lifecycle/uninstall-inventory.py verify --baseline "$HOME/qwen38-uninstall-baseline.json"

Use --model-root, --swap-file, --state-home, --data-home, --unit-dir, --fstab-path
and --hf-home to select exact inspection scope. The same inspection scope is
required for baseline and postcheck; mismatches refuse a PASS.

Results: NOT_PERFORMED (plan only), RESIDUALS_PRESENT, INCOMPLETE,
INVALID_BASELINE or PROJECT_SCOPE_NO_RESIDUALS. The last means *only*
no known candidates within the bounded inspected scope, not that the
whole OS has returned to factory condition. Exit 0 is a completed plan or
project-scoped no-residual verification; 2 means incomplete/invalid; 3 means
residuals observed. The audit cannot be used as a deletion token.

## Still missing before complete uninstall can be qualified

1. Exact-ID ownership and dependency records for every new research trial,
   model restore and image. Do not infer historical ownership retroactively.
2. Reusable archive-before-retire exact-ID cleanup independent of historical
   five-container or 17-container one-shot procedures. Verify SHA256 archives
   and preserve experiment/benchmark evidence out of removal scope.
3. Explicit per-category confirmation, final typed owner approval, bounded
   lock and fail-closed mutations, rollback/partial-failure reporting.
4. A distinct, optional shared-cache cleanup with provenance; never blindly
   delete HF cache, Docker engine, drivers, foreign volumes/swap or Git data.
5. Real install → remove → postcheck E2E with failure injection on a disposable
   DGX-compatible host/VM. M2 destructive acceptance remains NOT RUN.
6. Only after that testing, separately approve exact physical DGX removal
   scope, retained evidence, and before/after disk-space receipts.

Current physical DGX cleanup, GPU launch, service changes, model deletions,
swap changes, Docker cleanup, source sync and PR merge remain unauthorized.
