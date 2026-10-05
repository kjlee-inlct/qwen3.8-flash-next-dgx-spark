import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = REPO / "scripts/benchmark/analyze-orcarouter-r26-construction-overlap.py"


class R26ConstructionOverlapTest(unittest.TestCase):
    def test_modelopt_moe_dominates_order4_activity(self) -> None:
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
                "1970-01-01T00:16:41.000000Z worker QWEN38_R26_MODEL_CTOR_BEGIN class=Qwen prefix=\n"
                "1970-01-01T00:16:41.100000Z worker QWEN38_R26_MODELOPT_MOE_BEGIN seq=1 experts=512 hidden=2560 intermediate=640\n"
                "1970-01-01T00:16:41.200000Z worker QWEN38_R26_MODELOPT_W13_BEGIN seq=1\n"
                "1970-01-01T00:16:41.500000Z worker QWEN38_R26_MODELOPT_W13_END seq=1\n"
                "1970-01-01T00:16:41.550000Z worker QWEN38_R26_MODELOPT_W2_BEGIN seq=1\n"
                "1970-01-01T00:16:41.850000Z worker QWEN38_R26_MODELOPT_W2_END seq=1\n"
                "1970-01-01T00:16:41.900000Z worker QWEN38_R26_MODELOPT_MOE_END seq=1\n"
                "1970-01-01T00:16:42.000000Z worker QWEN38_R26_MODEL_CTOR_END class=Qwen prefix=\n",
                encoding="utf-8",
            )

            trace_rows = [
                " worker-1 [000] 2000.500000: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0",
                " worker-1 [000] 2001.210000: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0",
                " worker-1 [000] 2001.250000: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0",
                " worker-1 [000] 2001.300000: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0",
                " worker-1 [000] 2001.400000: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0",
                " worker-1 [000] 2001.490000: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0",
                " worker-1 [000] 2001.560000: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0",
                " worker-1 [000] 2001.620000: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0",
                " worker-1 [000] 2001.700000: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0",
                " worker-1 [000] 2001.800000: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0",
            ]
            (root / "rm-trace.txt").write_text(
                "\n".join(trace_rows) + "\n", encoding="utf-8"
            )

            proc = subprocess.run(
                [sys.executable, str(ANALYZER), str(root)],
                check=True,
                text=True,
                capture_output=True,
            )

            self.assertIn("rm_order4.total_activity_mib=10.000", proc.stdout)
            self.assertIn("rm_order4.inside_model_ctor_activity_mib=9.000", proc.stdout)
            self.assertIn("modelopt_moe.activity_mib=9.000", proc.stdout)
            self.assertIn("modelopt_packed_w13_w2.activity_mib=9.000", proc.stdout)
            self.assertIn("modelopt_moe.selected_call_count=1", proc.stdout)
            self.assertIn(
                "construction_discriminator=RM_ORDER4_PRIMARY_IN_MODELOPT_MOE_CREATE_WEIGHTS",
                proc.stdout,
            )


if __name__ == "__main__":
    unittest.main()
