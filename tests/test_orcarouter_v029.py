from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "runtime" / "orcarouter-v029.sh"
DOCKERFILE = ROOT / "scripts" / "Dockerfile.v029-orcarouter"
PLE = ROOT / "scripts" / "vendor" / "vllm_ple_mmap.py"


class OrcaRouterV029ExperimentTests(unittest.TestCase):
    def test_help_documents_isolated_v029_controls(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for text in (
            "vllm/vllm-openai:v0.29.0",
            "PLE               mmap",
            "QSA               exact torch.topk",
            "MTP               k=2",
            "prefix cache      disabled",
            "KV cache          24 GiB",
        ):
            self.assertIn(text, result.stdout)

    def test_runtime_never_mutates_managed_lifecycle(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('install-maintenance "${STATE_FILE}"', script)
        self.assertIn("stop it before this experiment", script)
        self.assertNotIn("systemctl stop", script)
        self.assertNotIn("systemctl start", script)
        self.assertNotIn("write_state", script)
        self.assertNotIn("release-manager.sh", script)

    def test_v029_image_is_minimal_and_pinned_to_release(self) -> None:
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        self.assertIn("FROM vllm/vllm-openai:v0.29.0", dockerfile)
        self.assertIn("Qwen4ExpNGramEmbedding", dockerfile)
        self.assertIn("VLLM_QSA_EXACT_TOPK", dockerfile)
        self.assertIn("spark-fla-warps", dockerfile)
        self.assertNotIn("VLLM_FP8_HYBRID", dockerfile)
        self.assertNotIn("DRAFT_VOCAB", dockerfile)

    def test_ple_helper_is_pinned_to_known_upstream_commit(self) -> None:
        ple = PLE.read_text(encoding="utf-8")
        self.assertIn("5be66376e8beaf96655f2d5682c82d538a970e66", ple)
        self.assertIn("Qwen4ExpNGramEmbedding", ple)

    def test_runtime_marks_v029_and_ple_mmap_for_benchmark_evidence(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("QWEN38_VLLM_BASE=v0.29", script)
        self.assertIn("QWEN38_PLE_MMAP=1", script)
        self.assertIn("VLLM_QSA_EXACT_TOPK=1", script)
        self.assertIn("QWEN38_GB10_FLA_FIX=1", script)


if __name__ == "__main__":
    unittest.main()
