"""Small deterministic, no-torch CT layerwise accounting counterexamples."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts/benchmark/simulate-h38-ct-layerwise-completion.py"
spec = importlib.util.spec_from_file_location("h38_ct_counterexamples", TOOL)
assert spec and spec.loader
sys.modules[spec.name] = module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class H38CtSyntheticCompletionTests(unittest.TestCase):
    def test_all_named_eight_ct_parameters_are_required(self) -> None:
        self.assertEqual(len(module.REQUIRED), 8)
        self.assertEqual(sum(module.REQUIRED.values()), 20)

    def test_complete_split_loads_do_not_false_finalize(self) -> None:
        for layer in ("8", "11"):
            with self.subTest(layer=layer):
                got = module.simulate(module.REQUIRED, module.normal_events(layer))
                self.assertTrue(got["all_parameters_covered"])
                self.assertEqual(got["credited_elements"], 20)
                self.assertEqual(got["uniquely_covered_elements"], 20)
                self.assertFalse(got["partial_end_finalizer_possible"])

    def test_duplicate_whole_packed_can_reach_gate_while_scales_absent(self) -> None:
        got = module.cases()["duplicate_packed_early_completion"]
        self.assertEqual(got["threshold_processing_event"], 2)
        self.assertEqual(got["credited_elements"], 20)
        self.assertEqual(got["uniquely_covered_elements"], 12)
        self.assertIn("w13_weight_scale", got["missing_elements_by_parameter"])
        self.assertTrue(got["ignored_event_indices_after_processing"])
        self.assertFalse(got["all_parameters_covered"])
        self.assertFalse(got["actual_h38_ct_loader_behavior_proven"])

    def test_duplicate_partial_can_hide_missing_packed_subrange(self) -> None:
        got = module.cases()["duplicate_partial_early_completion"]
        self.assertEqual(got["threshold_processing_event"], 8)
        self.assertEqual(got["credited_elements"], 20)
        self.assertEqual(got["uniquely_covered_elements"], 16)
        self.assertEqual(got["missing_elements_by_parameter"], {"w13_weight_packed": 4})

    def test_partial_end_finalizer_while_weight_incomplete(self) -> None:
        got = module.cases()["split_layer_8_partial_end_finalizer"]
        self.assertIsNone(got["threshold_processing_event"])
        self.assertTrue(got["partial_end_finalizer_possible"])
        self.assertEqual(got["missing_elements_by_parameter"], {"w13_weight_packed": 4})

    def test_repeated_or_out_of_range_input_invalid(self) -> None:
        for required, events in (
            ({"w13_weight_packed": 0}, []),
            (module.REQUIRED, [module.CopyEvent("unknown", 0, 1, "dummy")]),
            (module.REQUIRED, [module.CopyEvent("w13_weight_packed", -1, 1, "dummy")]),
            (module.REQUIRED, [module.CopyEvent("w13_weight_packed", 7, 2, "dummy")]),
            (module.REQUIRED, [module.CopyEvent("w13_weight_packed", 0, 0, "dummy")]),
        ):
            with self.assertRaises(ValueError):
                module.simulate(required, events)

    def test_intervals_count_only_unique_coverage(self) -> None:
        self.assertEqual(module.covered_size([(0, 4), (0, 4), (2, 6)]), 6)
        self.assertEqual(module.covered_size([]), 0)
        self.assertEqual(module.covered_size([(0, 2), (3, 5)]), 4)

    def test_cli_exits_without_gpu_or_model(self) -> None:
        proc = subprocess.run([sys.executable, str(TOOL)],
                              capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("H38_CT_SYNTHETIC_COUNTEREXAMPLES=PASS", proc.stdout)
        self.assertIn("REAL_H38_LOADER_COMPLETENESS=UNVERIFIED", proc.stdout)
        self.assertIn("GPU_OR_MODEL_EXECUTION=NO", proc.stdout)


if __name__ == "__main__":
    unittest.main()
