import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = REPO / "scripts/benchmark/analyze-orcarouter-r25b-init-model-overlap.py"
RUNNER = REPO / "scripts/benchmark/run-orcarouter-r25b-init-model-boundary.sh"
R24_HARNESS = REPO / "scripts/benchmark/run-orcarouter-hybrid-r24-kv16-rm-mitigation.sh"


class R25bInitModelOverlapTest(unittest.TestCase):
    def test_order4_activity_inside_initialize_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            anchors = [
                ("candidate-request-iso.txt", "candidate-request-monotonic-ns.txt", "1970-01-01T00:16:40+00:00", "2000000000000"),
                ("trace-window-start-iso.txt", "trace-window-start-monotonic-ns.txt", "1970-01-01T00:16:40.100000+00:00", "2000100000000"),
                ("trace-window-end-iso.txt", "trace-window-end-monotonic-ns.txt", "1970-01-01T00:16:40.200000+00:00", "2000200000000"),
            ]
            for iso_name, mono_name, iso_value, mono_value in anchors:
                (root / iso_name).write_text(iso_value + "\n", encoding="utf-8")
                (root / mono_name).write_text(mono_value + "\n", encoding="utf-8")

            (root / "host-page-size.txt").write_text("4096\n", encoding="utf-8")
            (root / "candidate-container.log").write_text(
                "1970-01-01T00:16:41.000000Z worker QWEN38_R25_INIT_MODEL_BEGIN\n"
                "1970-01-01T00:16:41.500000Z worker QWEN38_R25_INIT_MODEL_END\n",
                encoding="utf-8",
            )
            (root / "rm-trace.txt").write_text(
                " worker-1 [000] 2001.100000: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0\n"
                " worker-1 [000] 2001.300000: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [sys.executable, str(ANALYZER), str(root)],
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertIn("init_model_discriminator=RM_ORDER4_WITHIN_INITIALIZE_MODEL", proc.stdout)
            self.assertIn("rm_order4.total_activity_mib=2.000", proc.stdout)
            self.assertIn("rm_order4.inside_init_activity_mib=2.000", proc.stdout)
            self.assertIn("rm_order4.inside_init_pct=100.000000", proc.stdout)

    def test_r25b_runner_rewrites_all_r24_probe_definitions(self) -> None:
        runner = RUNNER.read_text(encoding="utf-8")
        prefix = 'python3 - "${R24_HARNESS}" "${TMP_HARNESS}" "${EXPERIMENT_CONTAINER}" <<\'PY\'\n'
        start = runner.index(prefix) + len(prefix)
        end = runner.index("\nPY\nchmod 700", start)
        transform = runner[start:end]

        with tempfile.TemporaryDirectory() as tmp:
            rendered = pathlib.Path(tmp) / "r25b-harness.sh"
            subprocess.run(
                [
                    sys.executable,
                    "-",
                    str(R24_HARNESS),
                    str(rendered),
                    "qwen38-hybrid-r25b-test",
                ],
                input=transform,
                text=True,
                check=True,
                capture_output=True,
            )
            text = rendered.read_text(encoding="utf-8")

        self.assertEqual(text.count("r25b_rm/"), 4)
        self.assertNotIn("r24_rm/", text)
        self.assertIn('GROUP="r25b_rm"', text)
        self.assertIn('EXPERIMENT_CONTAINER="qwen38-hybrid-r25b-test"', text)


if __name__ == "__main__":
    unittest.main()
