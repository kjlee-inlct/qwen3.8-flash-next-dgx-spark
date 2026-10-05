# Managed mazinb -> OrcaRouter live-switch evidence — 2026-10-03

## Result

**FUNCTIONAL PASS / HOST-STABILITY PASS**

This records the managed live-switch from the committed mazinb runtime to OrcaRouter under the current strict host-stability policy.

## Source state

The source runtime was the committed managed mazinb profile. The switch began from immutable release `a8aeca47433dc4033b3f1f995eb59023467222ce` with the profile-switch transaction idle before the operation.

The target plan selected:

- model: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`;
- pinned revision: `c1209bda15a6bbc4c68b585e93d40c0d85f50306`;
- image: `vllm-skinny-tp1:v1`;
- max model length: 262144;
- managed memory monitoring and protection enabled;
- PLE CPU offload;
- MTP k=2.

The checkpoint was already present and verified, so no model transfer was required.

## Managed transition

The replacement OrcaRouter container started at 10:12:20 KST.

The managed service then reported:

- health-ready at 10:26:25 KST (`elapsed=845s`);
- model-list validation at 10:26:26 KST;
- runtime transition committed at 10:26:26 KST;
- runtime attestation written at 10:26:26 KST;
- `/health` and `/v1/models` returned HTTP 200 at 10:26:27 KST;
- both endpoints again returned HTTP 200 at 10:29:28 KST, providing more than the required 180-second post-ready soak.

The served-model identity was `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` with `max_model_len=262144`.

At evidence collection time (11:09:58 KST), all lifecycle transitions were idle and the systemd service remained active/running.

## Host-stability evidence

The canonical OrcaRouter container was still running after approximately 57 minutes. Docker reported:

- state: running;
- exit code: 0;
- `OOMKilled=false`;
- no container error.

The memory monitor remained in protect mode. During startup, non-CMA free memory fell below 1 GiB at several samples, but non-CMA available memory stayed above the 10 GiB protection gate; no protected-stop sequence occurred.

The sudo-enabled kernel RM/OOM section for the exact validation window was empty. The collected evidence contains no `NV_ERR_NO_MEMORY`, no NVIDIA RM OOM event, no kernel OOM-killer event, and no `PROTECT stopping` marker.

Under the current strict policy this satisfies `HOST-STABILITY PASS`.

## Matrix consequence

The managed matrix now records:

- Hybrid -> mazinb (16 GiB): `FUNCTIONAL PASS / HOST-STABILITY FAIL` because one recoverable RM `NV_ERR_NO_MEMORY` occurred before readiness;
- mazinb -> OrcaRouter: `FUNCTIONAL PASS / HOST-STABILITY PASS`.

The remaining live-switch leg is OrcaRouter -> Hybrid final return. The PR remains open until that leg is recorded and the overall acceptance scope is reviewed.
