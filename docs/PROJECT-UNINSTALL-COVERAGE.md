# Project-wide uninstall coverage and residual audit

**2026-10-20 status: read-only inventory plus an opt-in guarded whole-project
delete engine are implemented in source; M2 destructive E2E remains NOT
HOST-QUALIFIED.** Neither source completion, plan receipt nor CI tests
authorize deletion on the one protected physical DGX.

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

## Complete removal target contract (owner-confirmed)

**Complete project uninstall means remove, NOT retain, every positively
identified Qwen3.8 project resource.** The default managed uninstall and
historical archive-preservation rules are *not* the full-reset policy.

| Target | Complete uninstall |
|---|---|
| OrcaRouter managed canonical Docker, checkpoint, runtime image | REMOVE |
| mazinb R2 trial #1, #2, #3 Docker IDs and downloaded checkpoint | REMOVE |
| Other project Docker experiments, images, project volumes | REMOVE after exact-ID/reference checks |
| NVIDIA, Hybrid H3/H4/H5/H6 and all project generated model stages | REMOVE with root/ownership verification |
| Dedicated PLE swap and its exact /etc/fstab entry | REMOVE (never normal /swap.img) |
| qwen38 service, proxy socket/service and custom API endpoints | REMOVE |
| Project state, immutable releases, config, journals and retirement archives | REMOVE |
| Locally retained benchmark/forensic materials, including project checkout evidence directories | REMOVE, explicitly including both original and copy |
| Project-specific Hugging Face model cache entries | REMOVE after provider/identity review |
| Shared whole Hugging Face cache, foreign Docker/apps, OS, NVIDIA drivers, system swap | NEVER mass-delete |
| GitHub remote branch/commits/PR history | NOT a local-uninstall target |

The physical owner-provided R2 read-only outputs validate at least these
candidate Docker IDs (do not infer that the set is exhaustive):
- first previous managed OrcaRouter container:
  `f6bfee5a421743758974920064d59c1fb7584cb3a96f83b5c3fafff6acd24`
  (its identity and live status must be independently rechecked);
- first R2 successful API/soak/smoke trial, subsequently exact-ID stopped:
  `82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424`;
- second failed R2:
  `68cd243882bf117dbccdfad577cfdec7a95063ee8f2a96dbe6bcf51cfd8554e7`;
- third failed R2:
  `bee2e3819b7c2fef595357b61ea23934dd8969215a7fe2b957678bbf98eb1dd8`.

Do not hardcode the historical IDs into a reusable deletion routine.
Enumerate the actual current project objects and compare **exact** IDs,
names, image/config fingerprint, stopped/running state, mounts, other-container
references and ownership before enabling deletion. No foreign Docker may be
removed to free an image. No name-only match constitutes deletion authority.

The second and third Docker were reported stopped, exit=137 and
OOMKilled=false; both named journals report
`M1Error: NVIDIA RM memory allocation error`. Their monitor output contained
no `PROTECT stopping` and the kernel RM query returned sudo-authentication
failure. Those facts do not qualify a live uninstall, and no more GPU trial
is needed for cleanup planning.

## Operator flow

The main Wizard's 2. Uninstall menu has independent actions:

1. Full-project resource inventory (READ ONLY).
2. Existing managed uninstaller (separate confirmation required).
3. Post-removal residual verification (READ ONLY; requires a previously saved JSON baseline).

The inventory is implemented in scripts/lifecycle/uninstall-inventory.py.
It checks the strict installation manifest, cumulative ownership registry,
bounded project state/release/model directory entries, exact full-ID project
Docker containers, project-tagged Docker images, project Docker volumes,
project runtime/service/proxy systemd unit files and LoadState/ActiveState,
dedicated PLE swap file and the exact # qwen38-ple-swap /etc/fstab marker.
It excludes the **shared HF cache root**, but separately inventories
project-specific HF model-cache entries. It includes local experimental
journals, external private benchmark archive candidates, and checkout-local
research evidence (which will require a separate safe checkout cleanup stage).
System Docker/NVIDIA components, unrelated swap and external apps stay out
of scope.

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

Use --model-root, --swap-file, --state-home, --data-home, --unit-dir,
--fstab-path, --hf-home, --home-path and --checkout-path to select exact
inspection scope. The same inspection scope is
required for baseline and postcheck; mismatches refuse a PASS.

Results: NOT_PERFORMED (plan only), RESIDUALS_PRESENT, INCOMPLETE,
INVALID_BASELINE or PROJECT_SCOPE_NO_RESIDUALS. The last means *only*
no known candidates within the bounded inspected scope, not that the
whole OS has returned to factory condition. Exit 0 is a completed plan or
project-scoped no-residual verification; 2 means incomplete/invalid; 3 means
residuals observed. The audit cannot be used as a deletion token.

