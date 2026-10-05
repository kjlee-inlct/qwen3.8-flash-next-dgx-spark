import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/benchmark/inspect-orcarouter-r32-precreate-source-contract.py"

spec = importlib.util.spec_from_file_location("r32_source_contract", SCRIPT)
assert spec and spec.loader
r32 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r32)


class R32SourceContractTest(unittest.TestCase):
    def test_call_name_and_direct_alloc_detection(self):
        tree = r32.ast.parse(
            """
def f():
    x = torch.empty((4, 4))
    y = helper()
    self.quant_method.create_weights(layer=self)
"""
        )
        func = r32.find_func(tree.body, "f")
        create_line = r32.find_call_lineno(func, "self.quant_method.create_weights")
        rows = r32.direct_alloc_calls_before(func, create_line)
        self.assertEqual(rows, [(3, "torch.empty")])

    def test_assignment_call_locator(self):
        tree = r32.ast.parse(
            """
def FusedMoEFactory():
    routed_experts = routed_experts_cls(a=1)
    return routed_experts
"""
        )
        func = r32.find_func(tree.body, "FusedMoEFactory")
        self.assertEqual(
            r32.find_assignment_call_lineno(func, "routed_experts", "routed_experts_cls"),
            3,
        )

    def test_sparse_moe_order_is_scoped_to_target_class(self):
        tree = r32.ast.parse(
            """
class Distractor:
    def __init__(self):
        self.experts = FusedMoEFactory()
        self.shared_expert_gate = ReplicatedLinear()
        self.gate = GateLinear()

class Qwen3NextSparseMoeBlock:
    def __init__(self):
        self.gate = GateLinear()
        self.shared_expert_gate = ReplicatedLinear()
        self.experts = FusedMoEFactory()
"""
        )
        cls = r32.find_class(tree, "Qwen3NextSparseMoeBlock")
        func = r32.find_func(cls.body, "__init__")
        gate = r32.find_self_assignment_call_lineno(func, "gate", "GateLinear")
        shared = r32.find_self_assignment_call_lineno(
            func, "shared_expert_gate", "ReplicatedLinear"
        )
        experts = r32.find_self_assignment_call_lineno(
            func, "experts", "FusedMoEFactory"
        )
        self.assertLess(gate, shared)
        self.assertLess(shared, experts)


if __name__ == "__main__":
    unittest.main()
