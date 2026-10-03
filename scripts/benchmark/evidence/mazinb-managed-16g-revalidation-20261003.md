# mazinb managed 16 GiB re-validation — 2026-10-03

## Status

**FUNCTIONAL PASS / HOST-STABILITY PENDING KERNEL EVIDENCE**

This is the managed Hybrid -> mazinb re-validation after promoting the mazinb default KV cache from 24 GiB to 16 GiB. The prior managed 24 GiB attempt remains `FUNCTIONAL FAIL / HOST-STABILITY FAIL` and is not overwritten by this result.

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

## Memory-protection observation

The managed monitor remained in protect mode. Late-startup/post-ready samples included non-CMA free memory near 1.1 GiB while non-CMA available memory remained about 15.7 GiB, above the 10 GiB protection gate. No protected-stop marker appears in the collected evidence, and the canonical container remained running.

This behavior is consistent with the earlier temporary B=16 GiB strict PASS and contrasts with the 24 GiB failures, where non-CMA available memory crossed below the protection gate and RM `NV_ERR_NO_MEMORY` was observed.

## Remaining host-stability closure item

The evidence collector could not read the kernel journal because the sudo credential was unavailable at collection time. Its kernel section therefore contains no positive or negative RM/OOM evidence.

Under the current strict acceptance policy, absence of a protected stop and `OOMKilled=false` are not sufficient to claim `HOST-STABILITY PASS` if the kernel RM window was not captured. The managed 16 GiB leg remains `HOST-STABILITY PENDING KERNEL EVIDENCE` until the kernel journal is checked for the candidate-start-through-soak window.

No model rerun is required. Re-run the read-only evidence collector with a fresh sudo credential, using the original managed-candidate start as the lower bound:

```bash
sudo -v
bash scripts/runtime/collect-managed-readiness-evidence.sh \
  --since '2026-10-03T04:56:51+09:00' \
  | tee /tmp/mazinb-managed-16g-kernel-20261003.txt
```

Because the runtime remains active, this re-collection also extends the observed stable-runtime window beyond the original 180-second soak.

Final host-stability acceptance requires no new `NV_ERR_NO_MEMORY`, NVIDIA RM OOM, kernel OOM-killer event, or protected stop in the managed candidate window through the re-collection time.
