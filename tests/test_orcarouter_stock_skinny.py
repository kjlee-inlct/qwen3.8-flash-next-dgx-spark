from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "runtime" / "orcarouter-stock-skinny.sh"


class OrcaRouterStockSkinnyExperimentTests(unittest.TestCase):
    def test_plan_documents_cases_and_fixed_controls(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "plan"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for text in (
            "STOCK   stock Qwen3.8 vLLM image",
            "SKINNY  stock image + GB10/TP=1 skinny-GEMM patch",
            "MODEL_PROFILE=orcarouter",
            "NSPEC=2",
            "MAXLEN=262144",
            "KV_MEM=25769803776",
            "MAXSEQS=3",
            "PREFIX_CACHE=0",
            "INDEX_SHARE=0",
            "AUTOTUNE=0",
            "SPEC=mtp",
        ):
            self.assertIn(text, result.stdout)

    def test_helper_reads_runtime_identity_from_manifest(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('install-maintenance "${STATE_FILE}"', script)
        self.assertIn('MODEL_DIR="${MODEL_DIR}"', script)
        self.assertIn('CONFIG_OVERRIDE="${CONFIG_OVERRIDE}"', script)
        self.assertIn('SERVED_NAME="${SERVED_NAME}"', script)
        self.assertNotIn('MODEL_DIR="${HOME}/models/', script)

    def test_helper_never_mutates_managed_lifecycle(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("systemctl stop", script)
        self.assertNotIn("systemctl start", script)
        self.assertNotIn("write_state", script)
        self.assertNotIn("release-manager.sh", script)
        self.assertIn("stop the managed service before an experiment", script)

    def test_invalid_case_is_rejected(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "start", "INVALID"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("case must be STOCK or SKINNY", result.stderr)


if __name__ == "__main__":
    unittest.main()
