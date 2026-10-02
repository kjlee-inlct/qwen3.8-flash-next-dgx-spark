# mazinb KV-cache A/B mitigation evidence — 2026-10-02

## Purpose

This experiment isolates mazinb KV-cache size after the managed 24 GiB activation failed with `FUNCTIONAL FAIL / HOST-STABILITY FAIL` due to an RM `NV_ERR_NO_MEMORY` event followed by a safety-monitor protected stop.

The controlled matrix is:

- A: 24 GiB KV, current mazinb default/control;
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

## Memory-monitor behavior

The monitor remained in protect mode for the entire startup and soak window.
No `PROTECT stopping` marker occurred.

The most important late-startup/ready-window samples were:

- 20:55:46: non-CMA available 34,539 MiB; non-CMA free 829 MiB;
- 20:56:47: non-CMA available 32,656 MiB; non-CMA free 2,196 MiB;
- 20:57:47: non-CMA available 14,833 MiB; non-CMA free 1,000 MiB;
- 20:58:48: non-CMA available 14,790 MiB; non-CMA free 948 MiB;
- 20:59:49: non-CMA available 14,776 MiB; non-CMA free 928 MiB.

Low free memory alone did not trigger protection because the configured protection gate also requires non-CMA available memory below 10 GiB. During the 16 GiB case, late-window non-CMA available memory remained about 14.8 GiB, leaving several GiB of margin above that gate.

This contrasts with the failed managed 24 GiB activation, where the decisive sequence reached non-CMA available 8,562 MiB with non-CMA free 1,053 MiB and accumulated five consecutive protection samples.

## Interpretation

Case B establishes that reducing mazinb KV cache from 24 GiB to 16 GiB is a viable mitigation candidate on this exact host under the current strict gate.

It does **not** yet prove that 24 GiB KV is the sole cause of the managed failure. The next required discriminator is case A using the same temporary helper and the same lifecycle conditions. This removes managed-vs-temporary runtime differences from the comparison.

Interpretation after A:

- if A reproduces `NV_ERR_NO_MEMORY` and/or a protected stop while B remains clean, the KV-size contrast becomes strong causal evidence that 24 GiB materially drives the host-memory failure boundary;
- if A also passes cleanly, the prior managed failure depended on another state variable or allocator condition and KV size alone is not sufficient to explain it;
- if A reaches functional readiness but logs `NV_ERR_NO_MEMORY`, it remains `HOST-STABILITY FAIL` under the current strict policy.

The successful B experiment is mitigation evidence only. It does not retroactively change the failed managed Hybrid -> mazinb activation classification and does not qualify the managed profile-switch leg until the chosen KV value is promoted into the managed profile and the managed transition passes the same strict readiness/soak/host checks.