## Integrated exact reset engine (source-only, NOT M2 host-qualified)

The code under scripts/lifecycle/full-project-uninstall.py is distinct
from the older uninstall.sh --purge-all. It implements a two-stage
SHA256-bound plan and an explicit opt-in destructive apply entry point.
Wizard 2. Uninstall now has entries 4 (full plan receipt in HOME),
5 (double-consent exact full removal), and 6 (receipt-bound postcheck).
**The physical DGX has not run any of these new actions.**

PLAN performs bounded read-only inventory of OrcaRouter, mazinb R2,
project trial containers, project-specific Docker images/volumes,
project model roots, dedicated PLE swap, owned systemd units and
local/checkout forensic evidence. It captures exact full Docker IDs,
labels, image IDs, mount sources, file inode/device and a canonical
SHA256. It refuses unknown ownership, unsafe paths, nested symlinks,
nested mounts, incomplete Docker/systemd discovery, stale transitions,
unowned swap/units and Docker assets referenced by other containers.
An old canonical qwen38-flash-next Docker without project labels
must have its exact /model Qwen3.8 project bind-mount.

PLAN must be written to a private file outside all deletion roots.
The wizard uses $HOME/qwen38-full-uninstall-plan.json and refuses
to overwrite an existing receipt. Standalone invocation:

    umask 077
    python3 -B scripts/lifecycle/full-project-uninstall.py plan > "$HOME/qwen38-full-uninstall-plan.json"

Inspect that receipt **before** any destructive action. APPLY requires
the unchanged receipt, its entire sha256 and an independent exact typed
acknowledgement. Its ordering is managed units/proxy, exact Docker ID,
project volumes/images, PLE swap, project model/caches/forensic trees,
project data and state last. No generic prune, force-removal of a
foreign container, /swap.img, or shared HF cache-parent is performed.

    python3 -B scripts/lifecycle/full-project-uninstall.py apply --plan-file "$HOME/qwen38-full-uninstall-plan.json" --plan-sha '<64-digit receipt sha256>' --confirm DELETE_ALL_QWEN38_PROJECT_ASSETS_AND_LOCAL_FORENSICS

That command is shown **for interface documentation only**, not a
recommendation or authorization to execute on the one protected DGX.
Applying is irrevocable: model weights and local forensic history
cannot be recovered without external backup. It can leave partial
cleanup if any later Docker, sudo, swap or filesystem step fails;
never automatically retry without manual inspection and a fresh plan.
The module obtains the shared lifecycle operation.lock first,
revalidates the complete preflight snapshot, and verifies residuals
after file teardown. The separate verify command checks remaining
project-scoped resources and refuses false success on probe failure:

    python3 -B scripts/lifecycle/full-project-uninstall.py verify --plan-file "$HOME/qwen38-full-uninstall-plan.json"

The receipt is intentionally outside the deletion roots, allowing
postcheck after local project state is gone. It contains resource
identifiers, not a copy of benchmark/monitor logs, and should itself
be handled as a private record. Remote GitHub evidence/history is
outside local uninstall scope. Current source unit tests and CI are
not destructive M2 host acceptance.
### 2026-10-20 actual DGX read-only plan preflight: legacy checkout/model

The owner selected Wizard 2 -> 4 and approved **plan creation only**.
The full reset engine refused to build a plan:

    FULL_UNINSTALL=BLOCKED_OR_PARTIAL_REVIEW_REQUIRED
    REASON=resource_status_not_safely_present:model:/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/model

The Wizard did **not** invoke apply and removed the unsuccessful empty
receipt; the following standalone read returned `PLAN_NOT_FOUND`.
The output is consistent with an `UNSAFE_SYMLINK` status for the
legacy `checkout/model` candidate (though the actual link type and
target still require a DGX `ls -ld/readlink/stat` receipt). The old
engine treated all non-`PRESENT` model candidates as unplannable.

Source-only corrective behavior: the engine now permits **only the
exact `checkout/model` symlink** as a separate
`legacy-model-link` plan resource. It records the raw readlink
text, resolved lexical destination, mode/device/inode; it never
follows the link for deletion. If the destination exists, it must
be an actual project-named model directory underneath an explicitly
configured model root and must **also be independently selected
for deletion as a model target**. External, redirected, untracked
or changed live targets fail closed. A true dangling symlink may be
unlinked as a link. Other symlinked model candidates remain blocked.
The synthetic tests exercise valid link-only unlink, preservation
of a foreign target, omitted model coverage and target drift.

