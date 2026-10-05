import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = REPO / "scripts/benchmark/analyze-orcarouter-r29-global-rm-chunk-cadence.py"


class R29GlobalRmChunkCadenceTest(unittest.TestCase):
    def test_repeated_large_chunk_spans_constructor_regions(self) -> None:
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
                        "2026-10-05T00:00:02.010000+00:00 QWEN38_R27_QWEN4_LAYER_BEGIN seq=1 layer=0 type=linear_attn",
                        "2026-10-05T00:00:02.100000+00:00 QWEN38_R26_MODELOPT_MOE_BEGIN seq=1",
                        "2026-10-05T00:00:02.200000+00:00 QWEN38_R26_MODELOPT_MOE_END seq=1",
                        "2026-10-05T00:00:02.300000+00:00 QWEN38_R28_UNQUANT_LINEAR_BEGIN seq=1 prefix=language_model.model.layers.0.linear_attn.in_proj_qkvz layer=MergedColumnParallelLinear input=2560 output=100 elements=100 dtype=torch.bfloat16",
                        "2026-10-05T00:00:02.400000+00:00 QWEN38_R28_UNQUANT_LINEAR_END seq=1",
                        "2026-10-05T00:00:04.900000+00:00 QWEN38_R27_QWEN4_LAYER_END seq=1",
                        "2026-10-05T00:00:05.000000+00:00 QWEN38_R26_MODEL_CTOR_END",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            page_count_800m = 800 * 1024 * 1024 // 4096
            (root / "rm-trace.txt").write_text(
                "\n".join(
                    [
                        f" test 102.150000: nv_alloc_pages_entry: page_count={page_count_800m} page_size=65536",
                        f" test 102.350000: nv_alloc_pages_entry: page_count={page_count_800m} page_size=65536",
                        f" test 102.600000: nv_alloc_pages_entry: page_count={page_count_800m} page_size=65536",
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
            self.assertIn("R29_GLOBAL_RM_CHUNK_CADENCE=BEGIN", out)
            self.assertIn("constructor_order4_request_count=3", out)
            self.assertIn("constructor_order4_activity_mib=2400.000", out)
            self.assertIn("repeated_large_request_sizes_mib=800.000", out)
            self.assertIn("region.modelopt_moe.request_count=1", out)
            self.assertIn("region.unquant_linear.request_count=1", out)
            self.assertIn("region.other_ctor.request_count=1", out)
            self.assertIn(
                "spanning_repeated_large_request_sizes_mib=800.000", out
            )
            self.assertIn(
                "r29_discriminator=R29_REPEATED_LARGE_RM_CHUNKS_SPAN_MULTIPLE_CONSTRUCTOR_BOUNDARIES",
                out,
            )
            self.assertIn("R29_GLOBAL_RM_CHUNK_CADENCE=END", out)


if __name__ == "__main__":
    unittest.main()
