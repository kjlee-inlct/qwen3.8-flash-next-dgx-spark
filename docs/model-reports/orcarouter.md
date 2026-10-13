# orcarouter — benchmark report

## ACTUAL_DGX OrcaRouter Legacy A isolated Docker START succeeded — NOT READY/NOT QUALIFIED (2026-10-13 17:57 KST)

The operator physically ran `./install.sh` using a clean detached worktree
at **exact source `48c517357cef2182be986c298a86ddfa1f4c74b0`**;
the wizard acquired its lifecycle lock, current installed OrcaRouter
management menu **6** → isolated A/B menu **2** (Legacy A) → entered
original exact old Docker ID → manually answered **Y** to isolated
Docker creation/start. Source CI #38369045129 had already succeeded
(955/955 tests + synthetic operator verification).
Actual DGX output **`AB_TRIAL_STARTED=UNQUALIFIED`**,
`AB_WIZARD_RC=0`, `OLD_DOCKER_UNCHANGED=YES`,
`INSTALL_MANIFEST_UNCHANGED=YES`:

- **New Legacy A experiment container exact ID:**
  `57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56`,
  image `vllm-skinny-tp1:v1` (preflight image ID
  `sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`).
- **Protected original managed Docker exact ID:**
  `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`,
  unchanged according to post-command Docker status/image/OOMKilled comparison.
  Original `install.env` SHA256 unchanged by post-command comparison.
- Trial API `http://127.0.0.1:18888`; isolated monitor log
  `/home/inlc/.local/state/qwen38-spark/ab-trials/legacy-1791881886/monitor.log`.
  Wizard session log
  `/home/inlc/dgx-ab-legacy-start-20261013-175703.log`.
- Physical evidence is the operator-pasted terminal output, not a
  retrieved monitor/API/kernel log. **No `/health`, `/v1/models`,
  watchdog recent heartbeat, long-running NVIDIA RM stability,
  inference or llama-benchy result has been verified**. Even if the
  initial container reported STARTED, it could subsequently exit or
  hit the 3600-second monitored runtime limit. All model benchmark
  results remain **NOT_MEASURED**.

**Immediate priority:** while the trial is present, collect read-only
exact-ID `docker inspect`, watchdog heartbeat/monitor tail,
Docker logs, API `/health` and served `/v1/models`, current
non-CMA memory and `journalctl -k --since '2026-10-13 17:57:00'`
NVRM/Xid/RM error evidence. A stale watchdog or strict RM failure
blocks benchmark; use **wizard management 6 → 4** to stop only the
candidate when necessary, not direct unmanaged `docker stop`.
Do NOT run B or llama-benchy yet, restart the managed service,
delete anything, or merge PR #259. The OrcaRouter no-delete instruction
is limited to this test. Record the **first actual** Legacy A trial as
DOCKER_STARTED_UNQUALIFIED, not model READY/host stable.
[Original operator-supplied physical startup evidence](../scripts/benchmark/evidence/dgx-orcarouter-legacy-a-actual-start-20261013.md).


## Legacy vs v0.29 images — BOTH NOT_MEASURED (2026-10-13)

The owner will compare the same checkpoint under `vllm-skinny-tp1:v1` (legacy CPU-offload) and `vllm-orcarouter-v029:v1` (mmap) **sequentially**, initially with 16 GiB managed KV. No real A/B model startup or `llama-benchy` result has been captured. API health, TTFT, PP/TG, strict host stability and reproducibility are unknown. [Wizard-based A/B protocol](../DGX-ORCAROUTER-AB-BENCHMARK.md). The current source adds a **read-only plan menu only**, not live launch. Do not populate benchmark fields from historical unrelated runs.


**BENCHMARK_STATUS: NOT_MEASURED**

| Field | Status / value |
|---|---|
| Project model profile | `orcarouter` |
| Repository/model provenance | `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` |
| Actual DGX context (2026-10-13) | checkpoint present; stopped legacy vllm-skinny-tp1:v1; M1 NOT_QUALIFIED |
| Tool | llama-benchy (planned, source SHA `e9be344578cec17745066b220798b80a0d2686d3`) |
| Source / runtime / container identity of future measurement | NOT_CAPTURED |
| Prompt processing (PP), tok/s | NOT_MEASURED |
| Generation throughput (TG), tok/s | NOT_MEASURED |
| TTFR and end-to-end TTFT, ms | NOT_MEASURED |
| Concurrency scaling | NOT_MEASURED |
| strict NVIDIA RM and monitor verdict for future run | NOT_MEASURED |

No benchmark has been executed under this new report protocol; these
are **intentional placeholders**, not zero measurements or failed
inference requests. Only populate after real `llama-benchy` JSON,
validated API model identity, pinned source/checkpoint/image, model
readiness and bounded host observation are available.

See [the benchmark protocol](README.md). Historical test results may
be separately linked with their original source/conditions, never
silently copied as current comparable measurements.
