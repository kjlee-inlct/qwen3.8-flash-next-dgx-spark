import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = REPO / "scripts/benchmark/analyze-orcarouter-r31-pre800-moe-boundary.py"


class R31Pre800MoeBoundaryTest(unittest.TestCase):
    def test_pre800_strictly_before_moe_begin(self) -> None:
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
                        "2026-10-05T00:00:02.200000+00:00 QWEN38_R26_MODELOPT_MOE_BEGIN seq=1 experts=128 hidden=1024 intermediate=2048",
                        "2026-10-05T00:00:02.210000+00:00 QWEN38_R26_MODELOPT_W13_BEGIN seq=1",
                        "2026-10-05T00:00:02.260000+00:00 QWEN38_R26_MODELOPT_W13_END seq=1",
                        "2026-10-05T00:00:02.300000+00:00 QWEN38_R26_MODELOPT_MOE_END seq=1",
                        "2026-10-05T00:00:03.000000+00:00 QWEN38_R26_MODEL_CTOR_END",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            page_count_800 = 800 * 1024 * 1024 // 4096
            page_count_400 = 400 * 1024 * 1024 // 4096
            (root / "rm-trace.txt").write_text(
                "\n".join(
                    [
                        f" test 102.190000: nv_alloc_pages_entry: page_count={page_count_800} page_size=65536",
                        f" test 102.230000: nv_alloc_pages_entry: page_count={page_count_400} page_size=65536",
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
            self.assertIn("selected_moe_count=1", out)
            self.assertIn("selected_w13_count=1", out)
            self.assertIn("exact_800_400_pair_count=1", out)
            self.assertIn("pre800_before_moe_begin_count=1", out)
            self.assertIn("pre800_inside_moe_pre_w13_count=0", out)
            self.assertIn(
                "r31_discriminator=R31_PRE800_STRICTLY_BEFORE_MODELOPT_MOE_BEGIN",
                out,
            )


if __name__ == "__main__":
    unittest.main()
