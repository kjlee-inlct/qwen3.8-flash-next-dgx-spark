# ACTUAL_DGX — OrcaRouter Legacy A protection stop CONFIRMED — 2026-10-13

**Observed from real operator uploaded diagnostic**
`붙여넣은 텍스트(1)(20261013-094152).txt` with
actual trial source SHA
`48c517357cef2182be986c298a86ddfa1f4c74b0`.
This supersedes the earlier *possible* protective-stop
hypothesis in
[initial exit-137 record](dgx-orcarouter-legacy-a-exit137-20261013.md);
it does not supersede the original file or discard any logs.

## Pinned Docker lifecycle

| Field | Legacy A candidate | protected managed predecessor |
| --- | --- | --- |
| Exact ID | `57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56` | `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24` |
| State | `exited` | `exited` |
| Start (UTC) | `2026-10-13T08:58:06.343683697Z` | `2026-10-07T07:35:45.800732164Z` |
| Finish (UTC) | `2026-10-13T09:00:10.251998976Z` | `2026-10-07T13:08:34.847184942Z` |
| ExitCode | **137** | **0** |
| OOMKilled | **false** | **false** |

## Exact monitor protection evidence

```text
2026-10-13 17:58:07 monitor started: container=qwen38-ab-legacy mode=protect available-warn=6GiB noncma-free=2GiB free-gate=10GiB swap-growth=256MiB swapfree=8GiB
2026-10-13 17:59:04 WARNING memory margin low protect=0/5: available=39579MiB noncma_available=39511MiB free=1626MiB cmafree=67MiB noncmafree=1558MiB swapfree=146488MiB swapgrowth=0MiB
2026-10-13 17:59:08 memory margin recovered: available=35387MiB noncma_available=35319MiB free=2238MiB cmafree=67MiB noncmafree=2170MiB
2026-10-13 17:59:10 WARNING memory margin low protect=1/5: available=34745MiB noncma_available=34677MiB free=1257MiB cmafree=67MiB noncmafree=1189MiB swapfree=144201MiB swapgrowth=2286MiB
2026-10-13 17:59:12 WARNING memory margin low protect=2/5: available=33668MiB noncma_available=33601MiB free=1382MiB cmafree=67MiB noncmafree=1314MiB swapfree=143026MiB swapgrowth=3461MiB
2026-10-13 17:59:14 WARNING memory margin low protect=3/5: available=31513MiB noncma_available=31446MiB free=1731MiB cmafree=67MiB noncmafree=1663MiB swapfree=143023MiB swapgrowth=3465MiB
2026-10-13 17:59:16 WARNING memory margin low protect=4/5: available=29793MiB noncma_available=29726MiB free=1914MiB cmafree=67MiB noncmafree=1846MiB swapfree=142592MiB swapgrowth=3895MiB
2026-10-13 17:59:18 memory margin recovered: available=29041MiB noncma_available=28973MiB free=2154MiB cmafree=67MiB noncmafree=2087MiB
2026-10-13 17:59:27 WARNING memory margin low protect=1/5: available=23687MiB noncma_available=23619MiB free=2069MiB cmafree=67MiB noncmafree=2001MiB swapfree=140538MiB swapgrowth=5949MiB
2026-10-13 17:59:29 WARNING memory margin low protect=2/5: available=20415MiB noncma_available=20347MiB free=970MiB cmafree=67MiB noncmafree=902MiB swapfree=139697MiB swapgrowth=6790MiB
2026-10-13 17:59:32 WARNING memory margin low protect=3/5: available=21788MiB noncma_available=21721MiB free=975MiB cmafree=67MiB noncmafree=907MiB swapfree=136785MiB swapgrowth=9703MiB
2026-10-13 17:59:34 WARNING memory margin low protect=4/5: available=23073MiB noncma_available=23005MiB free=983MiB cmafree=67MiB noncmafree=915MiB swapfree=134189MiB swapgrowth=12298MiB
2026-10-13 17:59:36 WARNING memory margin low protect=5/5: available=23231MiB noncma_available=23163MiB free=982MiB cmafree=67MiB noncmafree=914MiB swapfree=132391MiB swapgrowth=14096MiB
2026-10-13 17:59:36 PROTECT stopping qwen38-ab-legacy gracefully to preserve host stability
```

```text
RUNTIME_STOP_SCHEMA_VERSION=1
STOP_REASON=memory-protection
STOP_CONTAINER_NAME=qwen38-ab-legacy
STOP_CONTAINER_ID=57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56
UPDATED_AT=2026-10-13T08:59:36Z
```

This is **confirmed** watchdog protection action. The final
protect predicate is low immediate non-CMA `914MiB`,
low-free floor `2GiB`, with swap activity growth
`14,096MiB` over 256 MiB trigger; `noncma_available`
is ~22.6 GiB, not under the 6 GiB warning floor.
The recorded 30+ seconds after `PROTECT stopping` to
Docker Finish and ExitCode 137 is consistent with
`docker stop --timeout 30` culminating in SIGKILL.
This cannot establish which process received signal first,
or prove NVIDIA RM/kernel OOM. `OOMKilled=false`;
the owner displayed no NVRM/Xid matches in filtered kernel
journal. This is not a model inference or speed failure;
the model never reached READY, and no bench data exists.

## Journal reconciliation issue discovered

Both original per-trial and active manifest journal had
`phase=started_unqualified` after asynchronous watchdog
protection stopped the actual Docker object. The source
initially required `phase=stopped` before proceeding to B.
A source update makes wizard **status (menu 6→1)**
read-only and truthful about actual Docker state, code 137,
forensic memory stop and reconciliation-needed flag.
The operator may later use wizard **6→4** to reconcile
already stopped A (strict exact-ID, old predecessor
status/image, immutable release and manifest checks);
this is a state-record update only, **no Docker stop**
when candidate is already exited, and preserved
`runtime-stop.env` remains untouched. This code must
be verified by CI and cannot retroactively alter past logs.

## Scope / next action

Keep protection thresholds, swap and original stopped
managed Docker intact. **Do not delete or rerun Legacy A**
and do not infer an A throughput value. The v0.29 B image
uses a different PLE mmap runtime rather than Legacy's CPU
PLE offload; it may reduce memory loading pressure but
is not physically qualified to do so. Review and
preserve all Legacy logs/checksums. After source CI,
use the wizard to reconcile A and check B read-only
admission again, then explicitly approve a monitored
B load trial if host safety gates remain green.
Any B protective stop is useful evidence and blocks
benchmark; do not weaken monitor. PR #259 Draft/Unmerged.
