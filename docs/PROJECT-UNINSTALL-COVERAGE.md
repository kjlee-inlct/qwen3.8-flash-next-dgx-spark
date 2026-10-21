### Lost original receipts: separate fresh eight-root reauthorization (2026-10-21)

Physical DGX evidence on 2026-10-21 proves that the formerly validated
29-target canonical and original plan JSONs are BOTH missing from
`/home/inlc`. Cause unknown. No legitimate attempt to reconstruct
one of their historical SHA256s is possible from saved summary counts
and terminal output. The old `partial-uninstall-recovery.py audit`
therefore fails closed before deletion. This does **not** reverse
the operator's intent to remove the last 8 dedicated directories, but
the prior receipts are no longer valid executable authorization.

The separately maintained exceptional tool
`scripts/lifecycle/fresh-residual-recovery.py` supports
`snapshot` (create-only fresh receipt),
`audit --sha <fresh_sha>` and an independently approved
`apply --sha <fresh_sha> --confirm
DELETE_ONLY_EIGHT_FRESHLY_REAUTHORIZED_QWEN38_ROOTS`.
All actions use precisely
`/home/inlc/qwen38-residual-recovery-v2.json`;
the `snapshot` creates it once at 0600 using O_EXCL/O_NOFOLLOW
outside every deletion root. It checks exact home/checkout,
three dedicated caches, three evidence roots, project-only
state and data roots, stable directory dev/ino/mode,
no unrelated mounts/symlink traversals, absence of installed
project Docker/model/PLE swap, and all three independently
observed external Docker container IDs with fresh no-conflict
reference audit. `audit` repeats every check.
`apply` accepts **only** the new cryptographically bound
plan + exact user approval; it cannot invoke Docker,
model deletion, swapoff or entire Git checkout removal.
Its recursive cleanup is fd-relative/O_NOFOLLOW under root
for the previously blocked root-owned generated cache files.
Any unexpected resource/identity/mount reappearance stops.

The new receipt is NOT a recreation of the old lost receipt.
Do not send legacy `5248...` or `b38c...` as the
new plan SHA. Before execution, require current exact Git HEAD,
clean fast-forward and Push+PR CI PASS; physical snapshot,
second independent read-only audit and owner authorization
are still unqualified until operator outputs establish them.
Postcheck with both legacy full reset and inventory verifiers
must be adapted because their original receipt inputs are
also missing; the new helper does a fresh project-scope
`verify_removed` using its now-approved scope after apply,
with additional independent inventory plan/read-only
swap/Docker/shared-cache checks. Remaining checkout and
external review JSONs require a separately reviewed final step.


### Partial destructive reset recovery after verified project-owned root permission failure (2026-10-21)

A physically attempted exact owner-approved Qwen3.8 reset **partially
completed**: project Docker (8), project image tags (7),
both model directories, and the PLE swap/fstab marker were
independently observed absent; the regular `/swap.img` and
three unrelated Docker containers survived. `df -h /`
reported 626G used before vs 151G after (~475G freed,
rounded). The original `apply` failed deleting the
project-specific `~/.cache/flashinfer-v029` because root-owned
nested directories could not be unlinked by `inlc`.

Dedicated helper:
`scripts/lifecycle/partial-uninstall-recovery.py audit|apply`.
Its accepted source is the **original validated 29-target,
9-owner-exception SHA256 receipt**, not an altered partial
plan and not the original `apply` command. It enumerates only
3 project-only caches, 3 individually approved research
forensics paths, the project-only `state-root` and
`data-root`. State children (`install.env`, asset registry,
historical evidence, operation lock) and data release links
are covered by their single root, not independently recursive
path names. The helper checks exact project home/checkout
layout; receipt/owner review; exact permitted resource kinds,
counts and absolute names; original directory dev/ino/mode;
existing operation lock; independent current inventory for
unexpected Docker/image/model/systemd/swap reappearance;
shared roots and mountpoints; directory symlinks and nested
cross-device mounts. `audit` never mutates. `apply` requires
root and an additional exact approval
`DELETE_ONLY_VERIFIED_REMAINING_QWEN38_LOCAL_ROOTS`.
The remover operates with no-follow, directory-fd-relative
directory walks and unlinks symlinks *as links only*.
Do **not** run broad root `chmod`/`chown`, Docker prune,
`rm -rf ~/.cache`, or the stale 29-target `apply`.

