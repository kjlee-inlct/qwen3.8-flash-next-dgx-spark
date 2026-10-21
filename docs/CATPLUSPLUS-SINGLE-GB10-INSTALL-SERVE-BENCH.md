# catplusplus single DGX Spark — staged install, serve, benchmark preparation

**2026-10-19 state:** SOURCE PLAN IMPLEMENTED; ACTUAL CATPLUSPLUS CHECKPOINT
**NOT DOWNLOADED**, GB10 engine **NOT QUALIFIED**, GPU/API **NOT STARTED**,
benchmark **NOT MEASURED**. This is a preparation contract, not a
functional installer or launcher.

## Operator scheduling and invariants

**Priority:** Finish currently owner-approved **mazinb R2 checkpoint download,
isolated API smoke, soak and mazinb benchmark** first. Do not use
catplusplus's bulk checkpoint downloader, temporary container, model
switch, GPU session, build, package installation or disk pressure test
while mazinb is transferring or being benchmarked.

Never change or remove the protected
`qwen38-flash-next` OrcaRouter container, its managed manifest,
its 171-GiB checkpoint, earlier mazinb A/B or M1 archive, release
symlink, shared vLLM images, swap, monitoring configuration or
historical measurements. Keep PR #261 Draft/unmerged until separately
authorized.

The exact model is
`catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed`, immutable
revision `3251fd8afbd08f76368a9bfa71132d9aef364813`. The
previous physical DGX pinned Hub paginated metadata inventory
(2026-10-16) found 17,448 files, 96 root safetensors,
**188,540,029,444 bytes** for the *entire repo*, and rounded
root weights **174.8553 GiB**. The full repo size is NOT the
minimal serving download, and no tensor headers were inspected.

## A. Source transport and model contract

Physical Wizard 5→23→8 (2026-10-19) showed:
- pinned `resolve` config + launcher: **307** to a same-Hub
  `/api/resolve-cache/` route;
- pinned `raw` config + launcher: **200** with no Location;
- **HEAD only**, no body read; no source content was inspected.

Code now makes the existing Wizard **5→23→7** source audit
read **only** the pinned two `raw` endpoints with a hard-coded
allowlist, **GET/no redirect**, caps
`config.json` at 256 KiB and publisher
`extra/inference/inference_qwen38_flash_next_sglang.sh`
at 128 KiB. A 307 or oversize response still fails.
This cannot download weights, execute the publisher shell,
build/use an image or certify backend compatibility.
Record emitted **SHA256** and specific checks:
`modelopt_mixed`, `MIXED_PRECISION`, every
`linear_attn.in_proj_qkvz` alias explicitly
`MXFP8`, FP8 PLE dtype, and SGLang PLE file-offload
flags. These are declarations only.

**Next:** After mazinb's transfer is complete and physical
source HEAD/worktree are verified, operator runs **5→23→7**,
captures the full bounded output, and compares actual
quantization declarations to the intended adapter.

## B. Single-GB10 memory reality (NOT a peak-RAM prediction)

DGX Spark's nominal unified RAM is 128 decimal GB ≈
**119.2093 GiB**. Root safetensors file bytes at the pinned
revision are ≈ **174.8553 GiB**, i.e. ~55.65 GiB over
nominal capacity before any runtime overhead. The publisher
claims an FP8 PLE backing component of about **47.7 GiB**
(which this project's physical tensor-header audit has
**not confirmed**). Pure subtraction would leave about
**127.1553 GiB** stored, still ~7.95 GiB above nominal RAM
even if this *entire* estimated PLE is offloaded. Thus
"offload PLE" alone is **not** proof that the unchanged
mixed checkpoint fully fits. This is an optimistic arithmetic
screen only: file size, unpacked tensor bytes, page residency,
KV, MTP, host buffers, CUDA graphs and RM transient allocations
are different quantities.

Before any GPU approval, the engineer must present an explicit
on-GPU/CPU/NVMe **per-tensor residency plan**, including:
- BF16 preserved root/crown/attention/shared paths;
  NVFP4 experts, their per-expert scales, and fused
  MXFP8 QKVZ scales;
- actual PLE FP8 shard/scale headers, dimensions and
  mmap/prefetch/eviction semantics;
- KV+MTP/GLA state, prefill transient buffers, quant conversion
  buffers, FlashInfer/CUTLASS caches, CPU page cache and
  OS/non-CMA reserve;
- strict Docker/GPU RM watchdog thresholds, swap/RM activity
  and full-state rollback/forensics after failure;
- a measured or bounded **peak**, not merely steady-state
  or free swap.

Any plan requiring a larger swapfile must independently assess
host and GPU RM safety; swap space is **not** a guarantee
of allocatable GB10 unified physical memory.

## C. Two-engine comparison first — vLLM and SGLang both blocked

An engine is **not selected**. See the [vLLM vs SGLang verified PR/source comparison](CATPLUSPLUS-VLLM-SGLANG-COMPARISON.md) and pinned source tree Wizard 5→23→11. Upstream vLLM UVA CPU-pinned PLE was merged in PR #54371 (Sep 9), but UVA **retains GB10 shared DRAM**. Separate disk-mmap PLE PR #54129 was closed without merge. Existing mazinb vLLM v0.29 cannot be assumed to include either the latest upstream patch or the publisher's mixed MXFP8 fused QKVZ fixes. The publisher's SGLang production launcher is a concrete reference, not a GB10 qualification.

