# R32 attempt02 exact-image source checker result — 2026-10-06

Status: **SETUP INVALID / STATIC CHECKER INVALID / NO SOURCE-CLOSURE CLAIM**

## Preserved outcome

Corrected-scope R32 was run against exact diagnostic image `vllm-orcarouter-v029-r28-unquant-linear-marker:v1` (`sha256:54c1ae1ba05fc34ec10881db4e5a333895eebf5472a5d282fefa354fe39a762f`).

The checker stopped before emitting the normal contract block:

```text
expected one self.gate=*GateLinear in target function, found 0
R32_CORRECTED_RC=1
R32_CORRECTED_SOURCE_CONTRACT=FAIL
```

Managed runtime was explicitly checked after the failure and remained unchanged:
- container id before/after: `4ebf6df5860aef7b6e0681792f8b8a58b165dee454a98cc6f4bbb0926d94f321`
- StartedAt before/after: `2026-10-05T12:32:36.149058234Z`
- service remained active.

## Checker defect

Attempt01's whole-file ordering bug was fixed, but attempt02 still over-constrained the exact RHS class of `self.gate` to `GateLinear`. The R32 contract only needs the ordering of the actual `self.gate` assignment, `self.shared_expert_gate` assignment, and `self.experts = FusedMoEFactory(...)` inside `Qwen3NextSparseMoeBlock.__init__`; it must not assume the exact-image gate implementation class name.

Therefore this is a checker/setup failure, not evidence that the source-order contract is false. No R32 allocator/backing-growth closure may be claimed from attempt02.

## Required correction

Use AST scoped to `Qwen3NextSparseMoeBlock.__init__`, locate the actual call assigned to `self.gate` and `self.shared_expert_gate` without hard-coding their class names, report those call names, and continue to require `self.experts = FusedMoEFactory(...)` plus the intended ordering.
