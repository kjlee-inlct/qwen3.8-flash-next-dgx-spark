## 2026-10-14 — H6 isolated protected 16-GiB trial controller (SOURCE ONLY)

**Actual DGX admission evidence at commit**
`e61f6b4d44624e8ebb454eac3288d13e3904f370`:
`INSTALLED_MODEL_PROFILE=orcarouter`,
`SERVICE_ENABLED=0`, `SERVICE_OWNED=0`,
`MONITOR_ENABLED=1`, `MONITOR_PROTECT=1`,
`MONITOR_HEARTBEAT=60`; managed idle PASS;
pinned H3→H6 structural validator PASS; canonical prior Docker ID
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
stopped/non-OOM. `HYBRID_H6_LAUNCH_ADMISSION=BLOCKED_PENDING_SAFE_CONTROLLER`,
RC=3 **EXPECTED** because the existing service-backed live profile
switch requires ownership and boot-enabled management. This does not
invalidate the earlier H6 structural PASS or authorize checkpoint reclaim.

**New source-only experiment path:** Wizard **Benchmark 17–20** uses
`scripts/wizard/hybrid-h6-m1.py` (plan, status, strict preflight,
explicitly approved foreground protected run), extending
`scripts/serve.sh` with a unique `hybrid-h6-m1` create-only
profile at loopback `127.0.0.1:18890` with fixed **16 GiB KV**,
reboot restart policy **no**, and isolated trial HOME/cache/state.
This path **does not invoke installer profile switch**, change the
installed manifest or boot units, remove/recreate the original
`qwen38-flash-next` container, or retire old Hybrid trials.

First checks exact original container+image, immutable release,
install manifest SHA, transaction markers, owned operation lock,
single-model host idle, pinned H6 chain, image ID, active 128-GiB
managed swap, 12-GiB non-CMA available / 4-GiB non-CMA free /
16-GiB SwapFree / 20-GiB filesystem free, exclusive port 18890,
and strict sudo-readable NVIDIA kernel journal.
The fresh candidate is **Docker CREATE only**, then the separately
started exact-ID memory watchdog MUST write `armed` BEFORE
`docker start`. Stop on watchdog loss/memory-protect marker,
kernel NVIDIA RM allocation errors, old container/manifest/release
drift, API READY/served model ID failure, missing heartbeat, or
runtime/soak failure. Require 180-sec soak and inference smoke
before printing `H6_READY_FOR_BENCH`.
A caught terminal termination and normal STOP target **only** the
new pinned H6 ID, preserve the Docker object/logs, and never prune.
The watchdog has its own bounded fail-closed stop even if the
operator supervisor unexpectedly exits. Failure is never a 0-tok/s
measurement.

Terminal B `scripts/wizard/with-h6-session-lock.sh` holds a shared
lifecycle lock and exclusive H6 benchmark lock, reruns H6
`bench-admission` with exact Docker ID + heartbeat + RM checks
**before** executing the benchmark command. Wizard Terminal A
defers STOP while the benchmark lock is held. Do not run arbitrary
Docker CLI commands as a benchmark. Use a pinned llama-benchy
command with real JSON and provenance; separately archive/verify
hashes before any later model cleanup.

**QUALIFICATION BOUNDARY:** This entire new controller and synthetic
tests are SOURCE_ONLY until CI plus real DGX read-only preflight
and a separately authorized GPU run are captured.
`H6_READY_FOR_BENCH=NOT_OBSERVED`;
`H6_LLAMA_BENCHY=NOT_MEASURED`;
`H3_H4_H5_H6_DELETE=BLOCKED_KNOWN_REFERENCES`.
H7/H20 checkpoint alias and 16 old stopped Docker mounts still
block the original full-chain deletion. Do not use deletion, service
enablement, or raw unmanaged Docker as a bypass.

## 2026-10-14 — DGX dependency audit PHYSICAL PASS (retirement BLOCKED)