**Subsequent ACTUAL DGX read-only check (2026-10-20):** owner printed
`model` as a symbolic link (device `66306`, inode `12097904`)
with absolute link text pointing to
`/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models/qwen3.8-flash-next-orcarouter`.
The physically checked-out HEAD was
`b0ef37f9b756a86cc3670691e98a0b0798984d51`, with a clean
worktree and the expected feature branch. The later GitHub remote
source containing the symlink remedy was ahead; no local sync was
reported. The destination directory's actual existence/type, model
registry ownership and its fingerprint remain **NOT_OBSERVED**; the
link's own `stat` cannot establish them. See `CURRENT-STATUS.md`
for separate remote HEAD and exact-SHA CI evidence. Even if plan
creation succeeds after a separately reviewed source update,
**destructive M2 remains NOT_QUALIFIED**, and menu 5 is not authorized.

### Actual DGX OrcaRouter model association is not deletion ownership (2026-10-20)

Subsequent owner-provided **read-only DGX** evidence confirms the
`checkout/model` link resolves to an **existing, real**
`checkout/models/qwen3.8-flash-next-orcarouter` directory (target
device/inode `66306/12061870`). The manifest names this directory as
`MODEL_DIR` but has `MODEL_OWNED=0`. Exactly one model registry
entry matches the directory, and it has `owned=False`,
`state=ready`, and marker fingerprint
`3c1cb3a9082801d23c4d7cd14bfe3f30cba900b43fd32d3619e59328fcbd6389`.
The `.qwen38-model-manifest.json` content SHA256 matches this value.
The manifest also sets `VLLM_IMAGE=vllm-skinny-tp1:v1` and
`IMAGE_OWNED=0`; its *registry image entry and live Docker image
ID were not inspected* in this evidence.

This establishes a strongly identified **project-associated but not
installer-owned** model, not proof of independent exclusive ownership.
Do not change the manifest flags, forge registry ownership, or delete
the model solely because the marker hash matches. Under the source-only
positive-ownership guard, this present `UNVERIFIED` model is expected
to block the complete plan; an updated physical plan has **not** been
attempted. The next safe stage is read-only model-marker provenance,
Docker exact image ID/labels and reference inspection, plus a full
candidate inventory. Evaluate a distinct, evidence-bound
project-exclusive full-reset authority path only after the records
support it, with separate approval, synthetic foreign-data regression
tests and disposable E2E. The declared complete removal scope must
not be weakened to `--purge-all` just because old assets carry
`owned=False`. See `CURRENT-STATUS.md` for the physical source,
local checkout SHA, and the prior symlink identity details.

### 2026-10-20 actual DGX full inventory — source-only qualification gaps

The owner ran the **read-only** `uninstall-inventory.py plan` against the
physical DGX. It finished with no reported `INVENTORY_ISSUE`, enumerating
**eight** project-associated full-ID Docker container candidates,
**seven present UNVERIFIED Docker images**, **two present UNVERIFIED
model directories**, the `checkout/model` symlink, three dedicated
runtime cache directories, project state/releases/forensic artifacts, and
the `INSTALLER_OWNED` project-specific PLE swap with fstab marker.
The owner also observed `current` and `previous` inside the data root
as `release: UNSAFE_SYMLINK`; these are normal managed release
pointer candidates, not model paths. Shared HF and FlashInfer root
caches remain excluded.

The seven image tags are the present `vllm-skinny-tp1:v1`,
`vllm-orcarouter-v029:v1`, the H38 decoder-scope image and the
R25/R26/R27/R28 marker images. The OrcaRouter legacy image's
live exact SHA256 matches the `owned=False`/ready registry entry
(`sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`),
and two stopped project-named containers reference it
(`qwen38-ab-legacy` Exited 137 and `qwen38-flash-next` Exited 0).
This is immutable identity agreement and dependency evidence,
**not proof of exclusive ownership**. Four separately recorded
owned/claimed H9–H12 image entries with empty fingerprints are
not shown as present in the Docker inventory. See `CURRENT-STATUS.md`
for the exact eight IDs, seven tags, status provenance and limits.

**Second source-only issue and fix:** previously the full-reset scan
could reject both managed `release: UNSAFE_SYMLINK` entries before
arriving at the `data-root` owned removal boundary. The engine now
recognizes **only** `data-root/current` and `data-root/previous`
as `release-link` receipts. It captures the raw pointer text and
lstat device/inode/mode, requires lexical destination below the
project data `releases/` root, rejects external/intermediate symlink
redirection and refuses apply on pointer identity drift. These links
are removed only as entries when the separately validated project
data-root is torn down; the engine does not follow the links.
Synthetic tests cover accepted in-root current/previous pointers,
missing historical release targets, non-project pointers and
concurrent pointer drift. Other unexpected symlinks remain blocked.

