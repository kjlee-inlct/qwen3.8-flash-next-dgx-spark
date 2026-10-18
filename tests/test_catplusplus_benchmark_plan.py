"""Synthetic/source-only catplusplus benchmark plan safety regression tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/benchmark/catplusplus-plan.py"
SPEC = importlib.util.spec_from_file_location("catplusplus_benchmark_plan", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class CatplusplusBenchmarkPlanTests(unittest.TestCase):
    def test_pinned_m1_parity_and_no_measured_values(self) -> None:
        plan = MOD.build_plan()
        self.assertEqual(plan["operation"], "SOURCE_ONLY_BENCHMARK_PLAN")
        self.assertEqual(plan["checkpoint_revision"],
                         "3251fd8afbd08f76368a9bfa71132d9aef364813")
        self.assertEqual(plan["repository_size_bytes"], 188540029444)
        self.assertEqual(plan["root_weight_size_gib_rounded"], 174.8553)
        self.assertGreater(
            plan["root_weight_size_gib_rounded"] * MOD.GIB,
            plan["host_unified_ram_bytes_nominal"])
        self.assertEqual(plan["workloads"], [
            {"prompt_tokens": 512, "generate_tokens": 128},
            {"prompt_tokens": 2048, "generate_tokens": 128},
        ])
        self.assertEqual(plan["warmup_runs"], 1)
        self.assertEqual(plan["measured_runs"], 3)
        self.assertEqual(plan["concurrency"], 1)
        self.assertEqual(plan["prefix_caching"], "DISABLED_BASELINE")
        self.assertIsNone(plan["measurements"])
        self.assertFalse(plan["ready"])
        self.assertEqual(plan["benchmark_status"], "NOT_MEASURED")
        self.assertIn("BLOCKED_", plan["admission"])

    def test_source_only_cli_does_not_need_host_or_write_files(self) -> None:
        # Do not stub Bash/Docker and claim protection; this function does not
        # construct or call any subprocess at all.
        with mock.patch.object(MOD, "build_plan", wraps=MOD.build_plan) as build:
            rendered = MOD.render(MOD.build_plan())
            self.assertEqual(build.call_count, 1)
        self.assertIn("CATPLUSPLUS_BENCHMARK_STATUS=NOT_MEASURED", rendered)
        self.assertIn("CATPLUSPLUS_DOCKER_GPU_DOWNLOAD=NOT_PERFORMED", rendered)
        self.assertNotIn("READY=PASS", rendered)
        text = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("docker run", "docker start", "hf download",
                          "torch.cuda", "subprocess.run(", "urlopen(",
                          "requests.get(", "os.system(", "os.remove("):
            self.assertNotIn(forbidden, text)

    def test_json_plan_is_not_a_fake_report(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "plan", "--json"],
            cwd=ROOT, capture_output=True, text=True, check=False, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        doc = json.loads(result.stdout)
        self.assertIsNone(doc["measurements"])
        self.assertEqual(doc["benchmark_status"], "NOT_MEASURED")
        self.assertEqual(doc["permitted_by_this_plan"], "SOURCE_READ_ONLY_NO_HOST_CHANGE")

    def test_unknown_action_fails_closed(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "run"],
            cwd=ROOT, capture_output=True, text=True, check=False, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)


if __name__ == "__main__":
    unittest.main()