At exact `443fd2bd01f0bd5314ee6a0dc66608d2059dfbf6`, operator
performed the new physical Hybrid reference audit.
`PROTECTED_PROFILE_REFERENCES=2` (H7 group metadata and H20
ModelOpt conversion both alias the existing H6 checkpoint);
`DOCKER_CONTAINERS_INSPECTED=24`;
`DOCKER_REFERENCING_CONTAINERS=16` all exited, including
`DOCKER_OTHER_ROOT_REVIEW_CONTAINERS=11` recorded with historical
`/home/inlc/models` mounts.
`HYBRID_REFERENCE_AUDIT=BLOCKED_KNOWN_REFERENCES`,
`HYBRID_DELETION_AUTHORIZED=NO`, RC=3 **EXPECTED**.
No models/services/containers changed; H6 first bench NOT_MEASURED.

**Independent startup issue identified in source:** DGX installed manifest
last reported `SERVICE_ENABLED=0`, while `install.sh` requires
`SERVICE_ENABLED=1` AND `SERVICE_OWNED=1` for a real managed
profile switch. The current shutdown state cannot safely be converted
into a qualified live H6 switch by blindly running
`install.sh --model orcarouter-hybrid`. Even restoring ownership
requires careful no-boot/no-accidental-start planning. A source-only
read-only Wizard **Models 3→9** admission checks this lifecycle
restriction plus protective monitor/heartbeat and exact stopped
predecessor, without any model start; physical check pending.
Implement a protected isolated H6 trial or explicitly reviewed
managed-service transition before 1st benchmark; **do not bypass
with docker run**.

## 2026-10-14 physical DGX Phase-0 observed — static PASS / retirement blocked

**Source:** operator terminal on
`8ca529ba62067cae10e7ccdfd457e890967a1133`.
Fast-forward from `2a2c222`; managed idle PASS: API local, boot/service
disabled, no managed listeners or running Qwen containers. Pinned
`--runtime-only` Hybrid H3→H6 validation PASS (base
`c1209bda15a6bbc4c68b585e93d40c0d85f50306`, mazinb provenance
`f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f`).
The operator log has the base/H3/H4/H5/H6 manifest and index SHA256.

Physical `df -B1` available **298422198272 B**; FS 69% used.
`du -s -B1` base **183535857664 B**, H3 **77543333888 B**,
H4 **68014092288 B**, H5 **44912640 B**, H6 **35475456 B**.
Stage symlinks H3=13, H4=76, H5=91, H6=139; multi-link regular
file count zero for all five trees. Allocation is **not** certified
reclaimable bytes (COW/reflink/shared extents, peak build disk usage,
external references all require separate proof).

**Blocking evidence:** model registry lists protected
`hybrid-h7-group-metadata` and
`hybrid-h20-modelopt-convert-diag` with the exact H6 checkpoint path.
24 Docker containers were inspected, 22 exited; OpenWebUI and Portainer
are the two unrelated running containers. **16 exited Hybrid trials**
bind-mount all H3/H4/H5/H6 (five use repo-local model paths, eleven
record historic `/home/inlc/models` paths). Historical mounts and H7/H20
references must be preserved, reviewed and independently resolved;
none may be deleted as a shortcut.

**Verdicts:** `HYBRID_PHASE0_READONLY=PASS_STATIC_INVENTORY_ONLY`;
H6 actual READY/inference/llama-benchy **NOT_RUN / NOT_MEASURED**;
full H3→H6 retirement **BLOCKED_KNOWN_REFERENCES**; rebuild and
second benchmark **NOT_RUN**. No GPU work or model deletion was performed.
The new source-only Wizard **Models 3→8** uses
`scripts/wizard/hybrid-dependency-readonly.py` to report protected
registry aliases and all Docker bind mount references without changing
host state. Physical test of the *new* audit remains NOT_RUN.
This audit never authorizes deletion, even when no references are found.
The next gate remains a protected H6 live-switch/start design with
memory/RM monitors enabled, then first benchmark and independent archive.

