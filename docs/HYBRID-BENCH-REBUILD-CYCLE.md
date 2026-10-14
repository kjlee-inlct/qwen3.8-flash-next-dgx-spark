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
