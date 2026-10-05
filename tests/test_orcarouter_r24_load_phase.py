from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "scripts/benchmark/analyze-orcarouter-r24-load-phase.py"


class R24LoadPhaseAnalyzerTest(unittest.TestCase):
    def write(self, root: pathlib.Path, name: str, text: str) -> None:
        (root / name).write_text(text, encoding="utf-8")

    def test_rm_activity_is_localized_inside_weight_load_interval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.write(root, "candidate-request-iso.txt", "2026-10-05T00:00:00+00:00\n")
            self.write(root, "candidate-request-monotonic-ns.txt", "100000000000\n")
            self.write(root, "trace-window-start-iso.txt", "2026-10-05T00:00:20+00:00\n")
            self.write(root, "trace-window-start-monotonic-ns.txt", "120000000000\n")
            self.write(root, "trace-window-end-iso.txt", "2026-10-05T00:01:10+00:00\n")
            self.write(root, "trace-window-end-monotonic-ns.txt", "170000000000\n")
            self.write(root, "host-page-size.txt", "4096\n")
            self.write(
                root,
                "r24-analysis.txt",
                "candidate.largest_5s=start_monotonic=130.000000000 "
                "end_monotonic=135.000000000 delta_mib=+3.000\n",
            )
            self.write(
                root,
                "rm-trace.txt",
                "worker-10 [000] 130.000000: nv_alloc_pages_entry: "
                "page_count=256 page_size=65536 contiguous=0\n"
                "worker-10 [000] 132.000000: nv_alloc_pages_entry: "
                "page_count=256 page_size=65536 contiguous=0\n"
                "worker-10 [000] 134.000000: nv_alloc_pages_entry: "
                "page_count=256 page_size=65536 contiguous=0\n",
            )
            self.write(
                root,
                "candidate-container.log",
                "2026-10-05T00:00:25.000000000Z INFO Loading model from scratch...\n"
                "2026-10-05T00:00:36.000000000Z INFO Loading weights took 11.0 seconds\n"
                "2026-10-05T00:00:38.000000000Z INFO Model loading took 13.0 seconds\n"
                "2026-10-05T00:00:45.000000000Z INFO Capturing CUDA graphs\n",
            )

            run = subprocess.run(
                [sys.executable, str(ANALYZER), str(root)],
                check=True,
                text=True,
                capture_output=True,
            )
            out = run.stdout
            self.assertIn("clock_offset_spread_ms=0.000000", out)
            self.assertIn("rm_order4.total_activity_mib=3.000", out)
            self.assertIn("rm_order4.burst5_activity_mib=3.000", out)
            self.assertIn("weight_load_interval.order4_activity_mib=3.000", out)
            self.assertIn("weight_load_interval.coverage_of_trace_order4_pct=100.000000", out)
            self.assertIn(
                "load_phase_discriminator=RM_ORDER4_ACTIVITY_WITHIN_WEIGHT_LOAD_INTERVAL",
                out,
            )

    def test_missing_weight_marker_is_explicitly_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for iso_name, mono_name, iso_value, mono_value in (
                (
                    "candidate-request-iso.txt",
                    "candidate-request-monotonic-ns.txt",
                    "2026-10-05T00:00:00+00:00\n",
                    "100000000000\n",
                ),
                (
                    "trace-window-start-iso.txt",
                    "trace-window-start-monotonic-ns.txt",
                    "2026-10-05T00:00:20+00:00\n",
                    "120000000000\n",
                ),
                (
                    "trace-window-end-iso.txt",
                    "trace-window-end-monotonic-ns.txt",
                    "2026-10-05T00:01:10+00:00\n",
                    "170000000000\n",
                ),
            ):
                self.write(root, iso_name, iso_value)
                self.write(root, mono_name, mono_value)
            self.write(root, "host-page-size.txt", "4096\n")
            self.write(
                root,
                "r24-analysis.txt",
                "candidate.largest_5s=start_monotonic=130.000000000 "
                "end_monotonic=135.000000000 delta_mib=+1.000\n",
            )
            self.write(
                root,
                "rm-trace.txt",
                "worker-10 [000] 132.000000: nv_alloc_pages_entry: "
                "page_count=256 page_size=65536\n",
            )
            self.write(
                root,
                "candidate-container.log",
                "2026-10-05T00:00:25.000000000Z INFO Loading model from scratch...\n",
            )

            run = subprocess.run(
                [sys.executable, str(ANALYZER), str(root)],
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertIn("marker.weights_end=NA", run.stdout)
            self.assertIn(
                "load_phase_discriminator=INSUFFICIENT_WEIGHT_LOAD_MILESTONES",
                run.stdout,
            )


if __name__ == "__main__":
    unittest.main()
