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
            "orcarouter|mazinb|hybrid-residual",
        ):
            self.assertIn(text, result.stdout)

    def test_runtime_supports_mazinb_without_changing_installability(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('mazinb) NAME="qwen38-mazinb-v029"', script)
        self.assertIn("load_download_profile mazinb", script)
        self.assertIn("candidate_manifest_ok()", script)
        self.assertIn('data.get("status") == "complete"', script)
        self.assertIn('data.get("repository") == expected_repo', script)
        self.assertIn("load_manifest || return 1", script)

    def test_runtime_supports_residual_hybrid_without_installing_it(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('hybrid-residual) NAME="qwen38-hybrid-residual-v029"', script)
        self.assertIn('MODEL_DIR="${HYBRID_MODEL_DIR:-$HOME/models/qwen3.8-hybrid-residual-bf16}"', script)
        self.assertIn('BASE_MODEL_DIR="${MODEL_DIR}"', script)
        self.assertIn('"${BASE_MODEL_DIR}:/base-model:ro"', script)
        self.assertIn('data.get("variant") == "residual-bf16"', script)
        self.assertIn('data.get("residual_modules") == 96', script)
        self.assertIn('data.get("remaining_fp8_group0_targets") == 204', script)

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

    def test_v029_layer_type_patch_matches_current_upstream_behavior(self) -> None:
        patch = (ROOT / "scripts" / "patch-v029-qsa-layer-type.py").read_text(encoding="utf-8")
        self.assertIn('("full_attention", "qwen_sparse_attention")', patch)
        self.assertIn('layer_type == "qwen_sparse_attention"', patch)
        self.assertIn('self.layer_type in ("full_attention", "qwen_sparse_attention")', patch)
        self.assertIn("expected v0.29 decoder init block not found", patch)
        self.assertIn("expected v0.29 decoder forward block not found", patch)

    def test_runtime_checks_shared_api_port_before_docker_run(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("port_owner()", script)
        self.assertIn("port_in_use()", script)
        self.assertIn("already published by container(s)", script)
        self.assertIn("occupied by another listener", script)
        self.assertIn("API port %s", script)
    def test_start_message_does_not_claim_readiness(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("container started; readiness pending", script)
        self.assertNotIn("started %s (vLLM v0.29", script)

    def test_runtime_marks_v029_and_ple_mmap_for_benchmark_evidence(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("QWEN38_VLLM_BASE=v0.29", script)
        self.assertIn("QWEN38_PLE_MMAP=1", script)
        self.assertIn("VLLM_QSA_EXACT_TOPK=1", script)
        self.assertIn("QWEN38_GB10_FLA_FIX=1", script)


if __name__ == "__main__":
    unittest.main()
