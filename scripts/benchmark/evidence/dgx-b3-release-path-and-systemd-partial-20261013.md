# Physical DGX immutable release / manifest-root / systemd partial inspection (2026-10-13)

**Evidence class:** physical DGX operator-pasted partial terminal transcript, corroborated against repository sources at exact immutable-release commit. No independently timestamped or byte-identical host archive. This evidence does **not** establish a successful full inspection.

## Operator checkout and observed values

- The user started from `b35d0f3d7840d00c55f4c633813e88ac367c6373` with an explicit SHA assertion and clean-worktree assertion before read-only commands (output reached subsequent commands, so the assertions did not abort this subshell).
- Read-only release status: `CURRENT_RELEASE=ff67bab3c94d6992f61b9535836df97f03b9c022`; `PREVIOUS_RELEASE=a8aeca47433dc4033b3f1f995eb59023467222ce`.
- Resolved immutable release: `/home/inlc/.local/share/qwen38-spark/releases/ff67bab3c94d6992f61b9535836df97f03b9c022`.
- Canonical `install.env` `INSTALL_ROOT=/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark` (mutable source checkout).
- `MODEL_PROFILE=orcarouter`, `VLLM_IMAGE=vllm-skinny-tp1:v1`, expected served identity `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`, `MONITOR_PROTECT=1`, `MONITOR_ENABLED=1`.
- `systemctl show` partially displayed `Result=success`, `User=inlc`, `ActiveState=inactive`, `SubState=dead`, `ExecStart` through `.../current/scripts/service-runner.sh`, and `ExecStop` through direct `docker stop --timeout 30 qwen38-flash-next`.
- Captured terminal ended in a pager: `lines 1-6/6 (END)`. No lifecycle marker loop, completed command marker or aggregate return code was captured. Do **not** mark the whole check complete.

The operator's ad hoc comparison emitted `RELEASE_ALIGNMENT=MISMATCH_STOP` because it compared `INSTALL_ROOT` directly to `current`. **This is not an authoritative lifecycle check and must not be classified as a release/manifest drift failure solely from unequal strings.**

## Exact installed-release source review (GitHub, not a host command)

Source at the actual immutable commit `ff67bab3c94d6992f61b9535836df97f03b9c022` shows:

- Its release update code installs systemd via `manage-service.sh create --runtime-root current`, while the active installation Manifest may preserve an older source checkout as `INSTALL_ROOT`.
- The installed version of `runtime/service-runner.sh` derives its runtime execution root from the immutable service script path. Unlike the newer feature-branch runner, the installed version does not require `INSTALL_ROOT` to equal that release root or perform the newer restored-runtime delegation branch.
- The installed-version service generator emits a direct `ExecStop=-/usr/bin/docker stop --timeout 30 qwen38-flash-next`, matching the partial host output. The newer branch generator instead emits a container-attestation-aware stop helper. The unit shown is therefore **consistent with the installed historical release**, not evidence of a newly updated systemd unit.
- Earlier actual B2 Doctor reported current and previous immutable release integrity/qualification PASS and systemd path pointing at immutable `current`. The present partial host output does not overturn those PASS observations.

There is still a **legacy lifecycle behavior difference** (direct Docker-name stop versus current attested identity-aware stop), which matters for any future managed restart/replacement. Do not patch the systemd unit, hand-edit `INSTALL_ROOT`, regenerate runtime attestation, force recover, refresh H38 defaults or start the old container merely because of the unequal roots.

## Follow-up (safe, bounded)

1. Exit any terminal pager with `q`, without terminating or modifying runtime processes.
2. Complete the **existing** exact-SHA read-only offline snapshot (it already uses `systemctl show --no-pager`) and collect only the unit's `ExecStart`/`ExecStop` and state-marker existence without reading or changing their contents.
3. Interpret stopped-state behavior at the actual installed immutable-release source, not a future checkout's newer service runner.
4. Review exact service identity, rollback/stop boundaries, protections and retained historical protected-stop logs before considering an owner-scoped legacy OrcaRouter live baseline. No live M1 acceptance follows from this partial collection.

```text
ACTUAL_DGX_CHECKOUT=b35d0f3d7840d00c55f4c633813e88ac367c6373
INSTALLED_CURRENT_RELEASE=ff67bab3c94d6992f61b9535836df97f03b9c022
INSTALLED_PREVIOUS_RELEASE=a8aeca47433dc4033b3f1f995eb59023467222ce
INSTALL_ROOT_DIFFERS_FROM_CURRENT=OBSERVED_VALID_WITH_OVERRIDE_POSSIBLE
IMMUTABLE_SERVICE_EXECSTART=OBSERVED
LEGACY_DIRECT_DOCKER_EXECSTOP=OBSERVED
PAGER_BLOCKED_COMPLETE_OUTPUT=YES
B2_DOCTOR=COLLECTED_PARTIAL_5_FAIL_2_WARN
RELEASE_SERVICE_PATH_FOLLOWUP=PARTIAL_READONLY
RUNTIME_STATE_MARKERS_FOLLOWUP=NOT_COLLECTED
M1_LIVE_HOST_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_LIVE_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
HOST_PROTECTION_CONFIGURATION=ENABLED_LAST_OBSERVED
PR_259=DRAFT_OPEN_UNMERGED
```