This **does not** bypass the missing positive ownership of the two
model directories or seven image tags, does not prove Docker
container label/mount provenance, and is **not** destructive M2
qualification. Do not run menu 5. Before complete deletion can be
approved, design the explicitly evidence-bound historical ownership
policy with foreign-data preservation and disposable-host tests.

### Name-prefix ownership gap — SOURCE_ONLY fail-closed guard (2026-10-20)

The inventory continues to discover `vllm-*`/`qwen38-*` image
tags, `qwen3.8-*`/`qwen38-*` model directories and
project-like Hugging Face hub cache entries as **UNVERIFIED** candidates.
A matching name, an unused Docker image, or a directory contained in a
model root is **not** proof of project ownership.

The full-reset engine now requires `INSTALLER_OWNED` provenance on every
**present model, image and model-cache candidate** before including it in
the SHA256 deletion receipt. Currently the manifest's owned flags and
the cumulative registry's owned entries provide this attribution for
models and images. A `model-cache` candidate is not yet positively
attributed by the read-only inventory and therefore blocks the full
plan rather than being silently removed or omitted. The exact
`checkout/model` symlink exception remains link-entry-only; a live
linked model must itself be selected under the same positive ownership
guard. Unverified assets now fail with
`candidate_ownership_not_proven:<kind>:<locator>` (up to 12 candidate
identities, followed by `additional_unverified=N` if there are more)
*before* Docker image identity inspection or any destructive apply.
The separate per-candidate ownership check remains a second fail-closed
line of defense. The Wizard surfaces this read-only blocking reason
without generating a valid reset receipt.

Where a cumulative registry record exists, the plan now also refuses
a recorded image if its *current exact Docker image ID* differs from
the saved `ready` fingerprint, and refuses a recorded model if the
managed model-manifest SHA256 has changed, is missing, or the registry
record is not fingerprint-ready. Explicit registry `owned=false`
conflicting with an owned manifest flag also blocks. These checks
reuse the stored immutable provenance; an active manifest without a
matching cumulative record remains a separate historical case
requiring review before host qualification.

Synthetic tests cover similarly named unrelated model directories,
an unused `vllm-*` foreign image, matching-prefix cache entries,
positive recorded/manifest attribution, image ID drift and model
marker drift. These are SOURCE_ONLY regression checks, not evidence
of DGX ownership or complete removable inventory.

**Still blocked:** research-generated or old assets without positive
manifest/registry provenance, shared-root model-cache entries and
historical image tag-to-exact-ID provenance must be individually
reconciled using read-only evidence. Do not blindly mark candidates
`owned=true`, relabel images or fabricate ownership records to bypass
the guard. A future reviewed exact-ID and filesystem-fingerprint
allowlist mechanism may cover proven historical project assets, but
requires explicit owner approval, independent source tests, shared
dependency checks and actual DGX evidence. Until then, failure to
generate the complete plan is a correct safety result, not a reason
to skip unknown project assets or execute menu 5.

## Qualification and recovery work still missing before host use

1. Exact-ID ownership and dependency records for every new research trial,
   model restore and image. Do not infer historical ownership retroactively.
2. Reusable exact-ID experimental-Docker removal independent of historical
   five-container or 17-container one-shot procedures. Existing forensic
   evidence and prior archives must **also be removed**, not silently retained;
   an optional externally retained backup requires a separate explicit choice.
3. The SHA-bound plan, typed owner approval, shared operation lock and
   fail-closed mutation path exist in source. Still required: per-category
   review UX, completed cancellation/interruption recovery, independent
   rollback/partial-failure evidence and disposable-host qualification.
4. Remove project-specific HF cache and repo-local research evidence without
   wiping the shared cache parent or third-party data; a separately approved
   local Git checkout removal is required for a literally empty project tree.
   Never purge remote GitHub history or unrelated local Git projects.
5. Real install → remove → postcheck E2E with failure injection on a disposable
   DGX-compatible host/VM. M2 destructive acceptance remains NOT RUN.
6. Only after that testing, separately approve exact physical DGX removal
   scope, including irreversible local forensic deletion and before/after
   disk-space receipts. No default retention of R2/OrcaRouter materials.

Current physical DGX cleanup, GPU launch, service changes, model deletions,
swap changes, Docker cleanup, source sync and PR merge remain unauthorized.
