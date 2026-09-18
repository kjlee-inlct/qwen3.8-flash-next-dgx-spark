from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


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

    def test_prometheus_metric_parsing_and_delta(self) -> None:
        raw = """
# HELP vllm:spec_decode_num_drafts_total Number of drafts.
vllm:spec_decode_num_drafts_total{engine="0",model_name="model"} 10
vllm:spec_decode_num_accepted_tokens_per_pos_total{engine="0",position="0"} 7
vllm:spec_decode_num_accepted_tokens_per_pos_total{engine="0",position="1"} 4
"""
        samples = common.prometheus_samples(raw)
        self.assertEqual(
            common.metric_total(samples, "vllm:spec_decode_num_drafts_total"),
            10.0,
        )
        self.assertEqual(
            common.metric_position_totals(
                samples,
                "vllm:spec_decode_num_accepted_tokens_per_pos_total",
            ),
            {"0": 7.0, "1": 4.0},
        )

        later = common.prometheus_samples(raw.replace(" 10", " 13").replace(" 7", " 9"))
        self.assertEqual(
            common.metric_delta(
                samples,
                later,
                "vllm:spec_decode_num_drafts_total",
            ),
            3.0,
        )
        self.assertEqual(
            common.metric_position_delta(
                samples,
                later,
                "vllm:spec_decode_num_accepted_tokens_per_pos_total",
            ),
            {"0": 2.0, "1": 0.0},
        )

    def test_prometheus_counter_reset_is_unavailable(self) -> None:
        before = {"vllm:generation_tokens_total": 100.0}
        after = {"vllm:generation_tokens_total": 10.0}
        self.assertIsNone(
            common.metric_delta(
                before,
                after,
                "vllm:generation_tokens_total",
            )
        )

    def test_runtime_config_extracts_tuning_controls(self) -> None:
        config = {
            "Image": "vllm-nv-mixed:v2",
            "Cmd": [
                "/model",
                "--served-model-name", "qwen3.8-flash-next",
                "--distributed-executor-backend", "mp",
                "--kv-cache-memory", "16106127360",
                "--max-model-len", "524288",
                "--max-num-seqs", "8",
                "--max-num-batched-tokens", "8192",
                "--no-async-scheduling",
                "--no-enable-prefix-caching",
                "--enable-flashinfer-autotune",
                "--speculative-config",
                '{"method":"mtp","num_speculative_tokens":3,"index_share_for_mtp_iteration":true}',
            ],
        }
        result = common.runtime_config_from_docker_config("qwen38-bench-d", config)
        self.assertEqual(result["container_name"], "qwen38-bench-d")
        self.assertEqual(result["image"], "vllm-nv-mixed:v2")
        self.assertEqual(result["max_model_len"], "524288")
        self.assertEqual(result["kv_cache_memory"], "16106127360")
        self.assertTrue(result["flashinfer_autotune"])
        self.assertFalse(result["prefix_caching"])
        self.assertFalse(result["async_scheduling"])
        self.assertEqual(
            result["speculative_config"],
            {
                "method": "mtp",
                "num_speculative_tokens": 3,
                "index_share_for_mtp_iteration": True,
            },
        )

    def test_metrics_snapshot_is_optional(self) -> None:
        with mock.patch(
            "urllib.request.OpenerDirector.open",
            side_effect=OSError("metrics unavailable"),
        ):
            self.assertIsNone(
                common.metrics_snapshot("http://127.0.0.1:8888")
            )

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
        with mock.patch.object(runner.common, "prompt_for_tokens", return_value=("prompt", 8192)), \
             mock.patch.object(runner.common, "request_json", side_effect=[same, same, same]):
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
        with mock.patch.object(runner.common, "prompt_for_tokens", return_value=("prompt", 8192)), \
             mock.patch.object(runner.common, "request_json", side_effect=[same, changed]):
            result = runner.run_determinism(
                "http://127.0.0.1:8888", "model", ROOT / "README.md", 8192, 128, 2
            )
        self.assertEqual(result["status"], "fail")
        self.assertFalse(result["all_equal"])
        self.assertEqual(result["unique_hashes"], 2)

    def test_speculative_metrics_are_derived_from_counter_delta(self) -> None:
        before = {
            "vllm:spec_decode_num_drafts_total": 10.0,
            "vllm:spec_decode_num_draft_tokens_total": 20.0,
            "vllm:spec_decode_num_accepted_tokens_total": 11.0,
            'vllm:spec_decode_num_accepted_tokens_per_pos_total{position="0"}': 7.0,
            'vllm:spec_decode_num_accepted_tokens_per_pos_total{position="1"}': 4.0,
            "vllm:generation_tokens_total": 20.0,
            "vllm:iteration_tokens_total_count": 10.0,
            "vllm:iteration_tokens_total_sum": 25.0,
        }
        after = {
            "vllm:spec_decode_num_drafts_total": 191.0,
            "vllm:spec_decode_num_draft_tokens_total": 382.0,
            "vllm:spec_decode_num_accepted_tokens_total": 213.0,
            'vllm:spec_decode_num_accepted_tokens_per_pos_total{position="0"}': 126.0,
            'vllm:spec_decode_num_accepted_tokens_per_pos_total{position="1"}': 87.0,
            "vllm:generation_tokens_total": 404.0,
            "vllm:iteration_tokens_total_count": 192.0,
            "vllm:iteration_tokens_total_sum": 454.0,
        }

        result = runner.speculative_metrics(before, after, 12.0)

        self.assertEqual(result["drafts"], 181.0)
        self.assertEqual(result["draft_tokens"], 362.0)
        self.assertEqual(result["accepted_tokens"], 202.0)
        self.assertEqual(result["generation_tokens"], 384.0)
        self.assertEqual(result["engine_steps"], 182.0)
        self.assertEqual(result["iteration_tokens"], 429.0)
        self.assertEqual(result["accepted_tokens_per_position"], {"0": 119.0, "1": 83.0})
        self.assertEqual(result["draft_acceptance_rate"], 0.558011)
        self.assertEqual(result["accepted_per_draft"], 1.116022)
        self.assertEqual(result["generation_per_step"], 2.10989)
        self.assertEqual(result["iteration_tokens_per_step"], 2.357143)
        self.assertEqual(result["steps_s"], 15.166667)

    def test_speculative_metrics_are_optional(self) -> None:
        self.assertIsNone(runner.speculative_metrics(None, None, 1.0))

    def test_default_prefill_sizes_cover_existing_benchmark(self) -> None:
        args = runner.parser().parse_args(["prefill"])
        self.assertEqual(args.prefill_sizes, [8192, 16384, 32768])
        self.assertEqual(args.concurrency_levels, [1, 2, 4, 8])

    def test_tuning_mode_is_available(self) -> None:
        args = runner.parser().parse_args(["tuning"])
        self.assertEqual(args.mode, "tuning")

    def test_determinism_parser_defaults(self) -> None:
        args = runner.parser().parse_args(["determinism"])
        self.assertEqual(args.determinism_prompt_tokens, 8192)
        self.assertEqual(args.determinism_output_tokens, 128)
        self.assertEqual(args.determinism_repeats, 3)


if __name__ == "__main__":
    unittest.main()
