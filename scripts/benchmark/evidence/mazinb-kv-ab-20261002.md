# mazinb KV-cache A/B mitigation evidence — 2026-10-02

## Purpose

This experiment isolates mazinb KV-cache size after the managed 24 GiB activation failed with `FUNCTIONAL FAIL / HOST-STABILITY FAIL` due to an RM `NV_ERR_NO_MEMORY` event followed by a safety-monitor protected stop.

The controlled matrix is:

- A: 24 GiB KV, original mazinb default/control;
- B: 16 GiB KV, reduced-KV mitigation candidate.

All other runtime controls remain aligned with the failed managed mazinb attempt, including the v0.29 runtime image, mmap PLE path, MTP k=2, exact-QSA fallback, max model length 262144, max sequences 3, GPU utilization 0.80, and memory protection thresholds.

The temporary A/B runtime is isolated from managed installation state. The managed service and canonical container remain stopped during each case.

## Case B — 16 GiB

**Result: FUNCTIONAL PASS / HOST-STABILITY PASS**

Observed window:

- started: 2026-10-02 20:45:40 KST;
- API became ready at approximately 20:57:42 KST;
- `/health` returned HTTP 200;
- `/v1/models` returned the expected mazinb served-model identity;
- post-ready soak completed for 180 seconds;
- experimental runtime was then stopped intentionally;
- final container exit code: 0;
- Docker `OOMKilled=false`;
- runtime-stop marker: absent;
- kernel RM/OOM section for the exact case window contained no signal.

vLLM explicitly reserved 16.0 GiB for KV cache. The resulting KV capacity was 579,086 tokens, reported as 2.21x maximum concurrency for one 262,144-token request.

### B memory-monitor behavior

The monitor remained in protect mode for the entire startup and soak window.
No `PROTECT stopping` marker occurred.

The most important late-startup/ready-window samples were:

- 20:55:46: non-CMA available 34,539 MiB; non-CMA free 829 MiB;
- 20:56:47: non-CMA available 32,656 MiB; non-CMA free 2,196 MiB;
- 20:57:47: non-CMA available 14,833 MiB; non-CMA free 1,000 MiB;
- 20:58:48: non-CMA available 14,790 MiB; non-CMA free 948 MiB;
- 20:59:49: non-CMA available 14,776 MiB; non-CMA free 928 MiB.

Low free memory alone did not trigger protection because the configured protection gate also requires non-CMA available memory below 10 GiB. During the 16 GiB case, late-window non-CMA available memory remained about 14.8 GiB, leaving several GiB of margin above that gate.

## Case A — 24 GiB

**Result: FUNCTIONAL FAIL / HOST-STABILITY FAIL**

Observed window:

- started: 2026-10-02 21:15:53 KST;
- candidate did not reach API readiness;
- final container state: exited, exit code 1;
- Docker `OOMKilled=false`;
- runtime-stop marker recorded `STOP_REASON=memory-protection` for the exact A container;
- kernel logged `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)` twice, at 21:25:21 and 21:27:03 KST;
- the monitor accumulated five consecutive protection samples from 21:27:15 through 21:27:23;
- the monitor then executed `PROTECT stopping qwen38-mazinb-kv-a gracefully to preserve host stability`.

The decisive monitor sequence was:

- 21:27:15: `protect=1/5`, non-CMA available 9,416 MiB, non-CMA free 1,689 MiB;
- 21:27:17: `protect=2/5`, non-CMA available 9,178 MiB, non-CMA free 1,433 MiB;
- 21:27:19: `protect=3/5`, non-CMA available 8,808 MiB, non-CMA free 1,078 MiB;
- 21:27:21: `protect=4/5`, non-CMA available 8,734 MiB, non-CMA free 985 MiB;
- 21:27:23: `protect=5/5`, non-CMA available 9,008 MiB, non-CMA free 1,080 MiB;
- 21:27:23: protected stop.

Swap was not exhausted. Swap-free remained roughly 143 GiB throughout the decisive sequence.

The API-side traceback captured after the protected stop ends in an intentional termination path (`KeyboardInterrupt: terminated`) while the server was still inside processor/warmup initialization. It must not be classified as an independent application crash; the matching runtime-stop marker and monitor log establish the host-protection stop as the controlling termination event.

## Controlled contrast

The temporary A/B comparison now removes the managed-vs-temporary lifecycle difference that remained after the first failed managed activation:

- B, 16 GiB: strict PASS, API ready, served-model validated, 180-second soak complete, no protected stop, no RM/OOM signal, clean exit 0;
- A, 24 GiB: readiness never reached, two RM `NV_ERR_NO_MEMORY` events, five-sample low-memory protection sequence, protected stop, exit 1, `OOMKilled=false`.

Within the tested controls, this is strong causal evidence that the 24 GiB KV reservation materially pushes the GB10 unified-memory host across the RM/host-protection failure boundary, while 16 GiB leaves enough non-CMA available-memory margin to complete startup and soak.

This does **not** establish that KV size is the sole possible contributor under every allocator state, driver version, or workload. It establishes the narrower and operationally relevant result: on this host, with the same checkpoint, image, PLE mode, speculation, QSA mode, max length, max sequences, GPU utilization, and protection policy, changing the controlled KV reservation from 16 GiB to 24 GiB changed the outcome from strict PASS to repeated RM/protected-stop failure.

## Promotion decision

The selected mitigation is therefore:

- promote mazinb managed default KV from 24 GiB to 16 GiB;
- keep every other managed mazinb runtime control unchanged for the next validation;
- retain memory protection unchanged;
- rerun the real managed Hybrid -> mazinb transition;
- require managed readiness, correct served-model identity, post-ready soak, no protected stop, no Docker OOM kill, and no kernel `NV_ERR_NO_MEMORY` in the validation window before changing the managed matrix result.

The completed A/B experiment does not retroactively change the earlier failed managed Hybrid -> mazinb activation. Until the promoted 16 GiB default passes the real managed transition, that existing matrix entry remains `FUNCTIONAL FAIL / HOST-STABILITY FAIL`.
