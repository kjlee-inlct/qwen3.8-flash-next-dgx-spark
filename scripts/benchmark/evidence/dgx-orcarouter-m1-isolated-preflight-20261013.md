# Actual DGX M1 isolated OrcaRouter v0.29 preflight — 2026-10-13

**Evidence classification: ACTUAL_DGX operator-provided log, read-only.**
The operator used a clean detached source worktree at exact
`5a14d169bbca93604b92e52dc1e548ed75cc5569` (same-SHA
[GitHub CI #38350725606](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38350725606)
SUCCESS). Host-local log path:
`/home/inlc/dgx-m1-experiment-preflight-20261013-143450.log`.

~~~text
PROTECTED_BEFORE=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24|exited|false|sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4
vLLM v0.29 checkpoint preflight (orcarouter)
  model repo      : orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
  model revision  : c1209bda15a6bbc4c68b585e93d40c0d85f50306
  weights         : ready (/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models/qwen3.8-flash-next-orcarouter)
  image           : ready (vllm-orcarouter-v029:v1)
  managed service : inactive
  canonical       : not running
  experiment      : absent
  API port 8888     : free
PROTECTED_AFTER=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24|exited|false|sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4
M1_PREFLIGHT_RC=0
M1_PREFLIGHT_LOG=/home/inlc/dgx-m1-experiment-preflight-20261013-143450.log
MODEL_START=NOT_PERFORMED
~~~

All observed before/after ID, exited state, OOMKilled false, image
identity matched. The v0.29 image and checkpoint source were READY,
managed service inactive, no running canonical container, experiment
absent, port 8888 free, **M1_PREFLIGHT_RC=0**.
This did not start the model, validate API health, or benchmark anything.

**Owner instruction added after this observation:** actual model
**installation, switching and uninstallation must use the interactive
wizard**. Two terminals are reserved for (A) management/storage tasks
and (B) benchmarking; they are not permission for concurrent lifecycle
changes. Thus this direct experimental preflight remains useful
historical READ_ONLY evidence, but **do not use standalone experiment
start as the substitute for wizard managed activation**. The old
Docker object and immutable release remain protected. Managed
service restart / wizard profile change can delete the stopped
predecessor; normal uninstall can remove it. Hold until an explicitly
approved, wizard-mediated safe M1 plan exists. Five report cards
remain NOT_MEASURED and deletion remains BLOCKED.
