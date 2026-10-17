"""Tests for checksum-gated, raw-line-free Hybrid log marker reports."""
from pathlib import Path
import ast
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/model/hybrid-log-aggregate.py"


class HybridLogAggregateTests(unittest.TestCase):
    def test_parse_and_safety_contract(self):
        text = SOURCE.read_text()
        ast.parse(text)
        for marker in ("module.summarize(root)", "module.sha256(path)",
                       "raw_lines_in_output", "marker_counts_are_not_error_diagnoses",
                       "model_delete_performed", "docker_delete_performed"):
            self.assertIn(marker, text)
        for forbidden in ('docker("rm"', 'docker("stop"', 'docker("start"', "subprocess.",
                          "unlink(", "rmtree(", "write_text("):
            self.assertNotIn(forbidden, text)

if __name__ == "__main__":
    unittest.main()
