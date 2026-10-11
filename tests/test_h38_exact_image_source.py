"""Static source-contract regressions; never starts Docker/model or imports torch."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/benchmark/inspect-h38-exact-image-source.py"
RUNNER = ROOT / "scripts/benchmark/check-h38-exact-image-source.sh"
spec = importlib.util.spec_from_file_location("h38_exact_source", SOURCE)
assert spec and spec.loader
h38 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h38)

CT = '''\
class CompressedTensorsW4A4Nvfp4MoEMethod:
    def create_weights(self, layer):
        w13_weight = ModelWeightParameter(
            data=torch.empty(4, 5),
            input_dim=1, output_dim=2, weight_loader=loader,
        )
        layer.register_parameter("w13_weight_packed", w13_weight)
        w2_weight = ModelWeightParameter(
            data=torch.empty(5, 4),
            input_dim=1, output_dim=2, weight_loader=loader,
        )
        layer.register_parameter("w2_weight_packed", w2_weight)

    def process_weights_after_loading(self, layer):
        layer.register_parameter("w13_weight", layer.w13_weight_packed)
        delattr(layer, "w13_weight_packed")
        layer.register_parameter("w2_weight", layer.w2_weight_packed)
        delattr(layer, "w2_weight_packed")

    def apply(self, layer):
        layer_idx = 3
        self.moe_kernel.impl.fused_experts._qwen38_marlin_layer_idx = layer_idx
'''
HUMMING = '''\
class HummingFP8ScaledMMLinearKernel:
    def __init__(self):
        _qwen38_h20_compute = {}
        _qwen38_h20_compute["use_batch_invariant"] = True
'''
MARLIN = '''\
def _qwen38_canonicalize_marlin_sorted_tokens(key):
    return torch.argsort(key, stable=True)

class MarlinExperts:
    def apply(self):
        return getattr(self, "_qwen38_marlin_layer_idx", -1)
'''


def install(root: Path) -> None:
    for key, source in (("ct", CT), ("humming", HUMMING), ("marlin", MARLIN)):
        path = root / h38.SOURCE[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


class H38ExactSourceTests(unittest.TestCase):
    def test_h11_h12_retains_torch_empty_and_alias(self) -> None:
        output = h38.inspect_ct(CT)
        self.assertEqual(output["h11_packed_weights"], "PASS")
        self.assertEqual(output["h11_tensor_allocations_retained"], "YES")
        self.assertEqual(output["h12_postload_object_alias"], "PASS")

    def test_h11_missing_packed_tensor_allocation_rejects(self) -> None:
        with self.assertRaisesRegex(ValueError, "torch.empty allocation"):
            h38.inspect_ct(CT.replace("data=torch.empty(4, 5)", "data=helper(4, 5)"))

    def test_h12_rewrapped_parameter_is_not_accepted(self) -> None:
        legacy = CT.replace(
            'layer.register_parameter("w13_weight", layer.w13_weight_packed)',
            'layer.w13_weight = torch.nn.Parameter(layer.w13_weight_packed.data)',
        )
        with self.assertRaisesRegex(ValueError, "post-load alias"):
            h38.inspect_ct(legacy)

    def test_h38_humming_marlin_sources(self) -> None:
        self.assertEqual(h38.inspect_humming(HUMMING)["h38_humming_fp8_control"], "PASS")
        self.assertEqual(h38.inspect_marlin(MARLIN)["h38_marlin_canonical_scoped"], "PASS")
        with self.assertRaisesRegex(ValueError, "stable argsort"):
            h38.inspect_marlin(MARLIN.replace("stable=True", "stable=False"))

    def test_source_hashes_are_installed_file_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install(root)
            out = h38.inspect_installed(root)
            self.assertEqual(len([k for k in out if k.startswith("sha256_")]), 3)
            self.assertTrue(all(len(v) == 64 for k, v in out.items() if k.startswith("sha256_")))

    def test_r32_checker_must_really_succeed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "r32.py"
            script.write_text(
                'print("R32_PRECREATE_SOURCE_CONTRACT=BEGIN")\n'
                'print("direct_precreate_tensor_alloc_syntax=ABSENT")\n'
                'print("R32_PRECREATE_SOURCE_CONTRACT=END")\n',
                encoding="utf-8",
            )
            self.assertIn("R32_PRECREATE_SOURCE_CONTRACT=END",
                          h38.run_r32(Path(tmp), script))
            script.write_text(
                'print("direct_precreate_tensor_alloc_syntax=PRESENT")\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "incomplete or negative"):
                h38.run_r32(Path(tmp), script)

    def test_runner_guards_production_and_does_not_launch_vllm(self) -> None:
        content = RUNNER.read_text(encoding="utf-8")
        self.assertIn("--runtime runc --network none --read-only", content)
        self.assertIn("--cap-drop ALL --security-opt no-new-privileges", content)
        self.assertIn("--pull never", content)
        self.assertIn("--entrypoint python3", content)
        self.assertIn("--memory 512m --memory-swap 512m", content)
        self.assertIn("checkout_sha_mismatch", content)
        self.assertIn("h38_decoder_scope_label_mismatch", content)
        for unsafe in ("docker build", "docker pull", "systemctl", "drop_caches",
                       "compact_memory", "sysctl -w", "--gpus all"):
            self.assertNotIn(unsafe, content)
        proc = subprocess.run(["bash", "-n", str(RUNNER)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