The helper is an exceptional, source/CI-gated partial
recovery, not a generic Wizard command. **Physical-host
recovery has not yet run; complete deletion remains unverified.**
After recovery, read-only full engine `verify`, independent
inventory `verify`, regular swap, foreign Docker and disk
checks are required. The Git checkout itself and the three
saved owner/inventory/receipt JSONs are **not** handled by
this helper: they are a separate owner-requested final
cleanup only after GitHub evidence preservation and residual
postcheck. Repo history and unrelated host resources are
outside local deletion scope.


# Project-wide uninstall coverage and residual audit

**2026-10-20 status: read-only inventory plus an opt-in guarded whole-project
delete engine are implemented in source; M2 destructive E2E remains NOT
HOST-QUALIFIED.** Neither source completion, plan receipt nor CI tests
authorize deletion on the one protected physical DGX.

### 2026-10-21 owner-requested exact-identity reset exception — SOURCE IMPLEMENTATION ONLY

The operator has explicitly requested *total Qwen3.8 project-local
removal*, including known `owned=False`/`UNVERIFIED` historical
models and images, **without deleting foreign resources or shared
cache roots**. A new opt-in source extension of
`scripts/lifecycle/full-project-uninstall.py` accepts **both**
`--owner-exception-file` and `--baseline-inventory` for `plan`
and `apply` only. Legacy/default plan with no exception stays
fail-closed on `candidate_ownership_not_proven`; old ownership
records and `install.env` flags are **not** modified or promoted.

The operator has supplied a saved **actual DGX** read-only inventory
SHA256 `1a5892edff4cccf9ff662467cfda460608e9404bfef5d47bfbadcecdafa1d863`
(`schema=1`, `mode=READ_ONLY_PROJECT_SCOPE`, zero issues).
It lists **8** containers, **7** unverified Docker image tags,
**2** present unverified real model roots, one separate checkout/model
symlink, **3** dedicated runtime caches, **4** forensic candidates,
dedicated owned PLE swap, project state/data and releases. No
`model-cache` candidates are present; one shared `hf-cache` and
one shared FlashInfer runtime-cache parent remain excluded.
The review output, not the raw JSON bytes or its filesystem metadata,
was pasted into chat. The subsequent source changes are **not
physical-host validation** and the owner has not yet run this engine.

#### Exception contract

Exception JSON must contain **exactly**
`{"schema":1,"inventory_sha256":"<64 lowercase hex>","entries":[...]}`.
Every entry is exactly
`{"kind":"model|image","locator":"<exact path or Docker tag>","fingerprint":"<marker SHA256 hex for model; full sha256: image ID for image>"}`.
The CLI rejects unknown keys, duplicate records, noncanonical
fingerprints, model-cache exceptions and more than 64 entries.
Both input files must be regular files outside deletion subtrees;
the inventory SHA256 must match its bytes, issue list must be empty,
and inventory scope (including **the passed `--model-root`**) must
exactly match the engine's scan. The fresh scan must enumerate
**exactly the same** resource rows as the baseline; every present
unverified model/image must have one exact exception entry, with
no extra exceptions and no new unknown cache candidate.

Before a receipt can be issued, the engine runs fresh
`model_provenance_audit` and `reference_audit` and requires
`CONSISTENT_METADATA_NOT_OWNERSHIP` /
`NO_OBSERVED_CONFLICTS`; independently checks exact image IDs
and model marker file SHA256; and checks existing
unowned *ready* registry fingerprints for drift without
setting `owned=True`. It embeds approval bytes SHA256, entry
list, baseline SHA256 and resource fingerprints in the canonical
SHA256 plan receipt. Plan/apply share precisely the same input
files; apply holds the lifecycle lock, demands the existing
typed irreversible phrase + full receipt SHA, fully rebuilds
the plan, and rejects any drift. Extra Docker references/aliases
are independently rescanned after project Docker removal and
model marker hashes are revisited before file deletion.

