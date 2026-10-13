# Actual DGX B4 — stopped legacy OrcaRouter M1 pre-start inventory (2026-10-13)

> Classification: **ACTUAL_DGX operator-provided read-only pre-start output**.
> Date is the conversation observation date, not an independently captured local
> command timestamp. No host changes or runtime launch are established.

## Operator scope and exact identities

The user ran a subshell with `set -Eeuo pipefail`, exact Git HEAD
`b35d0f3d7840d00c55f4c633813e88ac367c6373` and a clean-worktree
assertion; the script reached the final `M1_PRESTART_READONLY=COLLECTED`
sentinel. On-host immutable `current` resolved exactly to release
`ff67bab3c94d6992f61b9535836df97f03b9c022`.

```text
PROFILE=orcarouter
VLLM_IMAGE=vllm-skinny-tp1:v1
SERVED_NAME=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
MONITOR_PROTECT=1
MONITOR_ENABLED=1
IMAGE_ID=sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4
CONTAINER_ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24
CONTAINER_IMAGE=vllm-skinny-tp1:v1
CONTAINER_STATUS=exited
CONTAINER_EXIT=0
CONTAINER_OOM=false
ROLLBACK_CONTAINER=ABSENT
MemFree=81708728 kB
MemAvailable=123938032 kB
SwapFree=150001540 kB
CmaFree=69320 kB
swapon=/swap-ple.img size=128G used=970.1M
swapon=/swap.img size=16G used=0B
SYSTEMD_RESULT=success
SYSTEMD_ACTIVE=inactive
SYSTEMD_SUB=dead
M1_PRESTART_READONLY=COLLECTED
```

Rounded values for readability: MemAvailable **118.20 GiB**, MemFree
**77.92 GiB**, SwapFree **143.05 GiB**, CmaFree approximately **67.70 MiB**.
These are *instantaneous* accounting numbers; they do not prove safe
transient startup/RM behavior.

The earlier B2/B3 actual-host evidence separately confirmed complete
18-shard model index, no active lifecycle transactions/temporary markers,
and the inactive historical unit with direct Docker-name ExecStop.
The present B4 command **did not recheck those transaction/marker states,
runtime-commit attestation, service unit text, model mount identity,
inference readiness, strict RM event window or dedicated `SWAP_FILE`
Manifest equality**. The presence of `/swap-ple.img` in `swapon`
does not by itself prove equality with canonical `SWAP_FILE`.

## Installed immutable release source analysis — not a new host measurement

The exact installed source at `ff67bab3c94d6992f61b9535836df97f03b9c022`
has a `service-runner.sh` that executes a **mutating** runtime transaction:
preflight, recover, prepare, model run, candidate validation and commit.
If a previous container exists, `runtime-transition.sh prepare`
renames it to a rollback object; after health/served-name acceptance,
`commit` **deletes the previous rollback container**. A normal
failure/rollback or some recovery paths **may start the old container**
even if it was previously intentionally stopped. The explicit memory
protection abort instead restores the predecessor left **stopped**.
The historical installed unit uses Docker-name-based ExecStop.

An important version-specific distinction: the installed release's
`monitor-runtime.sh` source evaluates low non-CMA free **AND** low
non-CMA available, or a swap-free floor, with the configured number of
consecutive samples. It does **not** show the swap-growth arm seen
in the archived October 7 candidate monitor trace. Never project the
candidate monitor's exact code/thresholds onto this installed legacy
release without establishing the running script identity.

The installed release's `preflight-runtime.sh` checks model index,
image existence, configured swap activation and minimum available
memory/swap/disk margins; this is not an assurance against the historical
transient >75 GiB first-construction allocation burst or strict NVIDIA RM
allocation errors.

## Decision and next actions

```text
B4_IMMUTABLE_RELEASE=PASS
B4_PROFILE_IMAGE_CONTAINER_IDENTITY=PASS_READONLY_AT_OBSERVATION
B4_OLD_CONTAINER_STOPPED=OBSERVED
B4_ROLLBACK_NAME=ABSENT_AT_OBSERVATION
B4_MEM_SWAP_POINT_IN_TIME=COLLECTED
B4_HOST_CHANGE=NONE
B4_MODEL_LOAD=NOT_RUN
B4_STRICT_RM_HOST_STABILITY=NOT_MEASURED
LEGACY_EXACT_ID_REVERSIBILITY=NOT_GUARANTEED
M1_LIVE_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_LIVE_ALL_PROFILE_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
D0_INDEPENDENT_DISPOSABLE=NOT_GRANTED
PR_259=DRAFT_OPEN_UNMERGED
```

A later legacy OrcaRouter managed M1 experiment must first choose whether
losing **this exact previous container object/ID** after healthy commit is
in scope. If that object must survive, the existing release's managed
start path **does not meet the reversibility condition**: do not launch it.
Before any owner-scoped actual start: verify immutable manifest/unit and
exclusive Docker name/port/operation lock ownership, the active `SWAP_FILE`,
current monitor policy, service restart semantics, disk/headroom, sampled
NVIDIA RM/kernel event baseline, limited readiness window, and an explicit
STOP/rollback plan that does not manually defeat memory protection. No
raw Docker start, no blind systemd restart, no H38 image refresh, no
disposable-host admission, no PR Ready/Merge.
