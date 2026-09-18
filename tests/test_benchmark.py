from __future__ import annotations

import importlib.util
import io
import json
import pathlib
from unittest import mock
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
BENCH = ROOT / "scripts" / "benchmark"
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, BENCH / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


common = load("common")
runner = load("run")


class BenchmarkCommonTests(unittest.TestCase):
    def test_loopback_url_validation(self) -> None:
        self.assertEqual(
            common.validate_base_url("http://127.0.0.1:8888/"),
            "http://127.0.0.1:8888",
        )
        self.assertEqual(
            common.validate_base_url("http://localhost:8888"),
            "http://localhost:8888",
        )
        for invalid in (
            "https://127.0.0.1:8888",
            "http://192.168.0.2:8888",
            "http://user:secret@127.0.0.1:8888",
            "http://127.0.0.1:8888/v1",
            "http://127.0.0.1",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                common.validate_base_url(invalid)

    def test_sse_parser_ignores_non_data_and_stops_at_done(self) -> None:
        stream = io.BytesIO(
            b': keepalive\n\ndata: {"choices": []}\n\nevent: ignored\n\ndata: [DONE]\n\n'
        )
        self.assertEqual(list(common.iter_sse(stream)), [{"choices": []}])

    def test_sse_parser_rejects_invalid_json(self) -> None:
        with self.assertRaises(common.BenchmarkError):
            list(common.iter_sse(io.BytesIO(b"data: not-json\n")))

    def test_summary_statistics(self) -> None:
        summary = common.summarize([0.1, 0.2, 0.3, 2.0])
        self.assertEqual(summary["count"], 4)
        self.assertEqual(summary["median"], 0.25)
        self.assertEqual(summary["p95"], 2.0)
        self.assertEqual(summary["max"], 2.0)
        self.assertEqual(
            common.summarize([]),
            {"count": 0, "median": None, "p95": None, "max": None},
        )

    def test_corpus_uses_unique_sections(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "corpus.txt"
            path.write_text("realistic source text", encoding="utf-8")
            text = common.corpus_text(path, 120)
        self.assertIn("benchmark section 0", text)
        self.assertIn("benchmark section 1", text)
        self.assertGreaterEqual(len(text), 120)

    def test_atomic_report_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "result.json"
            common.write_json_atomic(path, {"schema_version": 1, "status": "pass"})
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"schema_version": 1, "status": "pass"},
            )
            leftovers = [item for item in path.parent.iterdir() if item.name.startswith(".result.json.")]
            self.assertEqual(leftovers, [])


class BenchmarkRunnerTests(unittest.TestCase):
    def test_integer_list_parser(self) -> None:
        self.assertEqual(
            runner.parse_int_list("1,2,4,8", minimum=1, maximum=32),
            [1, 2, 4, 8],
        )
        for invalid in ("", "1,1", "0,1", "1,33", "one,two"):
            with self.subTest(invalid=invalid), self.assertRaises(Exception):
                runner.parse_int_list(invalid, minimum=1, maximum=32)

    def test_decode_prompt_disables_thinking(self) -> None:
        self.assertIn("/no_think", runner.DECODE_PROMPT)

    def test_determinism_hash_is_stable_without_retaining_text(self) -> None:
        first = runner.sha256_text("same output")
        second = runner.sha256_text("same output")
        other = runner.sha256_text("different output")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertEqual(len(first), 64)

    def test_determinism_workload_passes_only_for_identical_outputs(self) -> None:
        same = {
            "choices": [{"message": {"content": "stable"}}],
            "usage": {"prompt_tokens": 8192, "completion_tokens": 3},
        }
        with mock.patch.object(common, "prompt_for_tokens", return_value=("prompt", 8192)), \
             mock.patch.object(common, "request_json", side_effect=[same, same, same]):
            result = runner.run_determinism(
                "http://127.0.0.1:8888", "model", ROOT / "README.md", 8192, 128, 3
            )
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["all_equal"])
        self.assertEqual(result["unique_hashes"], 1)
        self.assertNotIn("stable", json.dumps(result))

        changed = {
            "choices": [{"message": {"content": "changed"}}],
            "usage": {"prompt_tokens": 8192, "completion_tokens": 3},
        }
        with mock.patch.object(common, "prompt_for_tokens", return_value=("prompt", 8192)), \
             mock.patch.object(common, "request_json", side_effect=[same, changed]):
            result = runner.run_determinism(
                "http://127.0.0.1:8888", "model", ROOT / "README.md", 8192, 128, 2
            )
        self.assertEqual(result["status"], "fail")
        self.assertFalse(result["all_equal"])
        self.assertEqual(result["unique_hashes"], 2)

    def test_default_prefill_sizes_cover_existing_benchmark(self) -> None:
        args = runner.parser().parse_args(["prefill"])
        self.assertEqual(args.prefill_sizes, [8192, 16384, 32768])
        self.assertEqual(args.concurrency_levels, [1, 2, 4, 8])

    def test_determinism_parser_defaults(self) -> None:
        args = runner.parser().parse_args(["determinism"])
        self.assertEqual(args.determinism_prompt_tokens, 8192)
        self.assertEqual(args.determinism_output_tokens, 128)
        self.assertEqual(args.determinism_repeats, 3)


if __name__ == "__main__":
    unittest.main()
