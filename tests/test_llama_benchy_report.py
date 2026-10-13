"""No-host benchmark report converter safety and numeric provenance tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/benchmark/llama-benchy-report.py"
spec = importlib.util.spec_from_file_location("benchy_report", SOURCE)
assert spec is not None and spec.loader is not None
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
HEX = "a" * 40


def sample() -> dict:
    def measurement(value: float) -> dict:
        return {"mean": value, "std": 1.0, "values": [value]}
    return {
        "version": "0.2.2.dev1", "timestamp": "2026-10-13 12:20:00Z",
        "model": "orcarouter/test", "latency_mode": "generation",
        "prefix_caching_enabled": False,
        "benchmarks": [{
            "concurrency": 1, "context_size": 0,
            "prompt_size": 128, "response_size": 32,
            "is_context_prefill_phase": False,
            "pp_throughput": measurement(1250.0),
            "tg_throughput": measurement(37.2),
            "e2e_ttft": measurement(120.3),
        }],
    }


class LlamaBenchyReportTests(unittest.TestCase):
    def render(self, data: dict) -> str:
        return tool.render(
            data, profile="orcarouter", expected_model="orcarouter/test",
            source_sha=HEX, release_sha=HEX, upstream_sha=HEX,
            raw_sha="b" * 64,
        )

    def test_reports_actual_numbers_with_source_identities(self) -> None:
        out = self.render(sample())
        self.assertIn("1250.00 ± 1.00", out)
        self.assertIn("37.20 ± 1.00", out)
        self.assertIn("120.30 ± 1.00", out)
        self.assertIn("NVIDIA RM", out)
        self.assertIn("b" * 64, out)

    def test_refuses_model_identity_mismatch(self) -> None:
        data = sample()
        data["model"] = "other"
        with self.assertRaisesRegex(tool.ReportError, "identity"):
            self.render(data)

    def test_refuses_unmeasured_empty_benchmarks(self) -> None:
        data = sample()
        data["benchmarks"] = []
        with self.assertRaisesRegex(tool.ReportError, "nonempty"):
            self.render(data)

    def test_refuses_all_null_metrics(self) -> None:
        data = sample()
        row = data["benchmarks"][0]
        row["pp_throughput"] = None
        row["tg_throughput"] = None
        row["e2e_ttft"] = None
        with self.assertRaisesRegex(tool.ReportError, "no numeric"):
            self.render(data)

    def test_refuses_nonfinite_metrics(self) -> None:
        data = sample()
        data["benchmarks"][0]["tg_throughput"]["mean"] = float("nan")
        with self.assertRaisesRegex(tool.ReportError, "invalid mean"):
            self.render(data)

    def test_refuses_markup_injected_metadata(self) -> None:
        data = sample()
        data["version"] = "bad|report"
        with self.assertRaisesRegex(tool.ReportError, "unsafe"):
            self.render(data)

    def test_refuses_writing_over_existing_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            inp = directory / "raw.json"
            dest = directory / "report.md"
            inp.write_text(json.dumps(sample()), encoding="utf-8")
            dest.write_text("protected original\n", encoding="utf-8")
            p = subprocess.run(
                [sys.executable, str(SOURCE),
                 "--profile", "orcarouter", "--input", str(inp),
                 "--output", str(dest), "--expected-model", "orcarouter/test",
                 "--source-sha", HEX, "--release-sha", HEX,
                 "--upstream-sha", HEX],
                text=True, capture_output=True, check=False, timeout=10,
            )
            self.assertEqual(p.returncode, 2, p.stderr)
            self.assertEqual(dest.read_text(), "protected original\n")


if __name__ == "__main__":
    unittest.main()
