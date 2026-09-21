from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "runtime" / "orcarouter-v029.sh"
DOCKERFILE = ROOT / "scripts" / "Dockerfile.v029-orcarouter"
PLE = ROOT / "scripts" / "vendor" / "vllm_ple_mmap.py"
H7_DOCKERFILE = ROOT / "scripts" / "Dockerfile.v029-h7-modelopt-group"
H7_PATCH = ROOT / "scripts" / "patch-v029-modelopt-moe-group-scale.py"
H8_DOCKERFILE = ROOT / "scripts" / "Dockerfile.v029-h8-ct-block"
H8_PATCH = ROOT / "scripts" / "patch-v029-ct-moe-block-scale.py"
H9_DOCKERFILE = ROOT / "scripts" / "Dockerfile.v029-h9-ct-modelweight-scale"
H9_PATCH = ROOT / "scripts" / "patch-v029-ct-moe-modelweight-scale.py"


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
            "orcarouter|mazinb|hybrid-residual|hybrid-group0",
        ):
            self.assertIn(text, result.stdout)

    def test_runtime_supports_mazinb_without_changing_installability(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('mazinb) NAME="qwen38-mazinb-v029"', script)
        self.assertIn("load_download_profile mazinb", script)
        self.assertIn("source_manifest_ok()", script)
        self.assertIn('data.get("status") == "complete"', script)
        self.assertIn('data.get("repository") == expected_repo', script)
        self.assertIn("load_manifest || return 1", script)

    def test_runtime_supports_residual_hybrid_without_installing_it(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('hybrid-residual) NAME="qwen38-hybrid-residual-v029"', script)
        self.assertIn('MODEL_DIR="${HYBRID_MODEL_DIR:-$HOME/models/qwen3.8-hybrid-residual-bf16}"', script)
        self.assertIn('BASE_MODEL_DIR="${MODEL_DIR}"', script)
        self.assertIn('"${BASE_MODEL_DIR}:/base-model:ro"', script)
        self.assertIn('("residual-bf16", 96, 204)', script)
        self.assertIn('selected = data.get("selected_modules", data.get("residual_modules"))', script)
        self.assertIn('data.get("remaining_fp8_group0_targets") == remaining', script)

    def test_runtime_supports_full_group0_hybrid_without_installing_it(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('hybrid-group0) NAME="qwen38-hybrid-group0-v029"', script)
        self.assertIn('HYBRID_GROUP0_MODEL_DIR', script)
        self.assertIn('qwen3.8-hybrid-group0-bf16', script)
        self.assertIn('data.get("variant") == variant', script)
        self.assertIn('("group0-bf16", 300, 0)', script)
        self.assertIn('selected == count', script)

    def test_runtime_supports_quant_layout_hybrid_without_installing_it(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('hybrid-quant-layout) NAME="qwen38-hybrid-quant-layout-v029"', script)
        self.assertIn("HYBRID_QUANT_LAYOUT_MODEL_DIR", script)
        self.assertIn("qwen3.8-hybrid-quant-layout", script)
        self.assertIn('data.get("variant") == "quant-layout-mazinb-experts"', script)
        self.assertIn('data.get("group0_bf16_weights") == 300', script)
        self.assertIn('data.get("base_expert_tensors_removed") == 221184', script)
        self.assertIn('data.get("overlay_expert_tensors_added") == 294912', script)
        self.assertIn('data.get("mtp_tensors_changed") == 0', script)

    def test_runtime_supports_h4_partial_expert_profiles(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('hybrid-h4-down) NAME="qwen38-h4-down-v029"', script)
        self.assertIn('hybrid-h4-gate-up) NAME="qwen38-h4-gate-up-v029"', script)
        self.assertIn('hybrid-h4-all) NAME="qwen38-h4-all-v029"', script)
        self.assertIn('hybrid-h5-neutral-input) NAME="qwen38-h5-neutral-input-v029"', script)
        self.assertIn('hybrid-h6-w4a16) NAME="qwen38-h6-w4a16-v029"', script)
        self.assertIn('hybrid-h7-group-metadata) NAME="qwen38-h7-group-metadata-v029"', script)
        self.assertIn('hybrid-h8-ct-block) NAME="qwen38-h8-ct-block-v029"', script)
        self.assertIn('hybrid-h9-ct-modelweight) NAME="qwen38-h9-ct-modelweight-v029"', script)
        self.assertIn('IMAGE="vllm-orcarouter-v029-h9-ct-modelweight:v1"', script)
        self.assertIn('IMAGE="vllm-orcarouter-v029-h8-ct-block:v1"', script)
        self.assertIn('IMAGE="vllm-orcarouter-v029-h7-group:v1"', script)
        self.assertIn("H4_ORCA_DOWN_MODEL_DIR", script)
        self.assertIn("H4_ORCA_GATE_UP_MODEL_DIR", script)
        self.assertIn("H4_ORCA_ALL_MODEL_DIR", script)
        self.assertIn("H5_NEUTRAL_INPUT_MODEL_DIR", script)
        self.assertIn("H6_W4A16_MODEL_DIR", script)
        self.assertIn("local/h7-modelopt-group-metadata", script)
        self.assertIn("local/h8-ct-block-over-orcarouter", script)
        self.assertIn("local/h9-ct-modelweight-over-orcarouter", script)
        self.assertIn('${H5_MODEL_DIR}:/h5-parent:ro', script)
        self.assertIn('${BASE_MODEL_DIR}:/base-model:ro', script)
        self.assertIn('${H4_ALL_MODEL_DIR}:/h4-all:ro', script)
        self.assertIn('${H3_MODEL_DIR}:/h3-model:ro', script)
        self.assertIn('data.get("parent_variant") == "quant-layout-mazinb-experts"', script)
        self.assertIn('data.get("input_scale_source") == "mazinb-h3"', script)
        self.assertIn('${H3_MODEL_DIR}:/h3-model:ro', script)

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

    def test_h7_patch_is_narrow_modelopt_moe_metadata_control(self) -> None:
        patch = H7_PATCH.read_text(encoding="utf-8")
        dockerfile = H7_DOCKERFILE.read_text(encoding="utf-8")
        self.assertIn("class ModelOptNvFp4FusedMoE", patch)
        self.assertIn("FusedMoeWeightScaleSupported.BLOCK.value", patch)
        self.assertIn("FusedMoeWeightScaleSupported.GROUP.value", patch)
        self.assertIn("expected exactly one ModelOpt NVFP4 MoE BLOCK metadata assignment", patch)
        self.assertIn("FROM vllm-orcarouter-v029:v1", dockerfile)
        self.assertIn("modelopt-nvfp4-moe-scale-metadata-group", dockerfile)

    def test_h8_patch_is_reciprocal_ct_metadata_control(self) -> None:
        patch = H8_PATCH.read_text(encoding="utf-8")
        dockerfile = H8_DOCKERFILE.read_text(encoding="utf-8")
        self.assertIn("class CompressedTensorsW4A4Nvfp4MoEMethod", patch)
        self.assertIn("FusedMoeWeightScaleSupported.GROUP.value", patch)
        self.assertIn("FusedMoeWeightScaleSupported.BLOCK.value", patch)
        self.assertIn("expected exactly two compressed-tensors NVFP4 MoE GROUP metadata assignments", patch)
        self.assertIn("FROM vllm-orcarouter-v029:v1", dockerfile)
        self.assertIn("compressed-tensors-nvfp4-moe-scale-metadata-block", dockerfile)

    def test_h9_patch_changes_only_ct_scale_parameter_representation(self) -> None:
        patch = H9_PATCH.read_text(encoding="utf-8")
        dockerfile = H9_DOCKERFILE.read_text(encoding="utf-8")
        self.assertIn("ModelWeightParameter", patch)
        self.assertIn('w13_weight_scale = ModelWeightParameter(', patch)
        self.assertIn('w2_weight_scale = ModelWeightParameter(', patch)
        self.assertIn("input_dim=1", patch)
        self.assertIn("output_dim=2", patch)
        self.assertIn("FusedMoeWeightScaleSupported.BLOCK.value", patch)
        self.assertEqual(patch.split("w13_new =", 1)[1].count("FusedMoeWeightScaleSupported.BLOCK.value"), 2)
        self.assertGreaterEqual(patch.count("set_weight_attrs("), 2)
        w13_new = patch.split("w13_new =", 1)[1].split("w2_old =", 1)[0]
        w2_new = patch.split("w2_new =", 1)[1].split("if body.count", 1)[0]
        self.assertNotIn("set_weight_attrs(w13_weight_scale, extra_weight_attrs)", w13_new)
        self.assertNotIn("set_weight_attrs(w2_weight_scale, extra_weight_attrs)", w2_new)
        self.assertIn("FROM vllm-orcarouter-v029:v1", dockerfile)
        self.assertIn("compressed-tensors-nvfp4-scale-modelweight-block-v2", dockerfile)

    def test_h9_runtime_rejects_stale_image_label(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("h9_image_ok()", script)
        self.assertIn("compressed-tensors-nvfp4-scale-modelweight-block-v2", script)
        self.assertIn("stale or incompatible H9 image", script)
        self.assertIn("Dockerfile.v029-h9-ct-modelweight-scale", script)

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