## C. SGLang backend compatibility evidence (BLOCKING)

The publisher's model card attributes the fused QKVZ
scale bug to constructing an unquantized BF16 fused
`in_proj_qkvz` layer and discarding MXFP8 scales.
A YAML/CLI flag or JSON alias alone does NOT establish that
the installed target SGLang executable:
1. selects the correct ModelOpt mixed method with per-layer
   MXFP8 `in_proj_qkvz` and consumes its *actual block scales*;
2. loads the NVFP4 expert layout without reinterpretation
   or silent fallback;
3. handles global FP8 PLE scales under file-backed
   offload, with physical memory commitments in bounds;
4. supports and correctly dispatches Qwen4Exp hybrid
   full attention, GLA recurrent state and MTP on
   **GB10 SM121**, not just the publisher's Thor setup;
5. honors proposed flags in an **exactly pinned ARM64 image**.

`extra/packages/` bundles published by the author are
**not audited/trusted executables**. Do not `source` or run
any upstream script, do not `sudo drop_caches`, do not
`--host 0.0.0.0`, `--trust-remote-code` or use floating
`latest` images to bypass this gate. Investigate a pinned
engine source tree, link exact wheel/image SHA, inspect
the corresponding real qkvz/scale and PLE implementation
without fetching large weights first, then test via
a separately authorized sandboxed loader experiment.

**Current disposition: NO KNOWN QUALIFIED IMAGE OR LAUNCH COMMAND.**
A new catplusplus install/run controller cannot responsibly be
activated until these gates pass. Do not reuse mazinb vLLM
as if it proves mixed precision compatibility.

## D. Download/install staging (FUTURE, not executed)

After mazinb R2 finishes, source declarations and the
pinned GB10 engine have independently passed:
1. Review exact pinned Hub file manifest and determine the
   **minimal loadable checkpoint subset**; never select files
   merely because their names look like unnecessary extras.
   Preserve missing index/weight entries as blockers.
2. Validate free NVMe bytes for **minimal required bytes +
   20 GiB reserve + independently sized offload/cache and
   archive budget**; note the worst-case *complete repo*
   estimate **188,540,029,444 + 21,474,836,480 bytes**.
3. Require no running model/bench or competing lifecycle
   write lock before any operation. The new Wizard
   **5→23→10** only checks an existing global lock and
   worst-case repository/disk bytes read-only; it does not
   reserve space, download or certify installability.
4. Add a new **explicit default-NO bulk download approval**,
   revision + per-file hash manifests, same-destination
   resumability, and separate immutable candidate model dir
   `models/qwen3.8-flash-next-catplusplus-mixed`. It
   MUST NOT alias mazinb/OrcaRouter directories, change
   the existing install profile or trigger automatic GPU start.

## E. Protected service startup (FUTURE, disabled)

Proposed one-shot isolated experiment on
`http://127.0.0.1:18892`, not systemd/boot persistent:
- exact source/pinned image/revision/tensor manifest attested,
  unique trial Docker created only and ID journaled before
  watchdog arm; watchdog live **before** Docker start;
- non-CMA/swap/MemAvailable limits, kernel RM and no running
  predecessor or conflicting API ports checked repeatedly;
- startup has finite timeout and monitor heartbeat;
- exact `/v1/models` name, healthy API, deterministic smoke,
  180-second protected soak, hard-stop if failed;
- postmortem preserves journal/logs/image provenance; never
  broad-prune unrelated Docker objects.

This controller is **NOT IMPLEMENTED** in the repository yet;
Wizard 5→23→3/4/5 deliberately rejects attempted live use.
No host GPU start is authorized by this document.

## F. Comparable llama-benchy and evidence (FUTURE)

Once a *real* separately approved protected catplusplus
API prints a verified READY marker, compare at least
the historical **mazinb M1** standardized protocol:
- pinned `llama-benchy` commit
  `e9be344578cec17745066b220798b80a0d2686d3`;
- PP512/TG128 and PP2048/TG128, depth=0, concurrency=1,
  warmup=1, measured=3; generation latency and caching
  policy matched; start with MTP off as a correctness
  control, record MTP-enabled separately;
- a protected exclusive benchmark lease with pre/post
  model identity, watchdog heartbeat, RM and host-stability
  checks; no benchmark accepted after STOP;
- new independent raw JSON, report
  (`scripts/benchmark/llama-benchy-report.py --profile catplusplus`),
  SHA256 and off-host backup; capture precise source,
  revision, engine/image, actual memory/quant/offload
  configuration and kernel evidence.

**No measured catplusplus benchmark exists.** The publisher
claims 26–35 tok/s on a different Thor system, while the
owner's archived actual mazinb DGX M1 was about
23.11/22.54 tok/s at the two selected workloads; those are
**not** controlled same-machine head-to-head outcomes.

## Current Wizard actions and next evidence

```text
5 → 23 → 7   Source two-file pinned raw GET audit (NO weight download)
5 → 23 → 8   Pinned HEAD-only resolve/raw redirect comparison
5 → 23 → 9   Offline install/loader/memory/benchmark gate plan
5 → 23 → 10  Read-only existing lifecycle-lock and conservative disk screen
5 → 23 → 3/4/5   LIVE/BENCH ADMISSION REMAINS BLOCKED
```

These actions are separate from mazinb Wizard
**3→12** currently downloading; running new bulk
operations on the same host is not authorized. Source-code
CI success does not substitute for real DGX evidence.
