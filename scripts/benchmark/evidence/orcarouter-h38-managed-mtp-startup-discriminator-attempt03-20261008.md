# H38 MTP startup discriminator attempt 03 — 2026-10-08

Status: HARNESS INVALID / CANDIDATE START REACHED / NO CAUSAL CLAIM

## Invocation

- branch: `feat/h38-managed-integration`
- exact checkout: `b177f815059c2bdc967434812f7b4ba4c774555b`
- evidence target:
  `/tmp/orcarouter-h38-mtp-none-attempt03-20261007T224704Z`

The required stopped managed baseline and all lifecycle-idle checks passed. The runner
acquired its operation lock, generated the vLLM config, and reached:

```text
===== start isolated H38 candidate with SPEC=none =====
```

Therefore this was the first discriminator invocation to create the isolated H38
candidate.

## Harness defect

Immediately after candidate creation, the identity validator emitted:

```text
File "<stdin>", line 1
  fail 'H38 SPEC=none candidate identity validation failed'
IndentationError: unexpected indent
```

The runner used the malformed construct:

```bash
python3 - ... <<'PY' ||
  fail 'H38 SPEC=none candidate identity validation failed'
...
PY
```

With Bash here-document parsing, the intended `fail` command became the first line of
Python stdin. The pending OR operator can then bind to the command following the
terminator, which means subsequent monitor/runtime behavior is not evidence from a
properly identity-attested experiment.

## Correction

The identity validator is now expressed as:

```bash
if ! python3 - ... <<'PY'
...
PY
then
  fail 'H38 SPEC=none candidate identity validation failed'
fi
```

In addition, the runner now:

- initializes `IDENTITY_VALIDATED=0`;
- sets it to `1` only after the full Docker identity proof succeeds;
- persists that value in the summary/evidence;
- requires `IDENTITY_VALIDATED=1` before `VALID_CLEAN`;
- statically rejects the malformed `<<'PY' ||` pattern.

## Classification

- candidate creation: REACHED
- exact candidate identity: NOT PROVEN
- FUNCTIONAL: INVALID FOR GATE
- HOST-STABILITY: NOT ACCEPTABLE FOR GATE
- MTP causal claim: NONE

Any runtime or protection observation from this attempt may be retained only as
diagnostic context, not as managed-H38 acceptance evidence.


## Retained diagnostic observations from the invalid run

The identity-attestation defect prevents this run from becoming a formal discriminator
result, but the observed runtime/kernel sequence is still useful diagnostic evidence.

The isolated candidate reported:

```text
started qwen38-h38-mtp-none
profile=orcarouter
executor=mp
PLE=mmap
SPEC=none
qsa_exact_topk=1
maxlen=262144
util=0.80
```

Checkpoint loading completed all 18 main-model shards. Relevant chronology:

```text
07:56:00.656  Loading weights took 493.49 seconds
07:56:02.678  NV_ERR_NO_MEMORY from _memdescAllocInternal
07:56:02.701  NV_ERR_NO_MEMORY from _memdescAllocInternal
07:56:02.710  NV_ERR_NO_MEMORY from _memdescAllocInternal
07:56:03       monitor protect=1/5
07:56:04.554  NV_ERR_NO_MEMORY from _memdescAllocInternal
07:56:11       monitor protect=5/5 -> PROTECT stop
07:56:13.243  Model loading took 71.72 GiB memory and 509.775746 seconds
```

The monitor remained healthy through most of the 18-shard load. Immediately before
the stop, non-CMA available remained about 35 GiB, non-CMA free was about 1.3-1.5 GiB,
and swap growth was 501 MiB. The strict RM failures therefore preceded the protective
stop. In this invalid run, protection was not the first event that prevented an
otherwise clean startup.

The runner summary observed:

```text
api_ready=0
oom_killed=false
kernel_window_rc=0
rm_oom_count=4
protected_stop=1
result=FUNCTIONAL_NOT_REACHED_HOST_FAIL
```

Because `IDENTITY_VALIDATED` did not exist in this runner revision and the validator
itself was malformed, these fields remain diagnostic observations only and are not
promoted to a formal MTP-discriminator classification.

### Diagnostic interpretation

This materially weakens the hypothesis that MTP materialization is the sole cause of
the H38 startup RM event:

- the launched command reported `SPEC=none`;
- all 18 main checkpoint shards completed;
- no MTP/speculator initialization marker was observed;
- strict RM `_memdescAllocInternal / NV_ERR_NO_MEMORY` appeared immediately after
  main weight loading and before the protection counter began accumulating.

The corrected identity-attested rerun remains required. If it reproduces strict RM OOM
with `identity_validated=1`, MTP-only causation is rejected and investigation should
return to the H38 core/main-model startup allocation path rather than monitor tuning or
MTP materialization.