# Hybrid H6: benchmark → full retire → prove absence → rebuild → benchmark → final retire

**Plan recorded:** 2026-10-14 KST. **Status: PLAN + physical idle PASS; Hybrid benchmark, rebuild and retire NOT_RUN.**
This document describes acceptance gates for the user's single NVIDIA DGX Spark.
Do not conflate host-free CI with physical model readiness or claim Hybrid
throughput from old H6/RM investigations. The only H6 profile in scope is
`orcarouter-hybrid`, `local/orcarouter-mazinb-h6-w4a16`,
`vllm-orcarouter-v029:v1` (not experimental H38).

## Physical starting state

The DGX's `2026-10-14` post-mazinb cleanup and twice independent
`verify-managed-idle.py` both passed on Git source `2a2c2220bbb70db6007934bd678bddd704c0f643`:
`API_ACCESS_MODE=local`, `SERVICE_ENABLED=0`, no managed active or
boot-enabled systemd units, no configured 8888/8000/8001/18888/18889
listeners and no running `qwen38-*` Docker. The manifest still carries
`MODEL_PROFILE=orcarouter`; this is configured identity, not live GPU activity.
Original mazinb source checkpoint and five exact M1/KV containers were
reclaimed after SHA-attested measurement; the H3–H6 hybrid stages, OrcaRouter
checkpoint, pinned vLLM image and research evidence remain protected.
OrcaRouter A/B benchmarking remains deferred.

**Important caveat:** `docs/HYBRID-FRESH-INSTALL-ACCEPTANCE.md` says
the installer has a source-level clean-host path but **no physical brand-new
DGX E2E acceptance** yet. A second build on this already-provisioned Spark,
with shared base model/image/swap preserved, tests *reconstruction from
source checkpoints*, not the complete fresh-OS hardware bootstrap promise.

## Six-phase ledger

### 0. Read-only admission (BEFORE any model start)

1. Confirm clean branch/HEAD, `verify-managed-idle.py` PASS, no interrupted
   runtime/profile/settings lifecycle transaction; record `df -B1`, inodes,
   full Docker IDs/image IDs, current manifest SHA, immutable release pointer,
   full stage sizes and real symlink/hardlink counts.
2. Validate current H3/H4/H5/H6 structure using
   `scripts/model/validate-orcarouter-hybrid.py --runtime-only` and the
   actual `models/` directory; record all four manifests and their SHA256.
   The missing original mazinb source is acceptable **only** in the current
   provenanced H3 reuse path.
3. Verify disk/swap/non-CMA headroom and root-filesystem reserves with
   stage sizes taken from actual allocated blocks rather than assuming an
   approximate 174 GiB checkpoint is all required. Do not start when any
   resource or ownership gate is inconclusive. ModelOpt H6 had historical
   NVIDIA RM/host-memory trouble; keep protective monitors enabled.
4. Confirm no H7/H20/historical preserved trial container/release depends on
   a checkpoint that would later be deleted; required external consumers
   block the later deletion, even if stopped.

### 1. First Hybrid benchmark: existing H6

- Use an operator-approved supervised model lifecycle path, not a raw Docker
  start bypass. **Current modular Wizard profile-switch option is preview
  only** (see `scripts/wizard/model-menu.sh`). The existing `install.sh`
  has a completed-install profile-switch transaction; no claim that the
  modular Wizard currently authorizes a qualified H6 live activation.
- Require READY `/health`, exact `/v1/models`, a real functional inference,
  protected monitor heartbeat, bounded non-CMA/swap trajectory and NVIDIA
  RM/Xid review **before** any performance workload.
- Run same pinned `llama-benchy` workload used for both trials. Record
  cold/warm context, PP/TG, TTFT/TTFR, concurrency, errors, source/release,
  image digest, H3–H6 checksums and service/container identities.
- Save original raw JSON, report, stderr/stdout, Docker logs, watchdog
  status and monitor/kernel diagnostics with SHA256 manifest. Verify an
  independently accessible/off-host copy before the first deletion.
