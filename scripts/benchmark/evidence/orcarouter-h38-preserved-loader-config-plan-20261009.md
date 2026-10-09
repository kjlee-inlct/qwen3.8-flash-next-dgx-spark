# H38 preserved candidate launch loader-config attestation — staged 2026-10-09

Status: **OFFLINE READ-ONLY ARCHIVE PARSER STAGED / NOT YET EXECUTED AGAINST DGX EVIDENCE**.
Nothing here authorizes a new H38 startup, model, checkpoint, GPU or Docker
operation, monitor/protection relaxation, source patch, R33 or PR merge.

## Why this is the next discriminator

Observed 2026-10-09 H38 installed-source contract **PASS** on the exact
image ID `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`,
recorded at
`orcarouter-h38-installed-loader-source-contract-result-20261009.md`.
The installed code includes default index-backed safetensors iteration
and alternate eager/prefetch/multithread load paths, but no evidence yet
establishes which one the protected H38 candidate **selected**.

The archived exact H38 SPEC=none discriminator Attempt 04 is a valid
`PROTECTED_STOP` with `FUNCTIONAL=NOT_REACHED`,
`HOST-STABILITY=INCONCLUSIVE`, no strict RM OOM in its own valid
window. Canonical historical source:
`orcarouter-h38-managed-mtp-startup-discriminator-attempt04-20261008.md`.

The historical harness
`scripts/benchmark/run-h38-mtp-startup-discriminator.sh` saved,
**before the candidate stopped**, the following files under its
operator-side immutable evidence directory:

```text
/tmp/orcarouter-h38-mtp-none-attempt04-20261007T232026Z/
    candidate-inspect.json
    candidate-cmd.json
    candidate-env.txt
    candidate-container-id.txt
    config.vllm.json
    candidate-container.log
    startup-phase.txt
```

The file list is established from the current harness' capture
implementation and historical evidence path; continued existence of
each file on the actual DGX host is **not confirmed**. Do **not**
recreate any missing file, rerun H38, or infer its contents from the
script. The evidence captured `SPEC=none` and identity
validation passed. The related managed atomic H38 candidate recorded
the `Auto-prefetch is disabled...` startup message; the Attempt 04
summary does **not** independently quote that message. Do not
attribute it to Attempt 04 unless its preserved startup log verifies it.

## New bounded offline tool

`scripts/benchmark/inspect-h38-preserved-loader-config.py`
takes exactly the specified existing evidence directory:
- Reads only `candidate-inspect.json`, `candidate-cmd.json`, and,
  **optionally**, `startup-phase.txt` or `candidate-container.log`.
  No live `docker inspect`, socket, model, weights or GPU access.
- Checks archived `.Config.Image` for the exact tag and archived
  `.Image` for the exact prequalified SHA256 ID. Cross-checks
  `.Config.Cmd` against saved `candidate-cmd.json`, existence of
  the `/model` mount and a four-field H38 runtime-lineage env
  whitelist. No host mount source value is ever printed.
- Extracts only explicitly present CLI options: load format,
  safetensors load strategy/prefetch flags, model-loader extra
  config, tensor/pipeline parallel, expert parallel, executor
  backend and speculative config. Extra JSON config is restricted to
  `enable_multithread_load` / `num_threads`; any other
  keys/values are redacted. Speculative-config JSON values and
  environment secrets are never printed.
- An absent option prints `NOT_EXPLICIT` — **never** guessed
  `auto`, `lazy`, `False`, or a synthesized effective vLLM
  setting. A preserved literal `Auto-prefetch is disabled`
  log marker is reported as a **log observation only**, not a
  proof of all effective prefetch settings.
- Requires bounded JSON files (8 MiB), optional log (1 MiB),
  regular non-symlink capture files, and exact model/source
  lineage. Inability to read or mismatch yields
  `H38_PRESERVED_LOADER_CONFIG=INVALID` / exit 2,
  not a substituted source-only answer.

Guarded runner:
`scripts/benchmark/check-h38-preserved-loader-config.sh`.
It verifies exact SHA + clean repository checkout, an explicit
absolute existing archive directory and then invokes only
`python3 -B`. It does not invoke Docker, systemctl, sudo,
container commands or any memory/protection control.

Synthetic regression:
`tests/test_h38_preserved_loader_config.py` checks absent
flags remain unknown, explicit flags, secret redaction, duplicate
flag rejection, symlink and corrupt archive failures and
non-mutating shell execution.

The diagnostic prints:
`H38_PRESERVED_LOADER_CONFIG_GATE=PASS_ARCHIVED_LAUNCH_FLAGS_ONLY`
if the **archived launch identity and CLI evidence** agree.
Even then:
`actual_effective_vllm_load_config_proven=false`,
`actual_tensor_iteration_proven=false`,
`base_vs_mtp_tensor_io_proven=false`,
`ct_meta_layer_completion_proven=false`,
`safe_peak_weight_buffers_proven=false`,
`host_stability_qualified=false`,
`metadata_order_gate_overridden=false`.

## One-time read-only DGX archive inspection (after CI green)

```bash
(
  set -Eeuo pipefail
  cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark
  git fetch --prune origin
  git switch feat/h38-managed-integration
  git pull --ff-only origin feat/h38-managed-integration

  TARGET="REPLACE_WITH_EXACT_CI_GREEN_HEAD"
  test "$(git rev-parse HEAD)" = "$TARGET"
  test -z "$(git status --porcelain=v1 --untracked-files=all)"

  ARCHIVE_DIR="/tmp/orcarouter-h38-mtp-none-attempt04-20261007T232026Z"
  test -f "$ARCHIVE_DIR/candidate-inspect.json"

  H38_PRESERVED_LOADER_TARGET_SHA="$TARGET" \
  H38_PRESERVED_LOADER_ARCHIVE_DIR="$ARCHIVE_DIR" \
    bash scripts/benchmark/check-h38-preserved-loader-config.sh \
    2>&1 | tee /tmp/h38-preserved-loader-config-attestation.txt
)
```

If the archive no longer exists, record **ARCHIVE_UNAVAILABLE**
and stop; do not change the runtime or regenerate it. The archived
container was removed at the end of the isolated discriminator, so
`docker inspect` of a newly created replacement would not be a
valid substitute.

## Decision after archive inspection

The parser can establish **explicit captured flags**, not the
resolved vLLM `LoadConfig` object, startup defaults or actual tensor
arrival order. Follow-up offline source + event confirmation must
still establish the CT packed `w13_weight_packed` and `w2_weight_packed`
weight-loader element accounting, scale/alias lifetime, deferred
materialization semantics and any additional buffering when base
model layer 8 spans shards 4→5 and layer 11 spans shards 5→6.
`model-mtp.safetensors` retains its separate namespace and
must not be assumed I/O-free solely because the Qwen4Exp
`WeightsMapper` drops `mtp.` assignments.

Do not reinterpret checkpoint `ORDER_GATE=FAIL` as PASS, promote
`HOST-STABILITY`, or propose CT meta implementation from
archived CLI options alone. PR #259 remains Draft/Open.
