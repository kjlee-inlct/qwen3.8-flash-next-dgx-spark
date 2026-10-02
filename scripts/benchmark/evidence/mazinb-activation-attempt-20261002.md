# Managed Hybrid -> mazinb activation attempt — 2026-10-02

## Classification

**FUNCTIONAL FAIL / HOST NOT CLASSIFIED**

This was a real managed profile activation attempt, not a dry-run and not an
instrumentation/tooling `NO TEST`.

The mazinb candidate did not reach the managed readiness boundary:

- `/health` never became ready in the captured installer output;
- runtime-commit attestation remained missing;
- the systemd service became `inactive` before readiness; and
- the installer rolled the profile switch back to `orcarouter-hybrid`.

The captured installer output does **not** contain enough retained host evidence
to classify the stop as memory protection, an application/container failure, a
kernel/RM host-stability event, or another lifecycle stop. Do not promote the
result to `HOST-STABILITY FAIL` or `HOST PASS` until the retained journal,
monitor, Docker state, and kernel evidence is inspected.

## Attempt configuration

The activation used the already staged pinned mazinb checkpoint:

- repository: `mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4`;
- revision: `f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f`;
- local size: approximately 173.64 GiB;
- runtime image: `vllm-orcarouter-v029:v1`;
- checkpoint-default config;
- runtime memory monitor enabled;
- low-memory protection enabled;
- managed LAN/API access; and
- managed systemd service enabled.

Before runtime startup, the installer reported:

- all checkpoint files already verified;
- PLE layout detected as BF16/I64;
- MTP tensors detected as BF16;
- release tests PASS (`359 tests`);
- immutable release qualification PASS; and
- candidate profile manifest activation to `mazinb`.

These pre-start results do not imply runtime acceptance.

## Readiness timeline captured by the installer

The same candidate container remained reported as running while the installer
waited for committed readiness.

Observed milestones include:

- 60 s: checkpoint shard loading had started;
- 720 s: readiness still waiting and attestation missing;
- 780 s: the vLLM log reported compile work for range `(1, 8192)`;
- 840 s: the vLLM log reported CUDA graph capture complete, using 0.53 GiB;
- immediately after the 840 s progress report: the managed service was reported
  `inactive`; and
- the profile-switch transaction rolled back to `orcarouter-hybrid`.

The captured output therefore establishes meaningful candidate startup
progress, but not API readiness, served-model validation, runtime commit, or a
host-stability classification.

## What the captured installer output does not establish

No conclusion should be drawn solely from the absence of these strings in the
installer transcript:

- `NV_ERR_NO_MEMORY` / `NVRM`;
- kernel OOM / process OOM;
- Docker `OOMKilled`;
- monitor `PROTECT` output; or
- the service-runner protected-stop message.

The installer version used for this attempt printed only the last service and
container progress lines while waiting. When the unit changed to `inactive`, it
returned the generic readiness error before dumping the complete service
journal, runtime monitor tail, Docker exit metadata, or kernel log.

## Leading lifecycle hypothesis — not yet a conclusion

A low-memory protected stop is a plausible first hypothesis because the managed
service runner intentionally exits successfully after a matching startup
memory-protection stop, while the systemd unit uses `Restart=on-failure`. That
combination can leave the service `inactive` rather than failed/restarting.

This is only a code-path consistency check. The retained monitor/journal
records must show the protected-stop evidence before classifying this attempt as
memory protection.

## Evidence required before another activation

Collect the retained evidence from the existing attempt before rerunning the
model:

1. transition states after rollback;
2. full managed-service journal covering the attempt;
3. runtime memory-monitor tail and warning/protection lines;
4. Docker container state/exit/OOM metadata where still retained; and
5. kernel RM/OOM lines for the same time window.

A read-only runtime helper was added after this attempt to collect these sources
in one command. It does not start or stop the model.

## Acceptance impact

- Hybrid -> mazinb is no longer merely "activation blocked"; an activation was
  attempted and rolled back.
- mazinb -> OrcaRouter remains pending because mazinb never reached committed
  readiness.
- The rollback restored `orcarouter-hybrid`; that rollback itself must not be
  counted as the still-pending final OrcaRouter -> Hybrid matrix leg.
- The existing Hybrid H6 R9 host-stability conclusion remains separate from
  this mazinb startup failure until the retained evidence is classified.
- PR #244 should remain open.

## Observability follow-up

After this attempt, managed readiness failure handling was hardened so an early
service stop or readiness timeout prints:

- systemd state/result/exit status;
- recent service journal;
- recent runtime memory-monitor log;
- Docker exit code and `OOMKilled`; and
- recent timestamped container logs.

Regression coverage and runtime documentation were added with the change.
