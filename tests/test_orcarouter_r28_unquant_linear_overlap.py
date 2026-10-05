import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = REPO / "scripts/benchmark/analyze-orcarouter-r28-unquant-linear-overlap.py"


class R28UnquantLinearOverlapTest(unittest.TestCase):
    def test_reports_separate_rm_and_nominal_payload_semantics(self) -> None:
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
                        "2026-10-05T00:00:02.300000+00:00 QWEN38_R28_UNQUANT_LINEAR_BEGIN seq=1 prefix=model.language_model.layers.0.linear_attn.in_proj_qkvz layer=MergedColumnParallelLinear input=2560 output=100 elements=100 dtype=torch.bfloat16",
                        "2026-10-05T00:00:02.500000+00:00 QWEN38_R28_UNQUANT_LINEAR_END seq=1",
                        "2026-10-05T00:00:03.000000+00:00 QWEN38_R26_MODEL_CTOR_END",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "rm-trace.txt").write_text(
                "\n".join(
                    [
                        " test 102.150000: nv_alloc_pages_entry: page_count=16 page_size=65536",
                        " test 102.400000: nv_alloc_pages_entry: page_count=16 page_size=65536",
                        " test 102.800000: nv_alloc_pages_entry: page_count=16 page_size=65536",
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
            self.assertIn("R28_UNQUANT_LINEAR_OVERLAP=BEGIN", out)
            self.assertIn(
                "rm_bytes_semantics=activity_volume_not_resident_ownership", out
            )
            self.assertIn(
                "payload_semantics=nominal_unquantized_weight_tensor_bytes", out
            )
            self.assertIn("r26_residual_outside_moe.activity_mib=0.125", out)
            self.assertIn("unquant_linear.in_r26_residual_activity_mib=0.062", out)
            self.assertIn("unquant_linear.pct_of_r26_residual=50.000000", out)
            self.assertIn("family.linear_attn.calls=1", out)
            self.assertIn(
                "unquant_linear_discriminator=RM_ORDER4_R26_RESIDUAL_MIXED_OUTSIDE_UNQUANTIZED_LINEAR_CONSTRUCTION",
                out,
            )
            self.assertIn("R28_UNQUANT_LINEAR_OVERLAP=END", out)


if __name__ == "__main__":
    unittest.main()
