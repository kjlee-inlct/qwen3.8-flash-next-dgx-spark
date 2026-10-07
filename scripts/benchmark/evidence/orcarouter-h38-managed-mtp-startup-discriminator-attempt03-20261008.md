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
