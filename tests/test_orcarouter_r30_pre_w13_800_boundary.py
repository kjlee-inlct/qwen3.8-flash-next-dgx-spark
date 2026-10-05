import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = REPO / "scripts/benchmark/analyze-orcarouter-r30-pre-w13-800-boundary.py"


class R30PreW13800BoundaryTest(unittest.TestCase):
    def test_exact_w13_400_with_immediate_preceding_800_mixed_placement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "candidate-request-iso.txt").write_text(
                "2026-10-05T00:00:00+00:00\n", encoding="utf-8"
            )
            (root / "candidate-request-monotonic-ns.txt").write_text(
                "100000000000\n", encoding="utf-8"
            )
            (root / "trace-window-start-iso.txt").write_text(
                "2026-10-05T00:00:01+00:00\n", encoding="utf-8"
            )
            (root / "trace-window-start-monotonic-ns.txt").write_text(
                "101000000000\n", encoding="utf-8"
            )
            (root / "trace-window-end-iso.txt").write_text(
                "2026-10-05T00:00:10+00:00\n", encoding="utf-8"
            )
            (root / "trace-window-end-monotonic-ns.txt").write_text(
                "110000000000\n", encoding="utf-8"
            )
            (root / "host-page-size.txt").write_text("4096\n", encoding="utf-8")

            (root / "candidate-container.log").write_text(
                "\n".join(
                    [
                        "2026-10-05T00:00:02.000000+00:00 QWEN38_R26_MODEL_CTOR_BEGIN",
                        "2026-10-05T00:00:02.050000+00:00 QWEN38_R27_QWEN4_LAYER_BEGIN seq=1 layer=0 type=linear_attention",
                        "2026-10-05T00:00:02.100000+00:00 QWEN38_R28_UNQUANT_LINEAR_BEGIN seq=1 prefix=language_model.model.layers.0.attn_hyper_connection.input_mix_weight_up layer=ColumnParallelLinear input=8 output=8 elements=64 dtype=torch.bfloat16",
                        "2026-10-05T00:00:02.160000+00:00 QWEN38_R28_UNQUANT_LINEAR_END seq=1",
                        "2026-10-05T00:00:02.170000+00:00 QWEN38_R26_MODELOPT_W13_BEGIN seq=1",
                        "2026-10-05T00:00:02.260000+00:00 QWEN38_R26_MODELOPT_W13_END seq=1",
                        "2026-10-05T00:00:02.400000+00:00 QWEN38_R27_QWEN4_LAYER_END seq=1 layer=0 type=linear_attention",
                        "2026-10-05T00:00:02.500000+00:00 QWEN38_R27_QWEN4_LAYER_BEGIN seq=2 layer=1 type=qwen_sparse_attention",
                        "2026-10-05T00:00:02.620000+00:00 QWEN38_R26_MODELOPT_W13_BEGIN seq=2",
                        "2026-10-05T00:00:02.700000+00:00 QWEN38_R26_MODELOPT_W13_END seq=2",
                        "2026-10-05T00:00:02.900000+00:00 QWEN38_R27_QWEN4_LAYER_END seq=2 layer=1 type=qwen_sparse_attention",
                        "2026-10-05T00:00:03.000000+00:00 QWEN38_R26_MODEL_CTOR_END",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            page_count_800m = 800 * 1024 * 1024 // 4096
            page_count_400m = 400 * 1024 * 1024 // 4096
            page_count_20m = 20 * 1024 * 1024 // 4096
            (root / "rm-trace.txt").write_text(
                "\n".join(
                    [
                        f" test 102.150000: nv_alloc_pages_entry: page_count={page_count_800m} page_size=65536",
                        f" test 102.200000: nv_alloc_pages_entry: page_count={page_count_400m} page_size=65536",
                        f" test 102.400000: nv_alloc_pages_entry: page_count={page_count_20m} page_size=65536",
                        f" test 102.600000: nv_alloc_pages_entry: page_count={page_count_800m} page_size=65536",
                        f" test 102.650000: nv_alloc_pages_entry: page_count={page_count_400m} page_size=65536",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [sys.executable, str(ANALYZER), str(root)],
                check=True,
                text=True,
                capture_output=True,
            )
            out = completed.stdout
            self.assertIn("R30_PRE_W13_800_BOUNDARY=BEGIN", out)
            self.assertIn("selected_w13_count=2", out)
            self.assertIn("constructor_400_request_count=2", out)
            self.assertIn("w13_exact_one_400_count=2", out)
            self.assertIn("w13_missing_400_count=0", out)
            self.assertIn("w13_multi_400_count=0", out)
            self.assertIn("constructor_400_outside_w13_count=0", out)
            self.assertIn("w13_400_immediate_preceding_800_count=2", out)
            self.assertIn("preceding_800_before_w13_begin_count=2", out)
            self.assertIn(
                "preceding_800_family_histogram=hyper_connection:1,outside_unquant:1",
                out,
            )
            self.assertIn(
                "r30_discriminator=R30_EXACT_W13_400_WITH_IMMEDIATE_PRECEDING_800_MIXED_USERSPACE_PLACEMENT",
                out,
            )
            self.assertIn("R30_PRE_W13_800_BOUNDARY=END", out)


if __name__ == "__main__":
    unittest.main()
