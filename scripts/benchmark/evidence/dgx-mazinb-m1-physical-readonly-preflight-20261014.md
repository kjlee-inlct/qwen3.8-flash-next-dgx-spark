# ACTUAL DGX Spark — mazinb M1 physical read-only preflight (2026-10-14 KST)

## Source and scope

This is a **user-provided actual DGX terminal transcript**, observed through
the root `wizard.sh` at exact Git commit
`2dfa74dacedfe50fe1c28ca309939ed9d61b8123` on
`feature/wizard-modular-phase1-20261014` (Draft PR #261).

The operator safely fetched the Git ref, verified detached HEAD, and ran
`wizard.sh`. The installed manager reported:

- `Manifest: valid (phase=complete)`
- `Profile: orcarouter`
- `Image: vllm-skinny-tp1:v1`
- `Runtime: NOT_PROBED` — the manager did NOT assert a running service.

At **Wizard -> 5 Benchmark**:
- Option **6** returned `M1_PLAN=NEW_ISOLATED_MAZINB_16G`,
  `M1_PORT=127.0.0.1:18889`,
  `M1_WATCHDOG=ARM_EXACT_ID_BEFORE_START`,
  `M1_SESSION_MAX_SECONDS=5400`, `M1_KEEP_OLD_AB_AND_MANAGED=YES`,
  `M1_START=ONLY_INTERACTIVE_WIZARD_OPT_IN`,
  and `M1_BENCHMARK=NOT_MEASURED`.
- Option **7** returned `M1_SESSION=ABSENT`.
- Option **8** displayed the managed protected Docker ID and required exact
  64-character typed confirmation. The operator confirmed it and approved
  sudo credentials for read-only NVIDIA RM evidence access.

### Exact physical output

```text
M1_PROTECTED_PREDECESSOR_ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24
M1_PREFLIGHT=PASS_READ_ONLY
M1_OLD_DOCKER_ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24
M1_IMMUTABLE_RELEASE=/home/inlc/.local/share/qwen38-spark/releases/ff67bab3c94d6992f61b9535836df97f03b9c022
M1_IMAGE_ID=sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734
M1_CANDIDATE_START=NOT_PERFORMED
```

These image/release/container identities were the verified *read-only*
snapshot at the time of the run; re-check all identities at the start of
any later M1 session. The output contains no model-token throughput,
memory benchmark, runtime READY, exact live model JSON, or new M1 Docker ID.

## Interpretation and gates

**PASS:** M1 plan/status inspection and current-host read-only admission,
with the exact predecessor ID, current manifest/release, mazinb image,
checkpoint and filesystem/lifecycle/memory preflight evaluated by source.
This is meaningful ACTUAL_DGX evidence, **not** synthetic GitHub CI.

**NOT RUN:** New `docker create`, watchdog arming on a real new candidate,
`docker start`, API /health, strict /v1/models response,
180-second post-READY soak, actual inference smoke, strict live RM
window, any measured llama-benchy work, external benchmark backup.

**PRESERVATION:** The preflight path does not remove or restart the managed
OrcaRouter, delete or restart historical mazinb A/B Docker objects,
remove model checkpoints or clear raw evidence.

**Next source hardening before physical startup:** The new M1 controller
must use a unique per-candidate `HOME` to ensure vLLM and FlashInfer
cache mounts do not touch the user's previous experimental or canonical
cache directories. Re-run source CI and perform exact-SHA verification of
that hardening commit. Do not launch live M1 on the older preflight SHA.

**Do not infer guaranteed host stability from preflight success.** The
historical managed 16-GiB mazinb run had an NVIDIA
`NV_ERR_NO_MEMORY` event despite successfully reaching READY; the
new M1 physical strict RM gate remains mandatory.

## Second current-host read-only review — user transcript (2026-10-14 KST)

After the source-only per-trial cache isolation change at
`72982e0e1bb53cdf8bb66a641356eb4a7e743320`, the operator
submitted a second root Wizard 5 -> 8 output confirming again:

- `M1_PREFLIGHT=PASS_READ_ONLY`
- `M1_CANDIDATE_START=NOT_PERFORMED`
- protected predecessor ID `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
- identical release `ff67bab3c94d6992f61b9535836df97f03b9c022`
- identical image `sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734`

The operator subsequently opened historical evidence via 5 -> 5 and chose
0 (Back). This did **not** re-inspect or mutate either historical case.

**Provenance qualification:** This second pasted output did *not* include a
`git rev-parse HEAD` line. The operator had been given instructions to
switch to the hardening commit, but the text alone is not an independent
cryptographic confirmation that the second preflight ran that exact SHA.
Before authorizing a physical M1 load, recheck the live worktree HEAD
against the pinned runtime source SHA and ensure the worktree is clean.
No M1 Docker creation, API READY, inference smoke or benchmark is reported.

## ACTUAL DGX FIRST LIVE M1 — memory protection stop (2026-10-14 KST)

**Observed source:** Exact DGX detached-worktree HEAD
`72982e0e1bb53cdf8bb66a641356eb4a7e743320` with clean status.
The owner selected root Wizard **5 -> 9**, explicitly approved a new
GPU-heavy M1 launch, acknowledged the complete preserved managed
predecessor Docker ID and typed `START_MAZINB_16G`; sudo kernel log
access was authorized.

**Physical terminal output (verbatim):**

```text
M1_SOURCE_READY=72982e0e1bb53cdf8bb66a641356eb4a7e743320
M1_CANDIDATE_STARTED_UNQUALIFIED=qwen38-mazinb-m1-20261013235416-edd777eb
M1_STOPPED_EXACT_ID=1ebe723a279171794d7753cdbc3726e8c0db052c7cac02ec3060b8fc23c2700d
M1_DOCKER_REMOVED=NO
M1_BLOCKED=candidate triggered memory-protection stop
```

**Verdict:** The new mazinb M1 Docker candidate was started and
supervised, then **stopped under memory protection before READY**.
The candidate Docker object was preserved, not removed.
No `M1_READY_FOR_BENCH`, actual inference smoke, post-ready 180-second
soak, llama-benchy JSON, model token/s or performance report exists
from this attempt. Do not misclassify the protective stop as an
observed Docker OOMKilled or NVIDIA RM failure: the pasted terminal
does not contain Docker inspect, monitor warning samples or kernel logs.

**Mandatory next step before any relaunch:** Collect read-only
`docker inspect` for the exact candidate ID,
`~/.local/state/qwen38-spark/mazinb-m1/<NAME>/monitor.log`,
`.../monitor/runtime-stop.env`, preserved active/per-trial JSON,
`docker logs`, `/proc/meminfo` and scoped sudo kernel journal.
Keep all old A/B, managed Docker, original candidate, models,
image, swap and evidence. No threshold lowering or repeated live start
until the numeric cause of the memory-protection transition is known.

**Source interpretation, not yet physical proof:** The current
`monitor-runtime.sh` protection predicate requires either
`SwapFree < 8 GiB` OR `noncmafree < 2 GiB` together with
`noncma_available < 10 GiB` OR swap consumption during monitoring
`>= 256 MiB`, for 5 consecutive samples 2 seconds apart.
Monitor log values determine which path actually triggered.

## ACTUAL DGX first live M1 monitor diagnostics — protection trigger established

**The actual second read-only diagnostic paste resolves the former uncertainty.**
Exact candidate ID `1ebe723a279171794d7753cdbc3726e8c0db052c7cac02ec3060b8fc23c2700d`
was `exited`, `RUNNING=false`, `EXIT=1`, `OOMKilled=false`, Docker started
`2026-10-13T23:54:16.608663358Z` and stopped
`2026-10-13T23:59:28.100236951Z`. Independent
`monitor/runtime-stop.env` pins the same Docker ID and
`STOP_REASON=memory-protection` at `2026-10-13T23:59:18Z`.
Model loader reached **26 / 95 safetensors shards (~27%)**,
then vLLM printed `KeyboardInterrupt: terminated` after the watchdog
stop. The traceback was caused by the explicit SIGTERM/shutdown; it is
not evidence of an independent checkpoint/model failure.

### Exact 2-second protection series (local KST)

| Time | Non-CMA free MiB | Non-CMA available MiB | Swap growth MiB | Protect |
| --- | ---: | ---: | ---: | --- |
| 08:59:10 | 1192 | 37855 | 279 | 1/5 |
| 08:59:12 | 1233 | 37616 | 331 | 2/5 |
| 08:59:14 | 2045 | 38684 | 331 | 3/5 |
| 08:59:16 | 1436 | 38373 | 331 | 4/5 |
| 08:59:18 | 1496 | 38698 | 411 | 5/5 |

Trigger was **non-CMA free < 2048 MiB (even 2045 MiB is below 2 GiB)**
PLUS **swap growth >= 256 MiB**. Available memory was 37-38 GiB
and SwapFree ~146031 MiB during stop, so this was **not**
SwapFree exhaustion or the primary non-CMA available < 10 GiB guard.
Earlier samples repeatedly printed `protect=0/5` despite
non-CMA free below 2 GiB because swap growth was < 256 MiB.

The diagnostic `sudo -n journalctl -k ... | grep -Ei ...`
section returned no matching lines for its selected time window;
this is *not* an exhaustive proof of no kernel issues elsewhere.
After stop, the host showed `121Gi` RAM total, ~`118Gi` available,
`/swap-ple.img` 128 GiB active (~1022 MiB used), and a separate
`/swap.img` 16 GiB active (0 used). Never modify existing swaps as
a response to this initial trace.

### Targeted source policy for next experimental M1 (NOT YET PHYSICALLY RUN)

The subsequent **new code** keeps monitor historical defaults unchanged
but permits `--swap-pressure-available-gib 12` **only** with pinned
protected Docker labels `qwen38.abtrial=mazinb` and
`qwen38.variant=m1`. New M1 passes 12. Thus swap growth
>= 256 MiB plus non-CMA free < 2 GiB does **not alone**
trigger protection while non-CMA available >= 12 GiB.
The original primary low-available gate of **10 GiB**,
SwapFree floor **8 GiB**, five consecutive samples at 2 seconds,
exact-ID stop, strict `/health`/model ID, guarded READY/180s soak,
and host-side strict NVIDIA RM check remain in effect.
The 12-GiB extra gate is a narrowly scoped mitigation, **not**
proof that all 38-GiB available states are safe or that a fresh
model/benchmark will pass. A future observed NVIDIA RM memory event
continues to disqualify strict host stability.

**State bookkeeping issue also found:** The original failed live run
stored JSON `phase=stopped` because `stop_exact` overwrote the interim
`failed` phase with `stopping` before deriving its final label.
New code preserves `failed_stopped` and the cause for subsequent
attempts. Historical immutable trial JSON must not be rewritten.