**Important:** the exception enables an owner-requested destruction
policy; it is not a claim that matching historical project labels
prove ownership, a promise of data recovery, or permission to
run a blind `rm -rf`/Docker prune. It never removes shared HF
or FlashInfer roots, foreign containers or the whole Git
checkout. The declared goal of eliminating the *checkout itself*
would require a **separate explicit final step after verifying
the project-scoped engine results**. Absence of a presently scanned
cache does not prove absence everywhere else. This new route
requires passing synthetics, exact HEAD CI, read-only on-host
plan/receipt review and a separately approved physical
apply procedure. **Destructive M2 remains NOT_QUALIFIED.**

### 2026-10-21 historical image build-to-current-ID evidence matrix — SOURCE REVIEW

This is a **repository source and archived operator-evidence review**, not
a new Docker scan or a deletion approval. The 2026-10-20 actual DGX
inventory recorded exactly **seven present candidate tags and full
image IDs**, all `UNVERIFIED` for ownership; the independently run
`references` mode at physical checkout
`35536609f3f971f84f63cbc1c4596a7dfbcd887c` reported
`NO_OBSERVED_CONFLICTS`, with eight project Docker containers,
three external, zero scoped foreign references/aliases and zero
project candidate volumes. Do not extrapolate these point-in-time
checks to other Docker contexts, future changes or non-Docker users.

### Exact current image identities and independent historical anchors

Each historical record below was written from a prior actual DGX
build/inspection at its own dated checkout; the present identities are
from `CURRENT-STATUS.md`, **not** re-inspected for this source review.
`BUILT_IMAGE_MATCH` means the archival physical *build* record's
full image ID exactly matches the later real-host image ID. This is
strong historical association, **not** exclusive ownership or
permission to remove.

| Current tag (all `UNVERIFIED` in inventory; `owned=False` only where a registry record exists) | Exact observed image ID (`sha256:` prefix omitted in table) | Evidence type / independent anchor | Source-only assessment |
|---|---|---|---|
| `vllm-skinny-tp1:v1` | `01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4` | [legacy Dockerfile](../scripts/Dockerfile.skinny-gemm), `install.env` `VLLM_IMAGE`/`IMAGE_OWNED=0`, exact unowned registry image ID; canonical and AB-legacy containers mount the identified OrcaRouter checkpoint | **BUILD_ID_ATTESTATION_MISSING**: image lacks project build labels; source recipe + managed use + registry identity are not direct proof that this image was built exclusively for the project |
| `vllm-orcarouter-v029:v1` | `dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734` | [v0.29 project Dockerfile](../scripts/Dockerfile.v029-orcarouter); [R25b physical build record](../scripts/benchmark/evidence/orcarouter-r25b-init-model-image-preflight-result-20261005.md) lists this **same exact parent ID** and inherited project stability label; R22 and A/B experiments reference it | **HISTORICAL_PARENT_ID_MATCH**, not an independently recovered original build log of this baseline and not proof it has no current external consumer |
| `vllm-orcarouter-v029-h38-decoder-scope:v1` | `412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc` | [H38 Dockerfile](../scripts/Dockerfile.v029-h38-decoder-scope), [managed image chain](../scripts/runtime/prepare-h38-image.sh), [actual DGX H38 installed source-contract check](../scripts/benchmark/evidence/orcarouter-h38-exact-image-source-contract-result-20261008.md) identified same image ID before/after static inspection | **INSTALLED_SOURCE_ID_MATCH**, not a directly cited original image-build log; intermediate H9–H12 source chain must remain distinguished from the seven currently tagged candidates |
| `vllm-orcarouter-v029-r25-init-marker:v1` | `9abb228a5a4c232d20bf38e33a806f15d4bf62ff61128502349fdf39d70e3a9e` | [R25b actual DGX build and preflight](../scripts/benchmark/evidence/orcarouter-r25b-init-model-image-preflight-result-20261005.md), `Dockerfile.v029-r25-init-model-markers`, exact parent v0.29 ID, `qwen38.r25=init-model-boundary-v1` | **BUILT_IMAGE_MATCH** |
| `vllm-orcarouter-v029-r26-construction-marker:v1` | `568d0ac6917b324eef6c29e5f06b0a1ba182b5db043052b13296fe7d3c5428aa` | [R26 actual DGX build and preflight](../scripts/benchmark/evidence/orcarouter-r26-construction-image-preflight-result-20261005.md), `Dockerfile.v029-r26-construction-markers`, exact R25 parent ID, `qwen38.r26=construction-boundary-v1` | **BUILT_IMAGE_MATCH** |
| `vllm-orcarouter-v029-r27-linear-marker:v1` | `e9e92c5cb98d443a8410f21345cb0e07c30c9e7c84516cedcc2a6dc213934119` | [R27 actual DGX build and preflight](../scripts/benchmark/evidence/orcarouter-r27-linear-image-preflight-result-20261005.md), `Dockerfile.v029-r27-linear-boundary-markers`, exact R26 parent ID, `qwen38.r27=w4a16-linear-boundary-v1` | **BUILT_IMAGE_MATCH** |
| `vllm-orcarouter-v029-r28-unquant-linear-marker:v1` | `54c1ae1ba05fc34ec10881db4e5a333895eebf5472a5d282fefa354fe39a762f` | [R28 actual DGX build and preflight](../scripts/benchmark/evidence/orcarouter-r28-unquant-linear-image-preflight-result-20261005.md), `Dockerfile.v029-r28-unquant-linear-markers`, exact R27 parent ID, `qwen38.r28=unquant-linear-boundary-v1` | **BUILT_IMAGE_MATCH** |

