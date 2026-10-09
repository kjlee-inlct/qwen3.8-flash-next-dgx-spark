# H38 checkpoint header/order read-only attempt 01 — tempfile preflight INVALID — 2026-10-09

Status: **INVALID / NO CHECKPOINT ORDER OR BUFFER-RISK CLASSIFICATION**. No memory, RM, or functional outcome changed.

## Operator-provided real DGX execution

- Checked-out commit: `551da2c603f2e83c6aedb4668e831e67dae82da6`
- Image: `vllm-orcarouter-v029-h38-decoder-scope:v1`
- Verified image ID: `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`
- Selected canonical model folder:
  `$HOME/models/qwen3.8-flash-next-orcarouter`
- Checkpoint index path exists (shell guard succeeded):
  `model.safetensors.index.json`.
- Original operator-side console log:
  `/tmp/h38-checkpoint-metadata-order.txt`
  (not fetched/uploaded, no claim of its SHA256).
- Runner: `scripts/benchmark/check-h38-checkpoint-metadata-order.sh`.
- CI of original staged implementation: `37822913604` and docs CI
  `37823235881`, both SUCCESS / 620 tests. **CI did not test actual
  UID 65534 + read-only image Python tempfile behavior.**

Original terminal outcome, with exact relevant lines:

```text
H38_CKPT_METADATA_PREFLIGHT=BEGIN
checkout_sha=551da2c603f2e83c6aedb4668e831e67dae82da6
image_id=sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc
scope=read_only_header_and_safe_open_keys_no_tensor_data_no_gpu
H38_CKPT_METADATA_ORDER=INVALID reason=[Errno 2] No usable temporary directory found in ['/tmp', '/var/tmp', '/usr/tmp', '/vllm-workspace']
H38_CKPT_METADATA_PREFLIGHT=INVALID reason=checkpoint_metadata_order_invalid
```

The operator invoked the test within `set -Eeuo pipefail`; the
checker returned INVALID. The trace does not show a
`H38_CKPT_METADATA_ORDER=BEGIN` block, any shard/tensor accounting,
a routed-expert layer order, or a buffer estimate. **Do not infer
missing/corrupt checkpoint shards, valid model-key ordering, or a
materialization failure from this failure.**

## Mechanism and narrowly bounded repair

The original runner deliberately used a read-only root filesystem
(`--read-only`) and an unprivileged UID (`--user 65534:65534`),
without mounting a writable Python temporary directory. The error
indicates Python (or an imported library) could not locate a usable
temporary directory inside the inspector. This is most consistent
with the execution isolation/temporary-filesystem omission;
the exact Python import/call stack was **not** captured, so precise
causality is a hypothesis, not a measured stack trace.

Repair **only** `scripts/benchmark/check-h38-checkpoint-metadata-order.sh`
to add a container-private RAM-backed `/tmp`:

```text
--tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777
--env TMPDIR=/tmp
```

This supplies a bounded writable temp directory exclusively inside
the ephemeral inspector container. Existing `--runtime runc`,
`--network none`, `--read-only`, `--pull never`, UID 65534,
no-new-privileges, all capabilities dropped, memory/pid/CPU caps
and **read-only model checkpoint / source bind mounts** remain.
It does not modify model bytes, host directories, CUDA, vLLM,
the managed model, or external host protection.

Add static regressions requiring exactly one bounded `--tmpfs`
and rejecting a writable model bind, root/GPU/container privilege
escalation. A CI PASS validates these **flags and Python/static
behavior in CI**, not actual source image runtime tempfile
availability. The real DGX repetition must use exactly the newly
pinned/qualified checkout and identical checkpoint and image ID.

## What remains unmeasured

```text
checkpoint_shard_count=UNMEASURED
routed_expert_layer_count=UNMEASURED
checkpoint_name_order=NOT_REACHED
metadata_buffer_scenarios=NOT_REACHED
exact_loader_order_contract=UNVERIFIED
meta_w13_materialization_proven=NO
rm_allocation_reduction_proven=NO
physical_memory_reduction_proven=NO
host_stability=INCONCLUSIVE
```

**No H38 model/allocator run, checkpoint mutation, VM/protection change,
PR Ready or merge is authorized.** A repaired source-only check is
the next justified action, not a GPU/M1/R33 experiment.

## Repair source-level qualification — 2026-10-09

- Fixed-source commit: `d3ff823d3b7c183bb84c53079e25984e321a23e0`.
- GitHub Actions `37882840040`: **SUCCESS / 622 of 622 tests**,
  ShellCheck, shell syntax, Python compile and whitespace PASS.
- **Not yet proved on actual H38 container:** Python tempfile
  usability, shard/index order, 48 routed layer order, hypothetical
  routed-buffer byte scenarios, actual vLLM loader equivalence,
  CT meta materialization, NVIDIA RM demand or host stability.
- Corrected source is staged for a single CPU-only, header-only,
  unchanged-image read-only recheck. Do not reinterpret this CI as
  an H38 checkpoint content PASS.
