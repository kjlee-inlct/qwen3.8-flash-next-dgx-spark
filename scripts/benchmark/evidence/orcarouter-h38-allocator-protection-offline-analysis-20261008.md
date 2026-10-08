# H38 protected-stop attempt 01 — full-history offline allocator analysis — 2026-10-08

Status: **COMPLETED READ-ONLY OFFLINE ANALYSIS** of the valid production-shape
H38 attempt 01, not a new DGX experiment.

## Provenance and evaluation boundary

- Original run: `SPEC=mtp k=2`, KV 16 GiB, exact candidate identity,
  executed at SHA `2e7aff15b03ffa49cb9aafd8cf688c140891c1e7`.
- Formal run result: `PROTECTED_STOP`; `FUNCTIONAL=NOT_REACHED`;
  `HOST-STABILITY=INCONCLUSIVE`; `rm_oom_count=0`;
  `OOMKilled=false`; kernel/collector/analyzer valid.
- Event: **2026-10-08 02:06:47 UTC / 11:06:47 KST**.
- Preserved original host directory:
  `/tmp/orcarouter-h38-allocator-protection-20261008T015824Z`.
- Operator-provided original archive:
  `h38-allocator-attempt01-evidence.tar.gz`, **274,967 bytes**, SHA256
  `cb0e3d03ac20eb49ce095df23807550415ffa1cfccf1679e84d4ba6ea6875818`.
- The archive contains the actual full `allocator-trajectory.csv`,
  `allocator-analysis.txt`, `monitor-protection-window.txt`,
  timestamped `startup-phase.txt`, and **raw** allocator fast/slow state
  files. The raw archive remains outside the Git repository; this document
  records computed findings and its original SHA256, not a fabricated
  historical host path.
- Reproducible read-only analyzer:
  `scripts/benchmark/analyze-h38-allocator-attempt-archive.py`;
  synthetic regressions:
  `tests/test_h38_allocator_attempt_archive.py`.

The event-aligned CSV has **651 rows**: fast 542 (1 s), slow 109 (5 s).
Only **502 fast and 101 slow** samples at or before the protection event
are used in pre-event calculations. The **40 fast and 8 slow** samples
captured after the monitor event (including graceful shutdown) are
excluded from all pre-protection maximum-drop and phase conclusions.
The first observed fast sample was 01:58:25.196146Z, approximately
501.804 s before protection.

The matching raw fast-state samples and derived CSV timestamp/MemFree
values were cross-checked. MiB uses 2^20 bytes, page size 4 KiB,
node 0, Normal zone, orders >=4. Snapshot quantities alone do not
establish contiguous allocation success or page ownership.

## The first, dominant high-order and physical-free collapse

At 01:58:25.196Z, the initial observed node0 Normal order-4+
reservoir was **76,787.500 MiB**, including Unmovable
**74,740.250 MiB** (near-synchronous slow sample).

**Largest continuous five-second decrease**:
`01:59:02.196334Z -> 01:59:07.196252Z`
(**10:59:02.196 -> 10:59:07.196 KST**).

| Independent metric over this same 5 s | Start MiB | End MiB | Change MiB |
|---|---:|---:|---:|
| node0 Normal order-4+ | 74564.125 | 55.375 | **-74508.750** |
| node0 Normal total free pages | 75824.715 | 667.461 | **-75157.254** |
| global MemFree | 76309.578 | 1151.914 | **-75157.664** |
| MemAvailable | 117735.785 | 41577.164 | **-76158.621** |
| SwapFree | 146478.875 | 146478.875 | **0.000** |

The sharpest individual one-second order-4+ drop was
**-24,958.750 MiB**, 01:59:04.196349Z -> 01:59:05.196269Z,
from 36,599.062 to 11,640.312 MiB. This is a direct allocator
trajectory finding, not inferred from the monitor's later warning.

Initial-relative threshold crossings (observed, not predictive
protection thresholds):

| Node0 Normal reservoir | First below 50% | First below 10% / 1% |
|---|---|---|
| Aggregate order-4+ | 01:59:04.196Z, 36599.062 MiB | 01:59:06.196Z, 120.000 MiB |
| Unmovable order-4+ | 01:59:05.197Z, 11277.750 MiB | 01:59:10.197Z, 60.062 MiB |

The largest five-second **slow** Unmovable order-4+ decrease was
**-63,443.312 MiB**, 01:59:00.196688Z -> 01:59:05.196636Z,
from 74,721.062 to 11,277.750 MiB. The next slow sample at
01:59:10.196613Z observed only 60.062 MiB Unmovable order-4+.

Thus the initial ~75 GiB high-order exhaustion happens **about
7 min 40 s before the eventual protected stop**, not primarily in
the 11:06:37-47 last-second protection window. The later low-free
and swap-growth sequence is a separate later pressure interval.

## Independent physical-page accounting (R21/R22 methodology)

The conserved *approximate* core residual is

`core_unexplained_growth = MemFree_loss - core_accounted_growth`

where core accounted growth uses the **non-overlapping** meminfo
categories: Active/Inactive anon and file LRU, Unevictable, Slab,
non-slab `max(0, KReclaimable-SReclaimable)` excess, PageTables,
SecPageTables, and KernelStack. Overlapping `Cached`, `AnonPages`,
and Slab child fields are not independently added.

**Same exact largest-five-second window**:

- Global MemFree loss: **75,157.664 MiB**.
- Conservatively accounted conventional resident growth:
  **396.148 MiB**.
- Resulting approximate **core unexplained physical free-page loss:
  +74,761.516 MiB**.
- Node0 Normal physical free-page loss: **75,157.254 MiB**,
  approximately matching global free-page loss.
- SwapFree change: **0.000 MiB**.