**Dependence versus historical creation:** the project-owned-code R25
→ R26 → R27 → R28 chain and H38's separate v0.29 → H9 → H10 →
H11 → H12 → H38 build path establish *source-level* parentage,
but deleting tags does not imply removal of all shared underlying
Docker layers or all historical source. v0.29 remains referenced by
currently preserved project containers (and is a parent of project
diagnostic images). The unlabeled legacy image is still selected by
the active managed install manifest; none may be treated as disposable
simply because one other container's reference is absent.

### P1 authorization gaps and next inspection boundaries

- **Legacy Skinny:** locate independent physical historical build log
  or source/image identity attestation tied to the exact current
  `sha256:01bd...`, with trusted provenance outside mutable labels.
  If unavailable, keep `UNVERIFIED` and require a separately
  reviewed exceptional legacy-asset disposition; do not fabricate
  a build record or change `IMAGE_OWNED=0`.
- **v0.29 and H38:** existing parent-ID / installed-source records
  provide stronger evidence than names; their original build
  provenance and current full dependency snapshot remain distinct
  validation gates. Validate the complete intermediate H38 chain
  before authorizing removal of project-exclusive data or layers.
- **R25–R28:** four historical build outputs already support exact
  project-created-image identity. Preserve dated logs and audit
  file references; require new live image-ID/tag/labels/reference
  checks and an independent owner approval at plan/apply time.
- **All seven:** historical identity does **not** attest exclusive
  Docker and non-Docker use. Recheck aliases, all external
  container/image/volume/bind references, cross-project shared
  image layers, running/stopped consumers and drift at both
  plan and apply. Never delete a foreign container or prune
  shared Docker resources as an inference.
- **Models/HF cache:** `provenance` verified two marker/registry
  sets and file metadata but no model-content hash or exclusive
  ownership; cache entry inventory and independently verifiable
  origin/revision/path remain open. Treat each project-like HF
  candidate as `UNVERIFIED`; the shared parent stays excluded.
  The last `references` zero-volume result is **not** a cache
  inventory result.

This matrix is **not** a hardcoded deletion allowlist and does not
change the full-reset engine, cumulative ownership registry,
Wizard menu 5, M2 `NOT_QUALIFIED` or the Draft/Unmerged PR #261.
No source-only confidence label above represents affirmative
`PROJECT_EXCLUSIVE_REVIEWED` authorization.

### 2026-10-20 physical `references` audit: exact-SHA zero observed Docker conflicts

At actual **local source HEAD**
`35536609f3f971f84f63cbc1c4596a7dfbcd887c`, on the
correct clean feature branch, the owner executed the maintained
read-only `uninstall-inventory.py references` command.
It completed with `NO_OBSERVED_CONFLICTS`: **8** project
containers, **11** total containers, **3** external containers,
**7** project candidate image tags, **0** project candidate Docker
volumes, **0** observed external-reference conflicts, and
**0** other tags sharing a candidate image ID.

