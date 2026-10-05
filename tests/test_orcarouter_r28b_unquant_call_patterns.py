import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = REPO / "scripts/benchmark/analyze-orcarouter-r28b-unquant-call-patterns.py"


class R28bUnquantCallPatternsTest(unittest.TestCase):
    def test_reports_sparse_large_rm_activity_across_small_calls(self) -> None:
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
                        "2026-10-05T00:00:02.100000+00:00 QWEN38_R26_MODELOPT_MOE_BEGIN seq=1",
                        "2026-10-05T00:00:02.200000+00:00 QWEN38_R26_MODELOPT_MOE_END seq=1",
                        "2026-10-05T00:00:02.300000+00:00 QWEN38_R28_UNQUANT_LINEAR_BEGIN seq=10 prefix=language_model.model.layers.1.attn_hyper_connection.input_mix_weight_up layer=ReplicatedLinear input=320 output=10240 elements=3276800 dtype=torch.bfloat16",
                        "2026-10-05T00:00:02.500000+00:00 QWEN38_R28_UNQUANT_LINEAR_END seq=10",
                        "2026-10-05T00:00:02.600000+00:00 QWEN38_R28_UNQUANT_LINEAR_BEGIN seq=11 prefix=language_model.model.layers.2.attn_hyper_connection.input_mix_weight_up layer=ReplicatedLinear input=320 output=10240 elements=3276800 dtype=torch.bfloat16",
                        "2026-10-05T00:00:02.700000+00:00 QWEN38_R28_UNQUANT_LINEAR_END seq=11",
                        "2026-10-05T00:00:02.800000+00:00 QWEN38_R28_UNQUANT_LINEAR_BEGIN seq=12 prefix=language_model.model.layers.3.self_attn.qkv_proj layer=QKVParallelLinear input=2560 output=13312 elements=34078720 dtype=torch.bfloat16",
                        "2026-10-05T00:00:02.900000+00:00 QWEN38_R28_UNQUANT_LINEAR_END seq=12",
                        "2026-10-05T00:00:03.000000+00:00 QWEN38_R26_MODEL_CTOR_END",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            # host_page_size=4096: page_count 204800 = 800 MiB,
            # 16384 = 64 MiB, 8192 = 32 MiB, 4096 = 16 MiB.
            (root / "rm-trace.txt").write_text(
                "\n".join(
                    [
                        " test 102.150000: nv_alloc_pages_entry: page_count=4096 page_size=65536",
                        " test 102.400000: nv_alloc_pages_entry: page_count=204800 page_size=65536",
                        " test 102.750000: nv_alloc_pages_entry: page_count=8192 page_size=65536",
                        " test 102.850000: nv_alloc_pages_entry: page_count=16384 page_size=65536",
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
            self.assertIn("R28B_UNQUANT_CALL_PATTERNS=BEGIN", out)
            self.assertIn("selected_unquant_calls=3", out)
            self.assertIn("positive_rm_calls=2", out)
            self.assertIn("zero_rm_calls=1", out)
            self.assertIn("family.hyper_connection.calls=2", out)
            self.assertIn("family.hyper_connection.positive_rm_calls=1", out)
            self.assertIn("family.hyper_connection.zero_rm_calls=1", out)
            self.assertIn(
                "hyper_connection.activity_histogram_mib=0.000:1,800.000:1", out
            )
            self.assertIn(
                "hyper_connection.request_size_histogram_mib=800.000:1", out
            )
            self.assertIn("uncovered_residual_activity_mib=32.000", out)
            self.assertIn("uncovered.request_size_histogram_mib=32.000:1", out)
            self.assertIn(
                "r28b_discriminator=R28B_HYPER_CONNECTION_RM_ACTIVITY_SPARSE_ACROSS_CALLS",
                out,
            )
            self.assertIn("R28B_UNQUANT_CALL_PATTERNS=END", out)


if __name__ == "__main__":
    unittest.main()
