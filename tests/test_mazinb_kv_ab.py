from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "runtime" / "mazinb-kv-ab.sh"


class MazinbKvAbExperimentTests(unittest.TestCase):
    def test_plan_documents_two_cases_and_fixed_controls(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "plan"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        for row in (
            "A  KV_MEM=25769803776  (24 GiB, current mazinb default/control)",
            "B  KV_MEM=17179869184  (16 GiB, reduced-KV candidate)",
        ):
            self.assertIn(row, result.stdout)

        for fixed in (
            "MODEL_PROFILE=mazinb",
            "NSPEC=2",
            "MAXLEN=262144",
            "MAXSEQS=3",
            "PREFIX_CACHE=0",
            "INDEX_SHARE=0",
            "AUTOTUNE=0",
            "GPU_UTIL=0.80",
            "QSA_EXACT_TOPK=1",
            "MONITOR_ENABLED=1",
            "MONITOR_PROTECT=1",
            "MONITOR_MIN_FREE_GIB=2",
            "MONITOR_FREE_GATE_GIB=10",
            "MONITOR_CONSECUTIVE=5",
        ):
            self.assertIn(fixed, result.stdout)

        self.assertIn("Run B first", result.stdout)
        self.assertIn("no kernel NV_ERR_NO_MEMORY", result.stdout)

    def test_invalid_case_is_rejected_before_runtime_mutation(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "run", "Z"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("case must be A or B", result.stderr)

    def test_experiment_is_isolated_from_managed_state(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('CONTAINER_NAME="qwen38-mazinb-kv-${CASE_LOWER}"', text)
        self.assertIn('XDG_STATE_HOME="$EXPERIMENT_XDG_STATE_HOME"', text)
        self.assertIn('RESTART_POLICY=no', text)
        self.assertIn('PUBLISH_HOST=127.0.0.1', text)
        self.assertIn("HOST NOT CLASSIFIED", text)
        self.assertNotIn("systemctl stop", text)
        self.assertNotIn("systemctl start", text)
        self.assertNotIn("install.sh", text)


if __name__ == "__main__":
    unittest.main()
