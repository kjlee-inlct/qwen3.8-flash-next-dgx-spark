import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = REPO / "scripts/benchmark/analyze-orcarouter-r27-linear-overlap.py"


class R27LinearOverlapTest(unittest.TestCase):
    def test_w4a16_linear_explains_r26_residual(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            anchors = [
                (
                    "candidate-request-iso.txt",
                    "candidate-request-monotonic-ns.txt",
                    "1970-01-01T00:16:40+00:00",
                    "2000000000000",
                ),
                (
                    "trace-window-start-iso.txt",
                    "trace-window-start-monotonic-ns.txt",
                    "1970-01-01T00:16:40.100000+00:00",
                    "2000100000000",
                ),
                (
                    "trace-window-end-iso.txt",
                    "trace-window-end-monotonic-ns.txt",
                    "1970-01-01T00:16:40.200000+00:00",
                    "2000200000000",
                ),
            ]
            for iso_name, mono_name, iso_value, mono_value in anchors:
                (root / iso_name).write_text(iso_value + "\n", encoding="utf-8")
                (root / mono_name).write_text(mono_value + "\n", encoding="utf-8")

            (root / "host-page-size.txt").write_text("4096\n", encoding="utf-8")
            (root / "candidate-container.log").write_text(
                "1970-01-01T00:16:41.000000Z w QWEN38_R26_MODEL_CTOR_BEGIN class=Qwen4ExpForCausalLM prefix=\n"
                "1970-01-01T00:16:41.050000Z w QWEN38_R27_QWEN4_LAYER_BEGIN seq=1 layer=0 type=linear_attention prefix=model.layers.0\n"
                "1970-01-01T00:16:41.100000Z w QWEN38_R26_MODELOPT_MOE_BEGIN seq=1 experts=512 hidden=2560 intermediate=640\n"
                "1970-01-01T00:16:41.800000Z w QWEN38_R26_MODELOPT_MOE_END seq=1\n"
                "1970-01-01T00:16:41.900000Z w QWEN38_R27_W4A16_LINEAR_BEGIN seq=1 input=2560 output=2560 partitions=1\n"
                "1970-01-01T00:16:41.920000Z w QWEN38_R27_W4A16_WEIGHT_BEGIN seq=1\n"
                "1970-01-01T00:16:42.750000Z w QWEN38_R27_W4A16_WEIGHT_END seq=1\n"
                "1970-01-01T00:16:42.800000Z w QWEN38_R27_W4A16_LINEAR_END seq=1\n"
                "1970-01-01T00:16:42.850000Z w QWEN38_R27_QWEN4_LAYER_END seq=1 layer=0 type=linear_attention\n"
                "1970-01-01T00:16:42.900000Z w QWEN38_R27_QWEN4_LAYER_BEGIN seq=2 layer=1 type=full_attention prefix=model.layers.1\n"
                "1970-01-01T00:16:42.980000Z w QWEN38_R27_QWEN4_LAYER_END seq=2 layer=1 type=full_attention\n"
                "1970-01-01T00:16:43.000000Z w QWEN38_R26_MODEL_CTOR_END class=Qwen4ExpForCausalLM prefix=\n",
                encoding="utf-8",
            )

            # One MiB per row. Total=20 MiB, 19 inside ctor, 8 in MoE,
            # 10 in W4A16 linear, of which 9 are in the packed weight marker.
            times = [2000.500]
            times += [2001.150 + i * 0.075 for i in range(8)]
            times += [2001.930 + i * 0.085 for i in range(9)]
            times += [2002.790]
            times += [2002.950]
            self.assertEqual(len(times), 20)
            rows = [
                f" worker-1 [000] {value:.6f}: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0"
                for value in times
            ]
            (root / "rm-trace.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(ANALYZER), str(root)],
                check=True,
                text=True,
                capture_output=True,
            )

            self.assertIn("rm_order4.total_activity_mib=20.000", proc.stdout)
            self.assertIn("rm_order4.inside_model_ctor_activity_mib=19.000", proc.stdout)
            self.assertIn("r26_modelopt_moe.activity_mib=8.000", proc.stdout)
            self.assertIn("r26_residual_outside_moe.activity_mib=11.000", proc.stdout)
            self.assertIn("w4a16_linear.activity_mib=10.000", proc.stdout)
            self.assertIn("w4a16_linear.pct_of_r26_residual=90.909091", proc.stdout)
            self.assertIn("w4a16_weight.activity_mib=9.000", proc.stdout)
            self.assertIn(
                "residual_discriminator=RM_ORDER4_R26_RESIDUAL_PRIMARY_IN_MODELOPT_W4A16_LINEAR",
                proc.stdout,
            )


if __name__ == "__main__":
    unittest.main()
