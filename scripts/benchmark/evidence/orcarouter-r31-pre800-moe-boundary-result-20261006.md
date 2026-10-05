# R31 — pre-800 / ModelOpt-MoE boundary result

Status: **COMPLETED — READ-ONLY POST-HOC PASS**

Source evidence: preserved R28 live run only. No model restart, candidate launch, image build, kprobe change, or evidence mutation.

## Result

R31 aligned the 48 exact R30 `800 MiB -> 400 MiB(w13)` pairs against the inherited R26 `ModelOptNvFp4FusedMoE.create_weights()` outer marker.

- selected ModelOpt-MoE intervals: `48`
- selected w13 intervals: `48`
- exact common sequence IDs: `48`
- exact 800/400 pairs: `48`
- 800 before ModelOpt-MoE BEGIN: `48/48`
- 800 inside MoE before w13: `0`
- 800 inside w13: `0`
- 800 -> MoE BEGIN: min `7.809684 ms`, median `8.070243 ms`, max `8.672666 ms`
- MoE BEGIN -> w13 BEGIN: min `0.002861 ms`, median `0.028849 ms`, max `0.078917 ms`
- 800 -> w13 BEGIN: min `7.822797 ms`, median `8.100208 ms`, max `8.730840 ms`

Discriminator:

`R31_PRE800_STRICTLY_BEFORE_MODELOPT_MOE_BEGIN`

## Interpretation

The repeated `800 MiB` RM request is **not** temporally inside `ModelOptNvFp4FusedMoE.create_weights()` and is therefore not the w13/w2 packed-weight allocation body itself. The outer ModelOpt marker is inserted immediately before the first statement of `create_weights()`, so the ~8 ms precursor belongs to an earlier constructor/factory phase.

This remains temporal localization, not causal ownership proof. RM bytes are logical allocation activity volume, not exact resident ownership.

## Next

R32 is source-only/static. Inspect the exact R28 image's installed Qwen4Exp decoder, Qwen3Next Sparse-MoE, FusedMoEFactory, and RoutedExperts constructor order. The purpose is to determine whether any direct model-tensor allocation exists in the pre-`create_weights()` path that can plausibly own the repeated 800 MiB family. If not, shift the investigation from model-prefix ownership to allocator/backing-growth semantics.
