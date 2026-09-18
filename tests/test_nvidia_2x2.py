from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "runtime" / "nvidia-2x2.sh"


class Nvidia2x2ExperimentTests(unittest.TestCase):
    def test_plan_documents_full_matrix_and_fixed_controls(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "plan"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        for row in (
            "A  INDEX_SHARE=0  AUTOTUNE=0",
            "B  INDEX_SHARE=1  AUTOTUNE=0",
            "C  INDEX_SHARE=0  AUTOTUNE=1",
            "D  INDEX_SHARE=1  AUTOTUNE=1",
        ):
            self.assertIn(row, result.stdout)

        for fixed in (
            "MODEL_PROFILE=nvidia",
            "NSPEC=3",
            "MAXLEN=524288",
            "KV_MEM=16106127360",
            "MAXSEQS=8",
            "PREFIX_CACHE=0",
        ):
            self.assertIn(fixed, result.stdout)

        self.assertIn("only controls temporary experiment containers", result.stdout)
        self.assertIn("benchmark harness separately", result.stdout)

    def test_preflight_documents_missing_asset_commands(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "preflight"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env={"HOME": "/tmp/qwen38-empty-home", "PATH": "/usr/bin:/bin"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MODEL_PROFILE=nvidia ./scripts/download-weights.sh --check", result.stdout)
        self.assertIn("docker build -t vllm-nv-mixed:v2", result.stdout)

    def test_invalid_case_is_rejected_without_starting_runtime(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "start", "Z"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("case must be A, B, C, or D", result.stderr)


if __name__ == "__main__":
    unittest.main()