This closes the previous source-only gap for this specific helper
and is independent of the earlier ad-hoc owner-run Docker reference
query. It is only a **point-in-time read-only** Docker image-ID,
bind-path and candidate-volume overlap inspection. Neither probe
establishes ownership of historical `owned=False` assets,
non-Docker open-file dependencies, exclusive HF cache use or future
host state. Project models and images remain unverified; the
source-only full deletion plan must continue to fail closed.

### Proposed P1 historical asset authority design — NOT APPROVED FOR APPLY

The following is an **implementation/acceptance proposal**, not
an accepted deletion approval, not a registry schema migration, and
not permission to run the current destructive engine. The existing
`INSTALLER_OWNED` semantics must remain unchanged.

1. **Separate authority type.** Introduce an explicit evidence-bound
   `PROJECT_EXCLUSIVE_REVIEWED` decision for eligible historical
   model/image/cache candidates, *separate* from
   `owned=True` / `INSTALLER_OWNED`. No name-prefix
   promotion, inferred ownership flags or ad-hoc external deletion
   allowlist; every positive decision binds to one already-discovered
   exact resource and an independently reviewed provenance record.
   It must not convert an existing `owned=False` registry record
   or silently override contrary manifest/registry evidence.
2. **Identity and evidence.** For each model require exact absolute
   path under the reviewed project model root, real directory,
   pinned repository + 40-hex revision, complete marker bytes/hash,
   one consistent registry record, file inventory and independently
   attributable project download/restore history. For each image
   require exact tag and full `sha256:` image ID, build/history
   evidence, labels when present, project Docker ancestry and
   explicitly evaluated unlabeled legacy cases. For each
   project-specific HF cache entry require independently scoped
   repository/revision-to-cache identity and a no-sharing assessment;
   the shared HF/cache parent is **never** a whole-tree target.
   A discovered project volume (none in the present snapshot)
   would require exact volume name/ID/labels, mount provenance and
   every consumer checked. Matching labels, file counts,
   fingerprints, an unused image or `NO_OBSERVED_CONFLICTS`
   alone are insufficient independent proof.
3. **Approval separation and completeness.** Build a review report
   before preparing any deletion-capable receipt, showing evidence
   sources, authority grounds, exclusions and unresolved cases.
   A separate explicit owner-reviewed approval must name each
   qualified exact target; the complete-reset plan must reject any
   **present unverified resource**, rather than omit it and report
   success. An external or shared resource must remain protected
   even if an owner mistakenly includes its name in an approval.
   Keep current plan/apply/verify and double-consent boundaries.
4. **Tamper/drift and containment.** At plan **and** apply,
   revalidate the reviewed evidence, marker bytes, filesystem
   device/inode/mode and non-symlink ancestry, fixed model/cache
   root confinement, exact image ID/tag mapping, full Docker
   inventory/foreign container bind/image/volume references,
   aliases, nested mounts and lifecycle state. Reject missing
   evidence, drift, ambiguous symlink/hardlink/shared-mount
   provenance or incomplete external discovery. Do not consume
   evidence or credentials located in a tree about to be removed
   without a separately checked private receipt outside that tree.
   Any plan/application race or post-removal residual/incomplete
   check must yield **BLOCKED/PARTIAL**, not complete success.
5. **Regression and qualification gates.** Add synthetic tests
   for valid independently attributable legacy candidates *and*
   negative cases: foreign similarly named model/image/cache,
   forged `owned=True`, missing or changed project evidence,
   marker/file metadata drift, tag alias or image-ID change,
   foreign Docker image/bind/volume use, shared cache parent,
   unexpected symlink/hardlink/mount, added candidate between
   plan/apply, partial deletion and postcheck uncertainty.
   Run a real disposable-host M2 with intentionally placed
   foreign assets and failure injection before considering a
   separately approved physical-host procedure. Source CI PASS
   alone never qualifies the protected single DGX.

**Implementation sequence:** first finish the independent
historical *image* and *model/cache* provenance evidence matrix.
Only then review the authority contract, implement an auditable
separate evidence mechanism, extend the existing lifecycle
module/tests and Wizard preview, and qualify on a disposable host.
Until approval and qualification, the existing fail-closed
`candidate_ownership_not_proven` check is correct and remains
enabled. No DGX apply or PR Ready/Merge.

