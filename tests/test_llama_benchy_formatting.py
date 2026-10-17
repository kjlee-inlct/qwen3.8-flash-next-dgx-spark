"""Report Markdown escape regression: source never uses invalid backtick escape."""
import importlib.util
from pathlib import Path
import sys
import unittest
import warnings

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/benchmark/llama-benchy-report.py"
spec = importlib.util.spec_from_file_location("report_format_regression", SCRIPT)
assert spec and spec.loader
REPORT = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = REPORT
spec.loader.exec_module(REPORT)


class ReportFormatting(unittest.TestCase):
    def test_backticks_render_without_literal_backslash(self):
        source = SCRIPT.read_text(encoding="utf-8")
        forbidden = chr(92) + chr(96)
        tick = chr(96)
        self.assertNotIn(forbidden, source)
        with warnings.catch_warnings():
            warnings.simplefilter("error", SyntaxWarning)
            compile(source, str(SCRIPT), "exec")
        output = REPORT.render({
            "model": "synthetic/test", "version": "synthetic",
            "timestamp": "2026-10-14T00:00:00Z", "latency_mode": "generation",
            "benchmarks": [{"concurrency": 1, "context_size": 0,
                            "prompt_size": 512, "response_size": 128,
                            "pp_throughput": {"mean": 100, "std": 1}}],
        }, profile="mazinb", expected_model="synthetic/test",
           source_sha="a"*40, release_sha="b"*40,
           upstream_sha="c"*40, raw_sha="d"*64)
        self.assertIn("- Selected project profile: " + tick + "mazinb" + tick, output)
        self.assertNotIn(forbidden, output)


if __name__ == "__main__":
    unittest.main()
