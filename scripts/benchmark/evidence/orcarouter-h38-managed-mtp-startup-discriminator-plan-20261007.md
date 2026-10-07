# H38 MTP startup discriminator plan — 2026-10-07

Status: IMPLEMENTED / STATIC CI PASS / LIVE NOT RUN

## Purpose

The first atomic managed-H38 migration reached the intended decoder-scope H38
candidate but memory protection stopped it before READY. Recovered monitor samples
showed high reclaimable non-CMA available memory, low immediately-free non-CMA
memory, and active swap growth. That signal collides with a known cold-load monitor
false-positive family.

That collision does **not** justify weakening the monitor. Canonical R22 evidence
already proves that a v0.29 PLE-mmap OrcaRouter runtime with the same 16 GiB KV
setting can reach READY and still record a strict NVIDIA RM
`_memdescAllocInternal / NV_ERR_NO_MEMORY` event.

The failed H38 candidate log also places the protection interval near a later
checkpoint-loading phase. Existing normal MTP startup evidence shows a second
safetensors loading pass followed by Qwen3.8 MTP speculator initialization. MTP
materialization is therefore a higher-information next variable than changing host
protection thresholds.

## Single-variable experiment

Runner:

`scripts/benchmark/run-h38-mtp-startup-discriminator.sh`

The runner requires the recovered post-protection managed state to remain unchanged:

- lifecycle transactions idle;
- managed service inactive;
- restored predecessor canonical container present but stopped;
- no rollback container;
- no active API on port 8888.

It never cold-starts the restored legacy runtime.

The isolated candidate preserves:

- image `vllm-orcarouter-v029-h38-decoder-scope:v1`;
- label `qwen38.h38scope=decoder-v1`;
- OrcaRouter checkpoint and served alias;
- PLE mmap;
- exact QSA;
- Marlin canonical order with decoder scope;
- 16 GiB KV;
- max model length 262144;
- max sequences 3;
- prefix cache disabled;
- standard 6 / 2 / 10 / 8 GiB monitor thresholds;
- 256 MiB swap-growth arm;
- five consecutive protection samples;
- `--protect`;
- strict kernel RM classification.

The only intended runtime variable is:

```text
production target: SPEC=mtp, k=2
discriminator:     SPEC=none
```

The experiment uses a distinct container, removes it on completion, and leaves the
managed predecessor in its original stopped state. It does not call `install.sh`,
`update-release.sh`, or mutate managed manifest/release pointers.

## Static validation

- implementation head: `3d4eadcf2ce60c55b600d9e3ecd4143d061355de`;
- GitHub Actions: `37633676272` — SUCCESS;
- shell syntax: PASS;
- ShellCheck: PASS;
- Python compile: PASS;
- unit tests: **587/587 PASS**;
- whitespace: PASS.

The static gate proves the isolated discriminator contract only. It does not advance
managed-H38 FUNCTIONAL or HOST-STABILITY acceptance. Before live execution, the runner
was additionally hardened so its post-start Docker identity proof rejects legacy CPU
offload and requires the matched H38 command shape: GPU utilization 0.80, 8192 max
batched tokens, prefix caching off, FlashInfer autotune off, chunked prefill on, and
async scheduling off. This keeps the intended live delta limited to removal of MTP.

The first operator invocation on 2026-10-08 was **SETUP INVALID / NO CANDIDATE START**.
The recovered predecessor and all lifecycle states were correct, but the harness
incorrectly required manifest `INSTALL_ROOT` to equal the immutable current-release
directory. The installer contract writes `INSTALL_ROOT` as the repository root from
which `install.sh` runs, while the immutable runtime identity is separately represented
by the verified `current` release pointer. Failed atomic refresh recovery correctly
restored that predecessor manifest, so the checkout-root value was expected. The runner
was fixed to verify the immutable current release independently and only require the
restored manifest install root to be a valid repository root. No runtime/container
mutation occurred in this invalid attempt.

## Classification

- `VALID_CLEAN`: SPEC=none reaches exact model READY, Docker OOM is false,
  protection does not intervene, the kernel evidence window is valid, and no strict
  RM OOM appears. This supports MTP startup materialization as the next pressure
  discriminator. It does **not** qualify SPEC=none for production.
- `PROTECTED_STOP`: unchanged protection also stops SPEC=none. MTP is not
  sufficient to explain the startup event.
- `FUNCTIONAL_PASS_HOST_FAIL`: SPEC=none reaches READY but strict RM OOM occurs.
- `FUNCTIONAL_NOT_REACHED_HOST_FAIL`: strict RM OOM occurs before READY.
- anything else: INVALID / no causal claim.

Managed H38 promotion remains blocked until the original MTP k=2 managed target passes
migration FUNCTIONAL/HOST-STABILITY, determinism, performance, and managed
restart/attestation gates.


## 2026-10-08 setup-invalid attempt 02

The corrected-root invocation reached the baseline function but still exited before
the experiment lock, evidence directory, or candidate start. The cause was shell return
semantics in the harness: the final command in `assert_post_protection_baseline` was
`docker inspect EXPERIMENT && fail`. The experiment container being absent is the
required baseline, so `docker inspect` correctly returned non-zero; because that AND
list was the function's final command, the function itself returned non-zero and the
top-level `set -e` exited silently.

This is **SETUP INVALID / NO CANDIDATE START / NO CAUSAL CLAIM**. The fix converts both
negative container-existence guards to explicit `if ...; then fail; fi` checks and
ends the baseline function with explicit `return 0`. No runtime, monitor threshold,
or RM-classification behavior changes.


## 2026-10-08 harness-invalid attempt 03

Attempt 03 reached isolated H38 candidate creation, but the post-start identity validator
was malformed as `python3 ... <<'PY' || fail ...`. Bash here-document parsing consumed
the intended `fail` shell line as Python stdin, producing:

```text
File "<stdin>", line 1
  fail 'H38 SPEC=none candidate identity validation failed'
IndentationError: unexpected indent
```

This construct is especially unsafe for experiment classification because the pending
`||` can bind to the command following the here-document terminator; therefore a
candidate may continue under the monitor while its exact identity proof was skipped.
Attempt 03 is consequently **HARNESS INVALID / NO CAUSAL CLAIM**, even if a later
runtime summary was produced.

The validator is now an explicit `if ! python3 ... <<'PY' ... PY; then fail; fi`
structure. The runner also tracks `IDENTITY_VALIDATED=1` only after the proof
succeeds, records it in evidence, and requires it for `VALID_CLEAN`. Static tests
reject the malformed `<<'PY' ||` pattern.


### Attempt 03 diagnostic timing retained

Although attempt 03 is formally harness-invalid because exact Docker identity was not
attested, its runtime/kernel chronology is retained as non-gating diagnostic evidence.
The launched candidate reported `SPEC=none`, completed 18/18 main-model shards, then
recorded four strict RM `_memdescAllocInternal / NV_ERR_NO_MEMORY` events beginning
about two seconds after the weight-loader completion marker. The first protected-monitor
count followed the first RM OOM rather than preceding it, and the candidate was stopped
at protect 5/5 with about 35 GiB non-CMA available still reclaimable.

This is materially different from the first atomic H38 run, where protection intervened
with no strict RM event in the measured window. It weakens MTP-only causation but remains
non-canonical until the corrected runner proves `identity_validated=1`.
