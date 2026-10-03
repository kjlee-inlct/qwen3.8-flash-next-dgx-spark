# OrcaRouter managed RM-sysmem R10 invalid attempt — 2026-10-03

## Classification

- Experiment validity: **INVALID / NO MANAGED RUNTIME RESTART**
- Functional classification: **NOT APPLICABLE**
- Host-stability classification: **NOT APPLICABLE**
- RM-sysmem conclusion: **NONE — the capture never reached model startup**

The first managed OrcaRouter R10 trace attempt must not be counted as a clean no-RM run. The trace wrapper launched, but its traced child did not receive a usable command environment and the managed service helper failed before it could restart the runtime.

## Preconditions that were valid

Before the trace attempt:

- repository branch was current at `e3f47ebdd3e536f553880f846044c8c115300400`;
- immutable current release was `ff67bab3c94d6992f61b9535836df97f03b9c022`;
- update, runtime, and profile-switch transition states were all idle;
- the managed service was active and healthy;
- the temporary 16 GiB service-level KV override was absent;
- the repository-managed OrcaRouter 16 GiB default remained active.

## Failure before runtime restart

The traced child emitted:

```text
/home/inlc/.local/share/qwen38-spark/current/scripts/manage-service.sh: line 5: dirname: command not found
ERROR: systemctl is required
```

The service helper therefore failed before the normal managed restart path could execute.

The original R10 wrapper incorrectly treated `trace-cmd` exit status as sufficient evidence of child success. `trace-cmd` returned zero even though the managed command had already failed. This produced a misleading summary containing `trace_rc=0`.

## Trace evidence proves no useful allocator run occurred

Every recorded CPU data section was reported as zero bytes. No model loading, RM allocation episode, or replacement-runtime startup was traced.

The generated analysis line:

```text
RM_SYS_ANALYSIS=NO_RM_OOM_IN_CAPTURE_WINDOW
```

is therefore **not** a host-stability result. It only reflects that the invalid trace window contained no RM OOM after the child failed immediately.

## Existing runtime was untouched

The final managed state remained:

- service active/running;
- Docker `OOMKilled=false`;
- API health ready;
- expected OrcaRouter model still served.

The final container ID was:

```text
4157f17f765b8f82e6a2f0af2903cc1e8fef2669a679e61574e54bee2c992817
```

and its `StartedAt` remained:

```text
2026-10-03T06:17:56.999616386Z
```

That was the already-running runtime from before the R10 attempt, confirming that no replacement container was started by this trace run.

## Runner correction

The corrected follow-up is R10b. Its runner changes the experiment contract in two important ways:

1. the traced managed child is launched under an explicit clean environment with a fixed system PATH, HOME, USER, LOGNAME, and SUDO_USER;
2. the managed child writes its own exit status independently of `trace-cmd`, and experiment validity additionally requires an observed container replacement.

The invalid R10 output directory should be retained as failed-run evidence. R10b uses a separate output directory and must be the run used for allocator/root-cause comparison against R9.
