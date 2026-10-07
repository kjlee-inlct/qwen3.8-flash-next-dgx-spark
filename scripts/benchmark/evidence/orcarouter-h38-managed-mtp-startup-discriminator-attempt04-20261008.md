# H38 MTP startup discriminator attempt 04 — 2026-10-08

Status: VALID PROTECTED_STOP — FUNCTIONAL NOT REACHED / HOST-STABILITY INCONCLUSIVE

## Provenance

- repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- branch: `feat/h38-managed-integration`
- exact checkout / target:
  `af0f098f9e36fe15bd64d7358f9449dcf1730f37`
- current immutable predecessor release:
  `ff67bab3c94d6992f61b9535836df97f03b9c022`
- managed predecessor container:
  `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
- isolated candidate image:
  `vllm-orcarouter-v029-h38-decoder-scope:v1`
- isolated candidate mode: `SPEC=none`
- KV cache: `17179869184` bytes (16 GiB)
- evidence directory:
  `/tmp/orcarouter-h38-mtp-none-attempt04-20261007T232026Z`

## Starting state

The corrected runner proved the required stopped post-protection baseline:

```text
managed service: inactive
qwen38-flash-next: running=false
qwen38-flash-next: OOMKilled=false
UPDATE_STATE=idle
TRANSACTION_STATE=idle
PROFILE_SWITCH_STATE=idle
RELEASE_PROFILE_REFRESH_STATE=idle
stale experiment container: none
```

The managed predecessor remained stopped and unchanged throughout the experiment.

## Exact candidate identity

This is the first MTP startup discriminator attempt with a successful post-start
identity proof.

The runner recorded:

```text
spec=none
candidate_image=vllm-orcarouter-v029-h38-decoder-scope:v1
identity_validated=1
```

The identity validator also required the matched H38 runtime shape:

- OrcaRouter served alias and checkpoint mount;
- PLE mmap;
- exact QSA;
- canonical Marlin order / decoder scope;
- no legacy CPU offload;
- no speculative config;
- 16 GiB KV;
- max model length 262144;
- max sequences 3;
- GPU utilization 0.80;
- max batched tokens 8192;
- prefix cache disabled;
- FlashInfer autotune disabled;
- chunked prefill enabled;
- async scheduling disabled.

Therefore the intended single runtime delta from the managed H38 production target was
the removal of MTP/speculative decoding.

## Observed startup and protection

The candidate started successfully but did not reach API READY:

```text
start_rc=0
wait_ready_rc=1
api_ready=0
oom_killed=false
```

Checkpoint loading was still early when protection intervened. The preserved startup
summary reached `5/18` main-model shards.

The monitor trajectory was:

```text
08:20:27 monitor started
08:21:19 low-free warning, swapgrowth=0 MiB
08:21:23 recovered
08:21:25 low-free warning, swapgrowth=0 MiB
08:21:40 recovered
08:21:52 low-free warning, swapgrowth=0 MiB
08:22:06 recovered
08:22:20 low-free warning, swapgrowth=0 MiB
08:22:24 protect=1/5, noncma_available=40324 MiB,
         noncmafree=1963 MiB, swapgrowth=949 MiB
08:22:26 recovered
08:22:34 protect=1/5, noncma_available=41019 MiB,
         noncmafree=1649 MiB, swapgrowth=3121 MiB
08:22:36 recovered
08:22:50 protect=1/5, noncma_available=43188 MiB,
         noncmafree=1794 MiB, swapgrowth=3151 MiB
08:22:52 protect=2/5, noncma_available=42909 MiB,
         noncmafree=1803 MiB, swapgrowth=3205 MiB
08:22:54 protect=3/5, noncma_available=42669 MiB,
         noncmafree=1706 MiB, swapgrowth=3315 MiB
08:22:56 protect=4/5, noncma_available=42410 MiB,
         noncmafree=1512 MiB, swapgrowth=3375 MiB
08:22:58 protect=5/5, noncma_available=42110 MiB,
         noncmafree=1488 MiB, swapgrowth=3425 MiB
08:22:58 PROTECT stop
```

Important properties:

- non-CMA available remained about 40-45 GiB through the warning/protection sequence;
- the 10 GiB absolute available gate was not approached;
- swap-free remained above 139 GiB;
- protection was armed by low non-CMA free plus the swap-growth arm;
- warning episodes repeatedly recovered before the final five-sample sequence;
- no strict RM no-memory line was present in the measured kernel window.

This is the same signal family as the first atomic managed-H38 protected stop:
high reclaimable available memory, low immediately-free non-CMA memory, and active
swap consumption during cold loading.

## Strict classification

The final runner summary was:

```text
functional=NOT_REACHED
host_stability=INCONCLUSIVE
kernel_window_rc=0
rm_oom_count=0
protected_stop=1
identity_validated=1
result=PROTECTED_STOP
script_rc=1
```

Classification:

- exact isolated H38 SPEC=none identity: PASS;
- API READY: NOT REACHED;
- FUNCTIONAL: NOT REACHED;
- strict RM window: VALID;
- strict NVIDIA RM OOM: NONE OBSERVED;
- memory protection: INTERVENED;
- HOST-STABILITY: INCONCLUSIVE;
- discriminator result: `PROTECTED_STOP`.

A zero RM count after protection is not HOST-STABILITY PASS.

## MTP discriminator conclusion

The intended question was whether removing MTP while holding H38 runtime identity and
host protection fixed would avoid the startup protection boundary.

It did not.

Therefore:

> **MTP materialization is not sufficient to explain the managed-H38 protected-stop
> boundary.**

This valid result does not prove that MTP has zero memory cost or can never amplify a
later pressure event. It does close MTP as the sufficient explanation for the observed
managed-H38 protection stop.

Attempt 03 remains harness-invalid for gate purposes, but its retained diagnostic
sequence is consistent with this direction: a launched `SPEC=none` candidate completed
18/18 main shards and then observed four strict RM OOM events before protection. Because
attempt 03 lacked exact identity attestation, that observation remains supporting
diagnostic context rather than formal MTP-discriminator evidence.

## Next engineering direction

Do not:

- weaken the monitor to force H38 through startup;
- classify this protected stop as host-stability pass;
- re-run the managed migration gate unchanged;
- authorize managed determinism/performance/restart follow-up.

The immediate next step is read-only/offline discrimination between:

1. known high-available / low-free / swap-growth protected-stop windows with no strict
   RM event, including this attempt and atomic H38 attempt 01; and
2. preserved strict-RM-failure trajectories from the R21/R22/RM investigation.

The purpose is to determine whether an additional trajectory/phase signal can
distinguish ordinary cold-load paging from impending RM order-4 failure **without
weakening the current safety policy first**.

The historical R9-R32 allocator closure remains authoritative: the lower-level failure
is a node0 Normal / Unmovable high-order RM allocation mechanism, not total-RAM or
swap exhaustion.