### 2026-10-20 actual DGX model metadata consistent; exclusive deletion ownership still unresolved

The owner has now **physically executed** the newer read-only
`uninstall-inventory.py provenance` command. It returned
`CONSISTENT_METADATA_NOT_OWNERSHIP`, without model-specific issues.
For the two real `owned=False` model directories, project markers
have `status=complete`, single ready registry records, matching
marker SHA256 fingerprints and exact repositories/revisions matching
`scripts/model/model-profiles.sh`:

- **mazinb:** revision `f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f`;
  108/108 listed regular files present; 0 unknown-size entries;
  97 listed file-content hashes, 0 recalculated.
- **OrcaRouter:** revision `c1209bda15a6bbc4c68b585e93d40c0d85f50306`;
  30/30 listed regular files present; 0 unknown-size entries;
  20 listed file-content hashes, 0 recalculated.

These are **138/138 bounded file-presence/size checks**, not full
checkpoint integrity or an independently proven download history.
The Git checkout HEAD after the owner's source update was not printed:
the successful CLI execution proves the newer `provenance` action
was available, not that the full checkout matches a specified SHA.
Details and earlier fingerprints are in `docs/CURRENT-STATUS.md`.

**Next approval gate remains blocked:** model metadata and absence of
observed external Docker conflicts are *association/consistency*
evidence, not project-exclusive delete authority. The full-reset
engine must continue to refuse present unverified model, image and
model-cache candidates. No registry `owned=True` promotion, ignored
unverified assets, shared-cache purge or destructive Wizard menu 5.
A separate reviewed exact-identity authority design requires
independent historical provenance and foreign-resource/dependency
checks for each target, including the seven current images, plus
synthetic foreign-preservation and disposable-host M2 coverage.
The legacy managed `uninstall.sh --purge-all` remains insufficient.

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

### 2026-10-20 physical exact Docker inspection — project association versus exclusive ownership

The latest operator-pasted DGX output independently inspects every
**8/8** currently enumerated project Docker ID. All eight are exited
(four exit 0, four exit 137). Seven project trial/research containers
have `qwen38.*` labels and a project model bind: two OrcaRouter
A/B, one H38, three mazinb M1 R2 and one R22 OrcaRouter.
H38 `/model` binds `checkout/model`, the verified local symlink.
The eighth, `/qwen38-flash-next`, is the legacy unlabeled managed
container; its `/model` bind is the exact managed OrcaRouter
checkpoint path (read-only), and its legacy image is
`vllm-skinny-tp1:v1`.

Six currently present v0.29-derived image tags have `qwen38.*`
build labels; the one legacy image is unlabeled. Seven tag→image-ID
pairs and all eight container ID/name/image/mount sets are now in
`CURRENT-STATUS.md`, including the R25–R28 image IDs that are not
referenced by the eight project containers shown. This **does not**
prove exclusive ownership of any image or lack of references from
unrelated containers. A complete, unfiltered Docker inventory and
reference reconciliation is still required.

**Shared cache non-deletion boundary observed physically:**
`/qwen38-flash-next` bind-mounts the host's
`/home/inlc/.cache/flashinfer` (shared) at
`/root/.cache/flashinfer`. Container removal never authorizes
deleting that host path. AB/mazinb private caches live in project
state; dedicated H38/R22 caches use project-specific host
`~/.cache/*-v029` directories. Keep `EXCLUDED_SHARED` in
postcheck and never replace it with blanket cache purge.

**Source-only additional guard:** an unlabeled reserved-name
`/qwen38-flash-next` is no longer admitted to the plan using only
the suggestive basename of its `/model` mount. The engine requires
the strict managed manifest's exact `MODEL_DIR`, an exact matching
present model entry in the bounded inventory, and one read-only
bind mount at `/model` with identical source. A different but
similarly named foreign model or writable mount fails closed, with
synthetic tests. This strict active-manifest binding can block
legitimate old predecessors after profile changes; supporting those
requires separately evidenced immutable historical records, not a
weaker basename check. No physical DGX source sync or M2 validation
has been performed.

### Read-only Docker dependency audit: reproducible source helper (SOURCE_ONLY, 2026-10-20)