The calculation explicitly includes Linux fields with parenthesized
names such as `Active(anon)`, `Inactive(anon)`, `Active(file)`,
and `Inactive(file)`. An initial ad-hoc parser used `\w+` key
matching and mistakenly omitted these four fields, yielding a
**superseded 74,542.438 MiB residual**. That figure is **invalid**.
The corrected value 74,761.516 MiB comes from full-key parsing, was
recomputed over every raw sample, and its maximum five-second increase
coincides exactly with the maximum Normal order-4+ decrease above.

This is still an approximate *accounting residual*, not an exact
NVIDIA-owned memory measurement. Nothing here independently
attributes the allocation to a specific RM/UVM call or model tensor.

## Timestamped checkpoint phase boundary: correction to attempt 01

The original summarized startup-phase excerpt showed `15/18` without
preserving the timestamp relation to the protection event. The raw
`startup-phase.txt` includes precise timestamps:

| Timestamp UTC | Recorded event | Relation to protection |
|---|---|---|
| 01:59:06.0616 | worker checkpoint message: EXT4, checkpoint 170.88 GiB, available RAM 40.78 GiB | ~7m41s before |
| 01:59:06.0621 | shard progress 0/18 | ~7m41s before |
| 01:59:43.0019 | first shard completed, 1/18 | ~7m04s before |
| 02:06:24.2269 | shard 14/18 completed | ~22.77s before |
| **02:06:47.0000** | **monitor PROTECT stop** | **event** |
| 02:06:53.9451 | shard 15/18 logged | **6.95s AFTER stop signal** |

**Correction:** the last *logged completion before protection* was
**14/18**, not 15/18. The post-event 15/18 message can occur while
graceful shutdown is being processed. It must not be backdated to
the monitor trigger.

The dominant high-order collapse overlaps the **initial 0/18
loading stage**, starting ~3.87 s *before* the 01:59:06.062 worker
shard-progress marker and finishing ~1.13 s after it. The first
shard completion follows another ~35.81 s later. Therefore it is
false to attribute the initial burst to loading shard 15 or to
the late protection window. This time correlation does **not**
prove whether the initial allocation is NVIDIA RM, UVM, model
metadata mapping, memory pool initialization, or another common
initialization path; that ownership boundary remains unresolved.

## Matched-scale (not matched-phase) R21/R22 comparison

Previously accepted **valid** reference results:

| Metric | R21 legacy offload | R22 mmap | H38 protected MTP k2 |
|---|---:|---:|---:|
| Largest 5 s core-unexplained residual growth (MiB) | 75174.387 | 75138.043 | **74761.516** |
| Difference from H38 (MiB) | 412.871 | 376.527 | 0 |
| H38 five-second Normal order-4+ drop (MiB) | — | — | 74508.750 |
| H38 5 s SwapFree change (MiB) | — | — | 0.000 |

R21/R22 reference measurements used a different **post-compaction
starting state**, different runtimes and at least one different
offload configuration. The H38 initial observed Normal order-4+
reservoir was ~76.8 GiB, versus approximately 119.7 GiB for prepared
R21 and 117.2 GiB for prepared R22. Matching the five-second
*residual scale* to within 0.6% is strong evidence of a
reproducible common **host free-page pressure pattern**, not proof
of identical tensor allocation, page owner, model loading step,
or safety outcome. The strict-RM-failure snapshots for R21 and R22
were **post-failure**, potentially affected by RM rollback; the
H38 observations are **pre-protected-stop**. Never treat these as
interchangeable thresholds.

R21/R22 eventually observed strict `_memdescAllocInternal` /
`NV_ERR_NO_MEMORY` failures, while H38 attempt 01 was stopped
by the unchanged monitor with **zero** strict RM events. The observed
H38 event remains `HOST-STABILITY=INCONCLUSIVE`, not PASS and
not FAIL.

## Engineering conclusion and next authorized work

1. **R21/R22-scale early 5 s physical-page burst is confirmed in
   production-shape H38 as well**, independent of meaningful
   contemporaneous swap consumption.
2. Approximately 75 GiB of node0 Normal free/high-order reservoir
   disappears around initial model-load/worker initialization;
   the observed source is not yet attributable to one NVIDIA
   allocation or model-shard operation.
3. The much later stop was a real active memory protection intervention:
   non-CMA free ~1.3 GiB, swap-growth 717 MiB over five consecutive
   warnings; no strict RM error was observed during the valid window.
4. Keep PR #259 Draft/Open; do not weaken memory protection,
   re-run unchanged H38, promote managed lifecycle, or merge.
5. The next *information-gaining* step, if approved, is **targeted
   observational attribution at the initial 01:59:02-07Z-equivalent
   common loading boundary** using existing R9-R32 results and
   narrowly scoped source/instrumentation review. Existing evidence
   must be exhausted before proposing another host experiment.

Reproduction on any copy of the original archive, no host mutation:

```bash
python3 scripts/benchmark/analyze-h38-allocator-attempt-archive.py \
  --archive /path/to/h38-allocator-attempt01-evidence.tar.gz \
  --json-output /tmp/h38-attempt01-offline-result.json
```

This command only reads the original archive and optionally writes a
local JSON analysis; it does not start a container or change protection.

## Offline implementation/static qualification — 2026-10-08

The reproducible analyzer and synthetic regressions were committed as
`a9f4ec6658653b49cf908b567aea608e831313d6`.
GitHub Actions workflow `37744164668`: **SUCCESS; 599/599 unit tests**,
shell syntax, ShellCheck, Python compilation, whitespace PASS. The three
new regression cases cover parenthesized meminfo keys, strict exclusion
of post-protection samples and shard messages, and rejection of
misaligned CSV event offsets. This CI is independent static validation;
no DGX live test or managed runtime qualification is inferred.
