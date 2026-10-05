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

    def test_sparse_moe_order_is_scoped_and_gate_class_agnostic(self):
        tree = r32.ast.parse(
            """
class Distractor:
    def __init__(self):
        self.experts = FusedMoEFactory()
        self.shared_expert_gate = WhateverSharedGate()
        self.gate = WhateverGate()

class Qwen3NextSparseMoeBlock:
    def __init__(self):
        self.gate = InstalledGateImplementation()
        self.shared_expert_gate: object = InstalledSharedGateImplementation()
        self.experts = FusedMoEFactory()
"""
        )
        cls = r32.find_class(tree, "Qwen3NextSparseMoeBlock")
        func = r32.find_func(cls.body, "__init__")
        gate_line, gate_call = r32.find_self_assignment_call(func, "gate")
        shared_line, shared_call = r32.find_self_assignment_call(
            func, "shared_expert_gate"
        )
        experts_line, experts_call = r32.find_self_assignment_call(func, "experts")
        self.assertLess(gate_line, shared_line)
        self.assertLess(shared_line, experts_line)
        self.assertEqual(gate_call, "InstalledGateImplementation")
        self.assertEqual(shared_call, "InstalledSharedGateImplementation")
        self.assertEqual(experts_call, "FusedMoEFactory")

    def test_self_assignment_locator_requires_unique_assignment(self):
        tree = r32.ast.parse(
            """
def f():
    self.gate = FirstGate()
    self.gate = SecondGate()
"""
        )
        func = r32.find_func(tree.body, "f")
        with self.assertRaises(SystemExit):
            r32.find_self_assignment_call(func, "gate")


if __name__ == "__main__":
    unittest.main()
