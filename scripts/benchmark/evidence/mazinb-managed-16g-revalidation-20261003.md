# mazinb managed 16 GiB re-validation — 2026-10-03

## Status

**FUNCTIONAL PASS / HOST-STABILITY FAIL (strict policy)**

This is the managed Hybrid -> mazinb re-validation after promoting the mazinb default KV cache from 24 GiB to 16 GiB. The prior managed 24 GiB attempt remains `FUNCTIONAL FAIL / HOST-STABILITY FAIL` and is not overwritten by this result.

The 16 GiB promotion successfully removed the previous protected-stop outcome, but it did **not** eliminate the NVIDIA RM memory-failure signature: one `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)` event was captured during startup. Under the project's current strict policy, any such RM event makes the host-stability result FAIL even when the runtime subsequently recovers and remains usable.

## Managed lifecycle result

The installation completed with the managed manifest at `~/.local/state/qwen38-spark/install.env` and runtime root at `~/.local/share/qwen38-spark/current`.

The collected post-switch state showed all lifecycle transitions idle:

- update transition: idle;
- runtime transition: idle;
- profile-switch transition: idle.

The systemd service reported `Result=success`, `ExecMainStatus=0`, `ActiveState=active`, and `SubState=running`.

For the promoted mazinb candidate started at 04:56:51 KST:

- memory protection remained enabled;
- profile: mazinb;
- executor: mp;
- PLE: mmap;
- MTP k=2;
- exact QSA enabled;
- max model length 262144;
- GPU utilization 0.80.

The runtime reached health-ready and model-list validation at 05:08:52 KST, committed the runtime transition and wrote the runtime attestation at 05:08:53 KST, then returned HTTP 200 from both `/health` and `/v1/models` again at 05:11:53 KST. This provides the required 180-second post-ready soak.

The served-model identity was `mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4`.

## 16 GiB KV confirmation

vLLM explicitly reported:

- manual KV reservation: 16.0 GiB;
- KV capacity: 579,086 tokens;
- maximum concurrency at 262,144 tokens/request: 2.21x.

The canonical container remained running after the soak and Docker reported `OOMKilled=false`.

## Kernel and protection result

The sudo-enabled re-collection covered the candidate window from 04:56:51 KST through 09:23:20 KST.

Kernel evidence contained exactly one matching RM/OOM signal:

- 05:07:46 KST: `NVRM: nvCheckOkFailedNoLog: Check failed: Out of memory [NV_ERR_NO_MEMORY] (0x00000051) returned from _memdescAllocInternal(pMemDesc) @ mem_desc.c:1359`.

No kernel OOM-killer event was captured, Docker reported `OOMKilled=false`, and no `PROTECT stopping` marker appeared in the collected evidence.

The RM event occurred about 66 seconds before health readiness. The runtime nevertheless continued through initialization, reached READY, committed and attested, passed the 180-second post-ready soak, and remained active through the 09:23:20 KST evidence collection. From candidate start to that collection, the managed runtime had remained alive for about 4 hours 26 minutes.

## Memory-protection observation

The managed monitor remained in protect mode. Around the RM event and final startup phase:

- 05:06:57: non-CMA available 34,327 MiB; non-CMA free 991 MiB;
- 05:07:58: non-CMA available 33,805 MiB; non-CMA free 3,080 MiB;
- 05:08:58: non-CMA available 15,670 MiB; non-CMA free 1,155 MiB;
- 05:09:59: non-CMA available 15,685 MiB; non-CMA free 1,142 MiB;
- 05:11:00: non-CMA available 15,685 MiB; non-CMA free 1,136 MiB.

Low non-CMA free memory alone did not trigger protection because non-CMA available memory remained above the configured 10 GiB gate. The runtime therefore survived the RM allocation failure instead of entering the five-sample protected-stop sequence seen with 24 GiB.

## Interpretation

The managed result narrows the 16 GiB mitigation claim.

The controlled temporary B=16 GiB case had no RM/OOM signal and passed strict host-stability acceptance. The real managed 16 GiB run, however, encountered one top-level RM `NV_ERR_NO_MEMORY` event and recovered. Therefore the evidence does **not** support the stronger claim that 16 GiB eliminates the RM sysmem allocation failure across allocator states.

What the combined evidence does support is operationally narrower:

- 24 GiB repeatedly crossed the host-protection boundary and failed readiness;
- 16 GiB materially improved memory margin, avoided the protected-stop sequence, reached committed readiness, and sustained the managed runtime for hours;
- allocator/runtime state still matters enough that a recoverable RM memory failure can occur at 16 GiB.

No R9 allocation trace was captured for this managed run, so the exact R9 order-4 rollback/order-0 retry mechanism is not claimed to have been re-proven here. Only the same top-level RM failure signature is established.

## Acceptance consequence

Under the project's current strict host-stability policy, the managed Hybrid -> mazinb 16 GiB leg is:

**FUNCTIONAL PASS / HOST-STABILITY FAIL**

The optional documented `HOST-STABILITY WARN / RECOVERABLE_RM_SYSMEM_FALLBACK` exception is not adopted implicitly. This managed run is a strong candidate for that class because the RM event was recoverable, no protection stop occurred, the API reached READY, the required soak passed, Docker was not OOM-killed, and the runtime remained active for more than four hours. That observation does not change the strict classification unless policy is explicitly changed.
