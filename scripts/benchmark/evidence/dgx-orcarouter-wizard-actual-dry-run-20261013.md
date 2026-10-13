# Actual DGX OrcaRouter installed-wizard dry-run — 2026-10-13

**Evidence class:** ACTUAL_DGX / operator-provided terminal output, not GitHub CI,
not a model launch, and not a measured llama-benchy report.

## Source and provenance

- Clean detached worktree:
  `/home/inlc/Workspace/llm/qwen38-orca-wizard-a61b4569c5a6865dbeb9aa4ba4b21aeea12424e2`
- Source SHA: `a61b4569c5a6865dbeb9aa4ba4b21aeea12424e2`.
  Source CI [#38354636800](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38354636800)
  completed SUCCESS (936/936 Python tests), separate from this operator's real DGX dry-run.
- Terminal A command: `./install.sh --dry-run`. The owner manually selected
  existing-setup management `1`, model selection `1` for OrcaRouter,
  and final `Continue? [Y/n]: Y` **under the original --dry-run**.
- Operator log:
  `/home/inlc/dgx-orcarouter-wizard-20261013-152129.log`
  (full log is on the physical DGX, not attached or read by GitHub).
- The driver compared the protected old Docker container's
  `Id|State.Status|Image` and the `install.env` file SHA256 before
  and after the wizard. Both comparisons were equal. This is a limited,
  well-defined preservation observation, not a full-machine mutation audit.

## Observed wizard output

```text
[1/1] Installed setup management
Current profile: OrcaRouter Uncensored (orcarouter, stable)
  1) Select / switch model profile
  2) Edit runtime / API / service settings
  3) Refresh current profile defaults
  4) Cancel
Select [1]: 1

[1/1] Model selection
Current profile: OrcaRouter Uncensored (orcarouter, stable)
  1) OrcaRouter Uncensored
     stable / installable / installed / default / active / image present
  2) NVIDIA Official NVFP4
     experimental / installable / not installed / image absent
  3) mazinb NVFP4
     experimental / installable / installed / image present
  4) OrcaRouter Hybrid H6
     experimental / installable / installed / image present
  Not selectable: lychee888 FP8-PLE
Select [1]: 1

Resuming installation from phase: complete
[6/6] Review installation plan

Model
  model       : orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
  profile     : orcarouter
  storage root: /home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models
  directory   : /home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models/qwen3.8-flash-next-orcarouter
  revision    : c1209bda15a6bbc4c68b585e93d40c0d85f50306
  image       : vllm-skinny-tp1:v1

Runtime
  config      : /home/inlc/.local/state/qwen38-spark/config.vllm.json
  PLE swap    : /swap-ple.img (128 GiB; existing swap preserved)
  protection  : enabled
  monitor     : enabled (available=6 GiB warn, free=2/10 GiB gate, swapfree=8 GiB, 5 samples, heartbeat=60s)

Access / service
  API access  : Docker apps: 8000; LAN: 10.221.50.65:8000 -> 127.0.0.1:8888
  service     : systemd boot service via immutable current release

Continue? [Y/n]: Y

DRY-RUN complete: no download, swap, release, API access, service, Docker, or manifest changes were made.
WIZARD_DRY_RUN_RC=0
OLD_DOCKER_UNCHANGED=YES
INSTALL_MANIFEST_UNCHANGED=YES
WIZARD_LOG=/home/inlc/dgx-orcarouter-wizard-20261013-152129.log
```

## Strict interpretation / safety boundary

The installed wizard resume reads the manifest's `vllm-skinny-tp1:v1`,
**NOT** `vllm-orcarouter-v029:v1` (the different experimental image
checked in the prior independent [M1 preflight](dgx-orcarouter-m1-isolated-preflight-20261013.md)).
The reported `active` label refers to the recorded profile, not to
a running container or healthy API. The menu said installed OrcaRouter,
mazinb and H6 checkpoints; it did not validate model load or inference.

The actual installed immutable release remains
`ff67bab3c94d6992f61b9535836df97f03b9c022`; exact
historical stopped Docker predecessor:
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`.
At source review, the service runner calls runtime-transition `commit`,
which removes the prior rollback container; some rollback/recovery
paths can start a deliberately stopped predecessor. Thus a
normal live `./install.sh` resume / `systemctl restart` is
**NOT an identity-preserving OrcaRouter test** solely by virtue
of this successful dry-run. The managed monitor's enabled
configuration is not evidence of actual host/RM stability.

**Next gate:** wizard-contained, opt-in, isolated OrcaRouter trial
workflow which explicitly protects the exact old Docker object, requires
dedicated monitor state, and includes a verified stop/abort plan.
This feature needs source implementation + synthetic tests and
explicit operator approval before any live attempt; it is **NOT
IMPLEMENTED OR LIVE-QUALIFIED** by this evidence.
Do not start with raw experimental Docker scripts as a substitute for
the owner-required wizard. Terminal B benchmark remains idle.

Owner's current retention instruction: do NOT delete OrcaRouter
**during this test only**, not forever. Future selective removal
may be considered after benchmark/raw JSON+Markdown+SHA256, verified
independent backup, dependency/recovery review and separate approval.
No model/Docker cleanup is authorized now. All five report templates
remain NOT_MEASURED. PR #259 remains Draft/Open/Unmerged.
