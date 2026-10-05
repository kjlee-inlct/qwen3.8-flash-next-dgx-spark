import importlib.util
import pathlib
import tempfile
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


if __name__ == "__main__":
    unittest.main()
