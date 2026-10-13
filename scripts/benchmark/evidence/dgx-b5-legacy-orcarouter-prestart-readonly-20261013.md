# DGX B5 legacy OrcaRouter pre-start read-only — actual operator result (2026-10-13)

**Evidence class:** ACTUAL_DGX, user-provided console transcript, not an independently rerun service test. The operator log path is `/home/inlc/dgx-orcarouter-b5-20261013-115949.log`. The GitHub record below is a scoped transcription, **not** an uploaded copy or SHA256 verification of the original on-host log.

## Exact identities and scope

- B5 source checkout: `c2a73179cc2319cac3b7402ac347cdc41572c1df` in a detached Git worktree; same SHA had completed [CI #38339098418](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38339098418) SUCCESS.
- Installed immutable current: `ff67bab3c94d6992f61b9535836df97f03b9c022`.
- Stopped existing Docker predecessor ID: `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`.
- Image `vllm-skinny-tp1:v1`; container exited, not OOM-killed; no rollback-named container.
- Systemd unit `qwen38-flash-next.service`: loaded, **inactive/dead**, result success, `Restart=on-failure`. **ExecStart** uses the immutable current release service runner. Legacy **ExecStop** is `docker stop --timeout 30 qwen38-flash-next`.
- Managed install phase complete, `MONITOR_PROTECT=1`, `MONITOR_ENABLED=1`, dedicated `/swap-ple.img` active. Manifest, ownership, release pointer and source identity remained unchanged.

## Operator-reported pre-start checks

```text
B5_CHECK=installed_release PASS
B5_CHECK=prior_docker_id PASS
B5_CHECK=prior_docker_stopped PASS
B5_CHECK=prior_docker_image PASS
B5_CHECK=prior_docker_not_oom PASS
B5_CHECK=rollback_object_absent PASS
B5_CHECK=managed_unit_stopped PASS
B5_CHECK=complete_manifest PASS
B5_CHECK=MONITOR_PROTECT=1 PASS
B5_CHECK=MONITOR_ENABLED=1 PASS
B5_CHECK=dedicated_swap_active PASS
B5_CHECK=manifest_unmodified PASS
B5_CHECK=ownership_unmodified PASS
B5_CHECK=release_unmodified PASS
B5_CHECK=source_unmodified PASS
B5_READONLY=COLLECTED_READ_ONLY
M1_LIVE=BLOCKED_PENDING_CONTAINER_ID_DECISION_AND_ROLLBACK_PLAN
OLD_DOCKER_ID_SURVIVAL=NOT_GUARANTEED_BY_INSTALLED_SERVICE_RUNNER
H38_LIVE=BLOCKED
```

**15/15 identity and read-only assertions PASS.** No live model loaded and no Docker, systemd, model or swap changes performed.

## Memory/storage point-in-time, not a live stability verdict

```text
MemFree:        81673120 kB
MemAvailable:  123938092 kB
SwapFree:      150001592 kB
CmaFree:           69320 kB
/swap-ple.img: 128G total, 970.1M used, priority 10
/swap.img:      16G total, 0B used, priority -2
/dev/nvme0n1p2: 916G total, 765G used, 105G available, 88% utilization
```

About **118.2 GiB MemAvailable** and **143.1 GiB SwapFree**; these are coarse Linux memory values, **not** proof of contiguous allocations or NVIDIA RM safety. `CmaFree` is about **67.7 MiB**, a point-in-time value, not an RM failure diagnosis. The 105G reported disk headroom is below the external lychee888 model card's ~123.25 GiB checkpoint size even before download overhead. No model download is allowed from this B5 result.

## Acceptance boundary

```text
B5_ACTUAL_DGX_PRESTART_READONLY=PASS
A5_ACTUAL_DGX_WIZARD_DRY_RUN=PASS
LYCHEE888_L0_REAL_HUB_INDEX_JSON=PASS
M1_LIVE_FUNCTIONAL=NOT_QUALIFIED
M1_HOST_STABILITY=NOT_QUALIFIED
M2_DESTRUCTIVE=NOT_RUN
M3_LIVE_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
D0_DISPOSABLE=NOT_GRANTED
```

**Next physical step:** Explicitly resolve the stopped predecessor's **exact container-object ID preservation** and review the installed version's managed transition, stop and rollback paths before a reversible OrcaRouter M1 live test. A successful managed commit may remove the predecessor object. Ordinary rollback/recovery may restart a deliberately stopped predecessor. Never use blind `systemctl restart` or raw `docker start` as a diagnostic substitute. Keep monitor/protect active; strict NVIDIA RM and protected-stop observations remain mandatory. B5 PASS is **not** permission to start.