- A protection stop, API-READY failure or RM/Xid issue is
  **BENCH_NOT_MEASURED_OR_FAILED**, not throughput zero. Archive its forensic
  data and block reclaim until there is a documented exception/decision.

### 2. First retirement: full generated-stage cleanup

- After the first measurement and off-host evidence PASS, stop the exact
  benchmark container and release managed API/service exposure using the
  approved lifecycle transaction. Verify host idle and no API listener.
- **Delete the H6 model PLUS its generating stages H5, H4, H3** if and only
  if a scoped read-only dependency/ownership and link-closure gate proves it
  safe. Deletion order: H6 → H5 → H4 → H3. Preserve the original OrcaRouter
  base source and unrelated H7/H20, H38, Docker images/other containers,
  releases, and evidence. If an unrelated dependent references any stage,
  the complete-rebuild test must stop and use isolated new stage paths
  instead; do not force-delete.
- The existing generic `manage-models.sh retire` command is **not an
  approved full-chain Hybrid cleaner** and `uninstall.sh --purge-all` is
  expressly forbidden here. Generic retire identifies each stage
  independently, may delete stopped containers/images and is not sufficient
  to attest shared symlink/hardlink/dependent closure. A stage-specific
  gated cleanup with approved exact paths must precede live deletion.
- Capture pre/post filesystem allocation and exact container inventories,
  no PR-wide or Docker-global prune, no `rm -rf models`.

### 3. Independent proof of absence

- H3/H4/H5/H6 paths all absent (including dangling symlinks), all approved
  experiment container IDs absent, all remaining Docker IDs unchanged,
  no unexpected untracked model directory, generated index/manifest paths
  absent, and no surviving symlink/mount references into retired stages.
- `API_ACCESS_MODE=local`, `SERVICE_ENABLED=0`, managed systemd units
  inactive/uninstalled, ports unbound, model GPU workers absent.
- Verify benchmark archive's raw JSON/report/log checksums again *after*
  deletion, compare before/after available bytes; do not count mere source
  bytes/hardlinks as actually reclaimed capacity.

### 4. Second installation: genuine H3→H6 regeneration

- With H3 **really absent**, the installer can no longer use its
  `HYBRID_REUSE_H3=1` shortcut. It must download the pinned mazinb source
  checkpoint again (previously retired) and use the pinned OrcaRouter base
  for full H3 → H4 → H5 → H6 reconstruction. If the source revision,
  HF entitlement or free disk/inode budget is unavailable: BLOCK.
- The installer source claims new-DGX single-Wizard setup but physical
  installation acceptance is not yet done. Verify all required downloads,
  SHA/pinned source manifests, model builder/runtime image, intermediate
  stage fingerprints, link closure and image digest; no partially stale
  output directory may be silently recycled.
- Record total **installed bytes**, download volume, elapsed times for
  individual stages, model/config equality or differences vs cycle 1,
  release/container identity and GPU/RM events. Do not mask previous
  history or overwrite trial 1 evidence.

### 5. Second benchmark and final retirement

- Identical readiness/stability gates, identical pinned model identity,
  runtime image/config/KV/corpus/tokenizer/workload and repetition policy.
  Raw cycle-2 evidence must be independently archived with SHA256.
  Compare both runs with confidence/variability, annotate config/build
  differences, not a fabricated equivalence.
- After archived evidence PASS, repeat scoped H6→H3 stage reclaim,
  verify absence and host idle (boot/service/proxy/API, Docker).
  Decide separately whether newly downloaded mazinb *source* can be deleted,
  using dependency gates and benchmark evidence. No shared OrcaRouter
  base/model/image/swap or immutable research archives are implicitly
  deleted.
- Restore logical managed state coherently after any Hybrid profile
  switch. An idle `PHASE=complete, MODEL_PROFILE=orcarouter-hybrid`
  manifest is not a deletion permit while it points at H6. Do not bypass
  active-model protections; finalize managed switch/uninstall without
  broad purge before touching that model.

