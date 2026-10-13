# Managed lifecycle read-only operator Attempt 01 — PARTIAL_CHECK_FAILURE (2026-10-12)

## Provenance and actual verdict

This is the **actual DGX Spark operator-pasted** read-only inventory/transaction status/Doctor stdout, not synthetic CI. The reported original operator logfile `/tmp/managed-lifecycle-readonly-attempt01-20261012.txt` was **not copied to GitHub byte-for-byte or independently SHA256-hashed**. This file transcribes only supported values from the supplied terminal output.

- Branch `feat/h38-managed-integration`, fast-forward `956ee0c..bbeceaf`, clean exact execution HEAD **`bbeceaf16c0c4bba4385c38cfead32e5dc243769`**.
- `QWEN38_LIFECYCLE_AUDIT_TARGET_SHA` bound to the checkout; the canonical read-only lifecycle inspector executed seven read-only commands (entry point documented in `OPERATIONS.md`).
- `MANAGED_LIFECYCLE_READONLY_PREFLIGHT=BEGIN`, `scope=read_only_inventory_transaction_status_doctor_no_mutation`, `host_mutation=NO`, `model_or_gpu_launch=NO`, `no_install_uninstall_or_purge=YES`.
- `MANAGED_LIFECYCLE_READONLY=PARTIAL_CHECK_FAILURE`, `MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED`, **`lifecycle_audit_rc=3`**.
- The wrapper reached its final result. The **Doctor failed**; this is not a wrapper crash and must not be converted to `COLLECTED_READ_ONLY` or M1 host-healthy PASS.

## Read-only inventory recorded (model discovery, not ready-to-serve)

| Registry profile | Registry qualification | Installable | Local model | Active | Local image |
|---|---|---|---|---|---|
| `orcarouter` | stable | yes | installed | yes | present |
| `nvidia` | experimental | yes | absent | no | absent |
| `mazinb` | experimental | yes | installed | no | present |
| `orcarouter-hybrid` | experimental | yes | installed | no | present |
| `lychee888` | planned | no | not-installable | no | not-applicable |

Active `orcarouter` checkpoint reported `/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models/qwen3.8-flash-next-orcarouter`, 18 referenced shard files; the wrapper did **not** load those model tensors. Backend registry: `vllm stable/installable=1`, `sglang planned/installable=0`. Both registry commands **rc=0**.

## Four transition states, all idle

```text
PROFILE_SWITCH_STATE=idle
TRANSACTION_STATE=idle
UPDATE_STATE=idle
RELEASE_PROFILE_REFRESH_STATE=idle
```

Each status command returned **rc=0**. No pending/incomplete named transition was reported. This proves **those four status checks** are idle; it does not certify runtime health, all possible artifacts, or that service restart is safe.

## Doctor's five failures and two warnings — preserved without corrections

```text
[FAIL] runtime commit attestation is missing or unsafe (/home/inlc/.local/state/qwen38-spark/runtime-commit.env)
[FAIL] container state is exited
[FAIL] API port is not loopback-only: no published port
[FAIL] memory protection monitor PID file is missing
[FAIL] health endpoint does not respond
[WARN] managed OrcaRouter still uses a legacy image; run --refresh-profile-defaults after the immutable release update
[WARN] systemd service exists but is inactive
Summary: 5 failure(s), 2 warning(s)
READONLY_CHECK=doctor_readonly rc=1
```

This is a **service/container stopped or unhealthy observation**, not proof that the image itself is defective, that a memory-protection trip occurred, or that restarting the model is allowed. In the checked-in Doctor source, absent/stopped runtime can create correlated API-port and health failures. A missing monitor PID may be consistent with an inactive service; the reason remains unobserved. The literal `no published port` comes from `docker port` in the doctor and is not yet an independent claim that `HostConfig.PortBindings` is wrong. The attestation is absent **or unsafe** — the transcript does not distinguish missing file, symlink, or unreadable path.

### Doctor positives relevant to diagnosis

- Installation manifest `complete`, supported profile and pinned repo/revision, valid cumulative asset ownership registry, no unfinished update/runtime/profile-switch/release-refresh transactions, no pending runtime adoption.
- Current immutable release verification **`ff67bab3c94d6992f61b9535836df97f03b9c022`**, previous release verification **`a8aeca47433dc4033b3f1f995eb59023467222ce`**, current release qualification digest match and systemd points at immutable release.
- Managed API socket active; Docker-app listener port `8000`; LAN listener `10.221.50.65:8000`; Docker daemon/image present. API-access socket existence does not override missing runtime health.
- Model index present, 18 referenced shards complete, checkpoint manifest complete, vLLM config compatible.
- Dedicated `/swap-ple.img` active; non-CMA available **118 GiB** (CmaFree=0), non-CMA free **80,045 MiB**, swap free **143 GiB**, model filesystem free **104 GiB**. These are a point-in-time Doctor snapshot, **not strict RM host stability qualification**.
- Existing stopped container's image, model mount, served name and `--init` configuration match the install manifest.
- Service is `enabled` but **inactive**; container state **exited**; legacy OrcaRouter runtime image remains present and selected.

The historical strict `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`, `RM_MITIGATION=UNPROVEN` for H38 managed acceptance are unchanged.

## Safe next discriminator (no restart/mutation)

Before any runtime operation, determine **why the pre-existing legacy runtime is exited** and whether it was deliberately stopped during protective handling, versus failed/stale service state:

1. read-only `docker inspect` fields only for current container status/exit code/OOMKilled/start/finish times and declared port bindings (never `docker start`, `run`, `rm`);
2. read-only `systemctl show` fields (ActiveState/SubState/Result/ExecMainStatus) and bounded service journal (no `systemctl restart`);
3. check existence/type of `runtime-commit.env`, `runtime-stop.env`, `monitor.pid` **without sourcing or editing** state files, and inspect reason fields only when safe/authorized;
4. compare timestamps and ownership with the currently verified immutable release; if cause remains ambiguous, **keep FAIL/UNKNOWN and stop**.

Do not delete/restore `runtime-commit.env`, force a transition commit, alter monitor/protection, run `install.sh --refresh-profile-defaults`, start any H38 GPU/model, modify manifests, run `uninstall.sh`, or promote PR #259. This diagnostic stage can be run while H38 runtime stays BLOCKED.

## Gates at close of this observation

```text
LIFECYCLE_M1_REGISTRY=OBSERVED_READ_ONLY_PASS
LIFECYCLE_M1_TRANSITIONS=OBSERVED_READ_ONLY_IDLE_4_OF_4
LIFECYCLE_M1_DOCTOR=FAIL_5_WARN_2
LIFECYCLE_M1_OVERALL=PARTIAL_CHECK_FAILURE
LIFECYCLE_M1_LIVE_HOST_HEALTH=NOT_QUALIFIED
LIFECYCLE_M2_DESTRUCTIVE_E2E=NOT_RUN
LIFECYCLE_M3_ALL_PROFILE_SWITCHES=NOT_QUALIFIED
LIFECYCLE_M4_H38_MANAGED=BLOCKED
LEGACY_RUNTIME_EXIT_CAUSE=UNVERIFIED
RUNTIME_COMMIT_ATTESTATION_CAUSE=UNVERIFIED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
HOST_STABILITY=INCONCLUSIVE
GPU_MODEL_RERUN=BLOCKED
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN
MERGE=BLOCKED
```
