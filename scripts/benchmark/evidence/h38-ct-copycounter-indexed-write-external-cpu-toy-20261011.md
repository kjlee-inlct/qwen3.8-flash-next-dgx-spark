# H38 CT CopyCounter indexed-write question — EXTERNAL CPU-only PyTorch toy (2026-10-11)

## Scope: separate from installed H38 / NOT a DGX runtime test

A small **external assistant analysis environment** was used to execute a CPU-only PyTorch tensor test. The tool reported `torch.__version__ == "2.10.0+cpu"`; device was explicitly CPU and all tensors had at most 6 elements.

**This was NOT executed in the operator's DGX Spark, H38 container, or vLLM v0.29 installed image.** It did not load the H38 checkpoint/model, import vLLM, use a GPU, touch the operator host, or change project/host resources. This external CPU probe has no H38 image ID or installed-H38 PyTorch version attestation. No equivalent TorchDispatchMode event capture has yet been observed in the H38 runtime.

The source contract already established by the earlier actual DGX source-only inspections:
- CT packed/scale source audit `PASS_SOURCE_CONTRACT_ONLY` on exact operator checkout `5fa4265d394255744f8886b857804a28c433cf3f`.
- Input-scale postconstruction attribute audit `PASS_SOURCE_SITES_ONLY` on exact operator checkout `1865521c2ff58add7bddeed6735c76803a3e3637`.
- The pinned vLLM source `CopyCounter` counts `torch.ops.aten.copy_.default` and `get_numel_loaded` caps **per invocation** using `min(numel, param.numel())`; no unique-address tracking was verified.
- RoutedExperts uses direct Tensor subscript assignments for input/global tensor scales and explicit copy_ for packed/group paths. The source alone does NOT certify which dispatcher events those assignments actually produce in H38.

## Executed external environment mini-probe

The following simple `TorchDispatchMode` pattern captures exactly the operator equality used by the pinned source `CopyCounter` concept, without importing vLLM:

```python
import torch
from torch.utils._python_dispatch import TorchDispatchMode

class Trace(TorchDispatchMode):
    def __init__(self):
        super().__init__()
        self.copies = []
        self.ops = []

    def __torch_dispatch__(self, func, types, args=(), kwargs=None):
        self.ops.append(str(func))
        if func is torch.ops.aten.copy_.default:
            self.copies.append(args[0].numel())
        return func(*args, **(kwargs or {}))

dest = torch.zeros((3, 2), device="cpu")
actions = (
    ("nested_scalar", lambda: dest[0].__setitem__(1, torch.tensor(2.0))),
    ("single_value", lambda: dest.__setitem__(1, torch.tensor([4.0, 5.0]))),
    ("row", lambda: dest.__setitem__(2, torch.tensor([6.0, 7.0]))),
    ("repeat_nested_scalar", lambda: dest[0].__setitem__(1, torch.tensor(9.0))),
)
for name, action in actions:
    with Trace() as trace:
        action()
    print(name, trace.ops, "copy_credit", sum(trace.copies))
```

### Observed output summary (external torch 2.10.0+cpu only)

| Operation | Notable dispatch events | Counted aten.copy_ destination numel |
|---|---|---:|
| `dest[0][1] = scalar` | aten.lift_fresh.default, 2 x aten.select.int, **aten.copy_.default** | 1 |
| `dest[1] = row2` | aten.lift_fresh.default, aten.select.int, **aten.copy_.default** | 2 |
| `dest[2] = row2` | aten.lift_fresh.default, aten.select.int, **aten.copy_.default** | 2 |
| `dest[0][1] = new_scalar` (repeat same destination) | aten.lift_fresh.default, 2 x aten.select.int, **aten.copy_.default** | 1 |

Final 3x2 toy tensor: `[[0.0, 9.0], [4.0, 5.0], [6.0, 7.0]]`.

**Synthetic accounting counterexample:** per-invocation copy credits sum to **6** while destination has only **5 unique elements written** (index `[0,0]` untouched). Toy `param.numel()=6`, so summing per-call `min(copy_credit, param.numel())` gives `6 >= 6` despite one never-written element. Rewriting the same location generates another counted copy event. The destination uniqueness claim is determined by the known toy operations, **not by the CopyCounter**, which does not track uniqueness.

A prior separate external test on the same CPU stack also showed that explicit `dest_slice.copy_(scalar)` and `dest[index] = row` emitted `aten.copy_.default`; these external observations establish only an example of PyTorch dispatcher behavior.

## Correct interpretation and next gate

1. **In this exact external CPU PyTorch version and these tiny operations**, indexed Tensor assignment did emit counted `aten.copy_.default` events. The earlier broad claim `"indexed assignments never count"` would therefore be inaccurate. The correct status for pinned **installed H38** is still `ACTUAL_H38_ATEN_COPY_CREDIT=UNVERIFIED` until an appropriately isolated, resource-safe runtime observation or an exhaustive source-supported proof.
2. **Even if H38 indexed assignments also emit copy_ events**, aggregate counted numel can overstate **unique covered destination elements** when repeated writes occur; it can also trigger a threshold before all required weights are loaded. This is a conditional hazard, not evidence that actual H38 repeats any particular destination.
3. The next discriminating question is exact callback counts and coverage per parameter/expert/shard in H38, including local/nonlocal routing, optional global-scale behavior, and shard 8/11 ordering. No real 512-expert load trace, weight completeness, memory bound, or inference safety can be inferred from this toy.
4. Importing torch and running this experiment **inside the DGX H38 image** has not been safety qualified in this work; do not do so automatically. No GPU/model execution, H38 image changes, checkpoint scan, managed-service/host-protection changes or PR Ready/Merge is authorized.

**Status:** EXTERNAL_CPU_TOY_DISPATCH=OBSERVED_TORCH_2_10_0_CPU_ONLY; H38_CT_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; H38_INPUT_SCALE_ATTR_SOURCE=PASS_SOURCE_SITES_ONLY; H38_TORCH_DISPATCH_RUNTIME=UNVERIFIED; H38_WEIGHT_COMPLETENESS=UNVERIFIED; SHARD_8_11_BUFFER_LIFETIME=UNVERIFIED; H38_FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.