## Source-only Phase-0 Wizard entry (not physical qualification)

Wizard Models **3 → 7** calls `scripts/wizard/hybrid-phase0-readonly.sh`
and reuses the existing idle validator and H6 runtime-only chain validator.
It prints manifest/index SHA256, actual disk/block metrics, per-stage symlink
and hardlink counts, all Docker container IDs and mount references.
A dirty checkout, missing or symlinked stage, failed validator or unavailable
Docker fails closed. An alternate absolute model directory is permitted through
`QWEN38_PHASE0_MODELS_ROOT` only for diagnostic inspection.

**PASS_STATIC_INVENTORY_ONLY does not permit model start or deletion.**
External H7/H20/release dependency closure, protected runtime stability,
evidence archiving and the complete retire admission remain separate gates.
The physical Phase-0 run is NOT_RUN until actual DGX output is received.
The operator command below remains a minimal manual fallback.

## Current operator gate: READ ONLY

Run from a clean physical DGX checkout, before any live activation.
No service starts, model downloads or deletions:

```bash
(
  set -euo pipefail
  cd "$HOME/Workspace/llm/qwen3.8-flash-next-dgx-spark"
  echo "=== SOURCE ==="
  git rev-parse HEAD
  git status --porcelain=v1 --untracked-files=all
  echo "=== CURRENT HOST IDLE ==="
  python3 -B scripts/diagnostics/verify-managed-idle.py
  echo "=== HYBRID H6 CHAIN ==="
  ROOT="$PWD/models"
  python3 -B scripts/model/validate-orcarouter-hybrid.py \
    --runtime-only \
    --base-dir "$ROOT/qwen3.8-flash-next-orcarouter" \
    --h3-dir "$ROOT/qwen3.8-hybrid-quant-layout" \
    --h4-dir "$ROOT/qwen3.8-h4-orca-all" \
    --h5-dir "$ROOT/qwen3.8-h5-neutral-input-scale" \
    --model-dir "$ROOT/qwen3.8-h6-modelopt-w4a16"
  echo "=== ALLOCATED STORAGE ==="
  df -h "$ROOT"
  du -sh -- "$ROOT"/qwen3.8-flash-next-orcarouter \
    "$ROOT"/qwen3.8-hybrid-quant-layout \
    "$ROOT"/qwen3.8-h4-orca-all \
    "$ROOT"/qwen3.8-h5-neutral-input-scale \
    "$ROOT"/qwen3.8-h6-modelopt-w4a16
  echo "=== MANAGED ASSETS ==="
  bash scripts/manage-models.sh assets
  echo "=== DOCKER ACTIVITY ==="
  docker ps --format '{{.ID}} {{.Names}} {{.Status}}'
  echo "HYBRID_PHASE0_READONLY=PASS"
)
```

A Phase-0 PASS establishes static chain integrity and host idle,
**not runtime READY, a successfully reinstallable chain or benchmark permission**.
Do not run any deletion step merely because this command exits 0.

## Engineering gaps before full-cycle authorization

- Provide a Wizard-mediated qualified Hybrid *live* switch/start path.
  The currently modular model switch remains preview-only. Reuse existing
  transactional installer rather than unguarded host mutation.
- Implement the independent Hybrid whole-chain retirement admission + exact
  deletion/postcheck/archives; verify protected H7/H20 consumers and
  file-link closure under lifecycle lock. No blind generic `retire` chaining.
- Provide immutable cycle-1 and cycle-2 benchmark receipt directories and
  independent SHA/off-host backup acceptance.
- Demonstrate true second-run H3 absence, forced mazinb source reacquisition
  and complete H3–H6 reconstruction; record tests for host-free source logic
  separately from actual DGX GPU runs.
- The separate full fresh-OS/single-Wizard DGX acceptance remains
  **NOT_QUALIFIED** until a genuinely new Spark is provisioned.
