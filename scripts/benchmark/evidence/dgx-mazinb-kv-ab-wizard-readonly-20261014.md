# Physical DGX mazinb KV A/B — Wizard read-only evidence review

**Evidence captured:** 2026-10-14 KST from Wizard `b4c58750e12a962aba2c1f4ae77784f6eb9c0ed2`, top-level **5 -> 5 -> 3**.
**Actual experiments were on 2026-10-02 KST.** This review did not start, stop, modify, or delete any Docker containers.
**Source provenance:** user-provided 417-line Wizard terminal transcript (not independently captured by CI), SHA-256 of that pasted transcript:
`7f8bcd198a1904e7baa1b016f796d455a38b3e32b19a6b16860f9cd686264162`.
Only the summary, not the full raw log, is committed here. Retain the original log and source Docker/monitor evidence; this fingerprint is **not** a verified off-host backup.

## Identity and historical configuration

| Field | Case A | Case B |
| --- | --- | --- |
| Docker name | `qwen38-mazinb-kv-a` | `qwen38-mazinb-kv-b` |
| Historical KV pool | 25,769,803,776 bytes (24 GiB) | 17,179,869,184 bytes (16 GiB) |
| Docker image label | `vllm-orcarouter-v029:v1` | `vllm-orcarouter-v029:v1` |
| Started (KST) | 2026-10-02 21:15:53 | 2026-10-02 20:45:40 |
| Finished (KST) | 2026-10-02 21:27:31 | 2026-10-02 21:00:45 |
| Status / exit | exited / **1** | exited / **0** |
| Docker OOMKilled | false | false |
| Historical runtime-stop marker | **memory-protection** | absent |

The currently installed *managed predecessor* is a separate stopped OrcaRouter instance: manifest image `vllm-skinny-tp1:v1` (legacy). Neither old KV case is the current managed service. This review does not modify that predecessor, manifest or immutable release.

The A runtime-stop marker names Docker ID `e9107e3cbebecea9affe7e92dfaf13f711ebf84f8ed8e6e06b1ba16985c9e647` and UTC stop timestamp `2026-10-02T12:27:23Z`.
The pasted evidence does not expose a full immutable B Docker ID, nor Docker immutable image digests. Re-inspect them before any future identity-bound operation.

## Case A — 24 GiB: protection intervention, not a proved kernel OOM

- `21:15:54` monitor armed in **protect** mode, with 6 GiB available-memory, 2/10 GiB non-CMA free and 8 GiB swap-free policy.
- `21:27:15` through `21:27:23` five consecutive `WARNING memory margin low protect=1/5` to `5/5` samples.
- Available memory during that sequence: approximately **9.48 to 8.80 GiB**, then **9.08 GiB** (MiB values 9484, 9245, 8876, 8802, 9075).
- At `21:27:23` the monitor emitted `PROTECT stopping qwen38-mazinb-kv-a gracefully to preserve host stability`; the persisted `runtime-stop.env` states `STOP_REASON=memory-protection` and the exact A Docker ID.
- The final Docker status is `exited`, exit **1**, `OOMKilled=false`. The `KeyboardInterrupt: terminated` traceback shown at `12:27:23Z` occurred **after** the protection stop signal; it is consistent with interrupted shutdown, and is not independent proof of a root model exception.
- The read-only evidence output's *filtered* kernel RM/OOM section is empty. This **does not establish** that the entire kernel log was free of unrelated errors.

**Historical classification:** `A_PROTECTED_STOP_CONFIRMED`; full readiness **not established by the displayed excerpt**; the 24 GiB setting did not complete the guarded stability trial. Do **not** relabel this a Docker OOM or a confirmed `NV_ERR_NO_MEMORY`.

## Case B — 16 GiB: API ready and observation window evidenced

- The memory monitor started `20:45:40` in **protect** mode. Periodic `HEARTBEAT healthy` entries continue through `20:59:49`, with no shown `WARNING memory margin low` or `PROTECT stopping`.
- The vLLM engine initialization and CUDA graph warmup completed; logs state `Initial free memory 114.91 GiB, reserved 16.0 GiB memory for KV Cache` and `GPU KV cache size: 579,086 tokens`.
- `21:57:29` would be the wrong date/time alignment; the **actual** API `Application startup complete` was **20:57:33 KST** (`11:57:33Z`).
- At **20:57:42 KST** (`11:57:42Z`) the API logged successful GET requests for **`/health` HTTP 200** and **`/v1/models` HTTP 200**.
- At **21:00:42 KST** (`12:00:42Z`), exactly about **180 seconds** later, vLLM's orderly shutdown began; Docker exited **0** around `21:00:45 KST`.
- The displayed `runtime-stop` marker is absent and the filtered RM/OOM section contains no matching events.
- The historical runner's source `historical mazinb KV A/B runner (mazinb-kv-ab.sh)` checks `/health`, verifies that `/v1/models` contains the expected sole model ID, and waits a configured 180-second soak before voluntarily stopping a healthy candidate. **However, the pasted transcript is evidence-only output; it does not contain the runner's final `RESULT case=B functional=... host=...` line or the exact model JSON body.** We can therefore corroborate that the API and observation sequence occurred, but should not fabricate an unprinted signed-off `FUNCTIONAL_PASS` or `HOST-STABILITY PASS`.

**Historical classification:** `B_READINESS_HTTP_OBSERVED`, `B_180S_OBSERVATION_CONSISTENT`, `NO_REPORTED_PROTECT_STOP`. Model-ID response body and exact runner RESULT line remain uncaptured in this review.

## Decision and unresolved gates

1. Prefer the **16 GiB KV** starting point for a future independently named mazinb candidate; this is a **historical safety baseline**, not a new host approval.
2. Preserve both old A/B Docker objects, their `experiment.env`, monitor logs, kernel evidence and runtime-stop marker. **Do not clean up historical case B** merely to reuse its fixed container name.
3. The Wizard must create a **new, uniquely named** supervised M1 candidate, not re-run `mazinb-kv-ab.sh run B` against an occupied name. Its exact-Docker-ID watchdog must be armed *before start*, durable across SSH disconnects, hold lifecycle lock ownership through observation/benchmark, and never touch the canonical predecessor.
4. The remaining live gates are **M1 implementation + isolated exact-DGX preflight**, fresh API `/health` and *exact* served-name JSON verification, supervised memory/RM stability, real request smoke, and **llama-benchy raw JSON/Markdown/SHA256** with verified off-host backup.
5. **Measured tokens/sec, TTFT, TTFR, PP/TG and concurrency are all `NOT_MEASURED`.** The successful historical health checks are not a performance report or permission to delete models/images.

**Evidence class:** `ACTUAL_DGX_READ_ONLY_REVIEW_OF_HISTORICAL_RUN`.
**New runtime launched for this review:** `NO`.
**Physical host mutation or artifact deletion for this review:** `NO`.