A separate `references` mode was added to the existing
`scripts/lifecycle/uninstall-inventory.py`, so repeatable checks
do not depend on past one-off pasted Python scripts:

    python3 -B scripts/lifecycle/uninstall-inventory.py references
    python3 -B scripts/lifecycle/uninstall-inventory.py references --json

This is **read only** and does not write a deletion receipt, mutate Docker,
change state/swap, change the registry or promote ownership. The mode
independently re-queries the complete Docker container list, inspects
**exact full-ID external containers**, maps all currently inventoried
candidate image tags to full image IDs, detects other tags sharing those
IDs and verifies project candidate Docker-volume references and host
bind-path overlaps (both lexical and symlink-resolved). Its candidate
filesystem scope comes from the bounded project resource inventory,
including explicitly discovered model-root candidates and
project-only cache/state/data/forensic paths; shared HF/runtime
cache *parent* paths remain excluded. Unexpected symlinked model
entries, missing/different Docker IDs, malformed inspect results,
incomplete inventory, inaccessible Docker and inspection limits
result in **INCOMPLETE**, never a zero-conflict pass.

Outputs are `NO_OBSERVED_CONFLICTS`, `CONFLICTS` or
`INCOMPLETE`; shell exit codes are respectively 0, 3 and 2.
Even `NO_OBSERVED_CONFLICTS` is a **point-in-time external-Docker
reference report only**, not evidence of exclusive model/image
ownership, open file descriptors of other host processes, and
certainly not approval to apply a reset. Synthetic tests check
shared-cache exclusions, external image-ID matches, project bind
overlap, Docker volume use, image aliases and discovery drift.
The physical DGX has **not** executed this newly added mode
because its last reported local checkout predates the source;
the owner's manual 11-container check is separately recorded
in `CURRENT-STATUS.md`.

### Model marker identity and lightweight provenance audit — SOURCE_ONLY (2026-10-20)

The owner independently inspected both actual project checkpoint
directories: OrcaRouter and mazinb are real, present directories and
each has exactly one `owned=False`, `ready` cumulative registry
record. Each `.qwen38-model-manifest.json` SHA256 matches its own
record (OrcaRouter `3c1cb3a9082801d23c4d7cd14bfe3f30cba900b43fd32d3619e59328fcbd6389`;
mazinb `996eb79378ab09160e119951b7e089b3ad32f8db718c943f84f7233580ef431c`).
Actual marker top-level keys are `files`, `repository`, `revision`,
`schema_version`, `status`. Their **values were not printed**.
`scripts/download-weights.sh` generates this schema from pinned
Hugging Face file metadata; `asset_ownership.py` stores the
**marker hash**, which does not verify the checkpoint file contents.
Project association and unchanged marker identity must not be
misrepresented as installer ownership or full model integrity.

A new `provenance` mode of the existing read-only inventory
can repeat this assessment **after a separately reviewed clean
fast-forward to its source**:

    python3 -B scripts/lifecycle/uninstall-inventory.py provenance
    python3 -B scripts/lifecycle/uninstall-inventory.py provenance --json

It requires a valid bounded inventory and exact model registry records,
reads model marker JSON with a size limit, compares the marker SHA256
to its recorded ready fingerprint, validates pinned 40-hex revision,
schema/status, enumerated file paths and each file's existence,
non-symlink ancestry and recorded nonzero size. It never reads or
hashes checkpoint tensor contents, downloads weights, runs a model,
changes Docker or upgrades `owned=False`. JSON and text explicitly
report that **zero model-content hashes were verified**.
`CONSISTENT_METADATA_NOT_OWNERSHIP` means metadata/size consistency,
`REVIEW_REQUIRED` means an issue was observed, `INCOMPLETE`
means inventory/registry inspection failed, and
`NO_MODEL_CANDIDATES` means nothing in this scope was found.
A zero size in upstream metadata is treated as **unknown expected
size**, not an integrity match. The source-only synthetic tests cover
valid metadata with `owned=False`, incomplete download status,
size drift, file symlinks and marker/registry hash drift.
None is a destructive uninstall qualification or exact allowlist
authority. Live DGX `provenance` output has **not been obtained**.
The positive-ownership fail-closed guard remains unchanged.

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
