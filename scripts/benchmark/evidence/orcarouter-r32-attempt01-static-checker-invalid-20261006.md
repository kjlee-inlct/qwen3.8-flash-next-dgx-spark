# R32 attempt 01 — static checker invalid

Status: **SETUP INVALID / NO SOURCE-CLOSURE CLAIM**

The first exact-image static source-contract run used repository head
`f3b187b8710952e9baacf7181a7fa6bc36f62a37` and R28 image
`sha256:54c1ae1ba05fc34ec10881db4e5a333895eebf5472a5d282fefa354fe39a762f`.

Observed output:

- `qwen4_decoder_attention_before_mlp=PASS`
- `qwen4_decoder_hyperconnection_after_mlp=PASS`
- `sparse_moe_gate_before_factory=FAIL`
- `routed_experts_order_contract=PASS`
- `factory_pre_routed_direct_tensor_alloc_count=0`
- `routed_pre_create_direct_tensor_alloc_count=0`
- `direct_precreate_tensor_alloc_syntax=ABSENT`
- `r32_discriminator=R32_PRECREATE_SOURCE_CONTRACT_NOT_CLOSED`
- command RC `1`

This attempt makes **no negative or positive closure claim** for R32.

Root cause is a checker-scoping bug, not a measured runtime failure. The original
`sparse_moe_gate_before_factory` check used whole-file `str.find()` positions for
`self.gate`, `self.shared_expert_gate`, and `self.experts` in `qwen3_next.py`.
That is not a valid test of `Qwen3NextSparseMoeBlock.__init__` ordering because
other classes/functions in the same module can contain the same spellings.

Correction:

- scope the sparse-MoE ordering check to the AST node for
  `Qwen3NextSparseMoeBlock.__init__`;
- locate exact `self.<attr> = <call>` assignments there;
- add a regression test containing an intentionally misleading earlier class so
  whole-file first-occurrence logic cannot regress.

The PASS observations from attempt 01 are preserved as diagnostic output only;
they are not promoted to an overall R32 closure until the corrected checker
passes on the exact R28 image.

No model restart, candidate launch, GPU access, network access, kprobe change,
or evidence mutation was requested by the R32 procedure.
