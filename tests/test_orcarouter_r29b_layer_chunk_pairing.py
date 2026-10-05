import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = REPO / "scripts/benchmark/analyze-orcarouter-r29b-layer-chunk-pairing.py"


class R29bLayerChunkPairingTest(unittest.TestCase):
    def test_strict_adjacent_800_then_400_pair_per_layer(self) -> None:
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
                        "2026-10-05T00:00:02.100000+00:00 QWEN38_R27_QWEN4_LAYER_BEGIN seq=1 layer=0 type=linear_attention",
                        "2026-10-05T00:00:02.900000+00:00 QWEN38_R27_QWEN4_LAYER_END seq=1",
                        "2026-10-05T00:00:03.000000+00:00 QWEN38_R27_QWEN4_LAYER_BEGIN seq=2 layer=1 type=qwen_sparse_attention",
                        "2026-10-05T00:00:03.900000+00:00 QWEN38_R27_QWEN4_LAYER_END seq=2",
                        "2026-10-05T00:00:04.000000+00:00 QWEN38_R26_MODEL_CTOR_END",
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
                        f" test 102.200000: nv_alloc_pages_entry: page_count={page_count_800m} page_size=65536",
                        f" test 102.250000: nv_alloc_pages_entry: page_count={page_count_400m} page_size=65536",
                        f" test 102.500000: nv_alloc_pages_entry: page_count={page_count_20m} page_size=65536",
                        f" test 103.200000: nv_alloc_pages_entry: page_count={page_count_800m} page_size=65536",
                        f" test 103.250000: nv_alloc_pages_entry: page_count={page_count_400m} page_size=65536",
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
            self.assertIn("R29B_LAYER_CHUNK_PAIRING=BEGIN", out)
            self.assertIn("selected_layer_count=2", out)
            self.assertIn("size400_request_count=2", out)
            self.assertIn("size800_request_count=2", out)
            self.assertIn("ordinal_pair_count=2", out)
            self.assertIn("pair_800_before_400_count=2", out)
            self.assertIn("pair_adjacent_stream_count=2", out)
            self.assertIn("pair_stream_delta_histogram=1:2", out)
            self.assertIn("layer400.exact_once_count=2", out)
            self.assertIn("layer400.missing_count=0", out)
            self.assertIn("layer800.exact_once_count=2", out)
            self.assertIn("layer800.missing_count=0", out)
            self.assertIn(
                "r29b_discriminator=R29B_STRICT_800_THEN_400_ADJACENT_PAIR_PER_DECODER_LAYER",
                out,
            )
            self.assertIn("R29B_LAYER_CHUNK_PAIRING=END", out)


if __name__ == "__main__":
    unittest.main()
