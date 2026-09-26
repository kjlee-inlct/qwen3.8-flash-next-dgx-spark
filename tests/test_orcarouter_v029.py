from __future__ import annotations

import subprocess
import sys
import tempfile
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
H10_DOCKERFILE = ROOT / "scripts" / "Dockerfile.v029-h10-ct-global-scale"
H10_PATCH = ROOT / "scripts" / "patch-v029-ct-moe-global-scale-modelparam.py"


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
        self.assertIn('hybrid-h10-ct-global-scale) NAME="qwen38-h10-ct-global-scale-v029"', script)
        self.assertIn('IMAGE="vllm-orcarouter-v029-h10-ct-global-scale:v1"', script)
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

    def test_h10_patch_changes_only_ct_global_scale_representation(self) -> None:
        patch = H10_PATCH.read_text(encoding="utf-8")
        dockerfile = H10_DOCKERFILE.read_text(encoding="utf-8")
        self.assertIn("PerTensorScaleParameter", patch)
        self.assertGreaterEqual(patch.count("FusedMoeWeightScaleSupported.TENSOR.value"), 2)
        self.assertGreaterEqual(patch.count("set_weight_attrs("), 2)
        self.assertIn('w13_weight_scale_2 = PerTensorScaleParameter(', patch)
        self.assertIn('w2_weight_scale_2 = PerTensorScaleParameter(', patch)
        self.assertIn("(1.0 / w13_weight_global_scale)", dockerfile)
        self.assertIn("(1.0 / layer.w2_weight_global_scale)", dockerfile)
        self.assertIn("FROM vllm-orcarouter-v029-h9-ct-modelweight:v1", dockerfile)
        self.assertIn("compressed-tensors-global-scale-pertensor-v1", dockerfile)

    def test_h10_runtime_rejects_stale_image_label(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("h10_image_ok()", script)
        self.assertIn("compressed-tensors-global-scale-pertensor-v1", script)
        self.assertIn("stale or incompatible H10 image", script)
        self.assertIn("Dockerfile.v029-h10-ct-global-scale", script)

    def test_h9_runtime_rejects_stale_image_label(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("h9_image_ok()", script)
        self.assertIn("compressed-tensors-nvfp4-scale-modelweight-block-v2", script)
        self.assertIn("stale or incompatible H9 image", script)
        self.assertIn("Dockerfile.v029-h9-ct-modelweight-scale", script)

    def test_runtime_stop_preserves_container_unless_remove_requested(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("REMOVE_AFTER_STOP=0", script)
        self.assertIn("--remove) REMOVE_AFTER_STOP=1", script)
        self.assertIn('docker stop --timeout 30 "${NAME}"', script)
        self.assertIn("preserved for diagnostics", script)
        self.assertIn('if [[ "${REMOVE_AFTER_STOP}" == 1 ]]', script)
        self.assertNotIn('docker rm -f "${NAME}"', script)

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


    def test_h11_runtime_and_patch_are_registered(self) -> None:
        patch = (ROOT / "scripts" / "patch-v029-ct-moe-packed-modelweight.py").read_text(encoding="utf-8")
        dockerfile = (ROOT / "scripts" / "Dockerfile.v029-h11-ct-packed-modelweight").read_text(encoding="utf-8")
        runtime = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("w13_weight = ModelWeightParameter(", patch)
        self.assertIn("w2_weight = ModelWeightParameter(", patch)
        self.assertIn("compressed-tensors-packed-modelweight-v1", dockerfile)
        self.assertIn("hybrid-h11-ct-packed-modelweight", runtime)


    def test_h12_preserves_modelweight_object_across_postload_rename(self) -> None:
        patch = (ROOT / "scripts" / "patch-v029-ct-moe-postload-preserve-weight-param.py").read_text(encoding="utf-8")
        dockerfile = (ROOT / "scripts" / "Dockerfile.v029-h12-ct-postload-preserve").read_text(encoding="utf-8")
        runtime = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('register_parameter("w13_weight", layer.w13_weight_packed)', patch)
        self.assertIn('register_parameter("w2_weight", layer.w2_weight_packed)', patch)
        self.assertIn("assert 'layer.w13_weight = torch.nn.Parameter(' not in body", dockerfile)
        self.assertIn("compressed-tensors-postload-preserve-modelweight-v1", dockerfile)
        self.assertIn("hybrid-h12-ct-postload-preserve", runtime)


    def test_h13_changes_only_input_global_scale_parameter_objects(self) -> None:
        patch = (ROOT / "scripts" / "patch-v029-ct-moe-input-scale-modelparam.py").read_text(encoding="utf-8")
        dockerfile = (ROOT / "scripts" / "Dockerfile.v029-h13-ct-input-scale").read_text(encoding="utf-8")
        runtime = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("w13_input_scale = PerTensorScaleParameter(", patch)
        self.assertIn("w2_input_scale = PerTensorScaleParameter(", patch)
        self.assertIn("compressed-tensors-input-scale-pertensor-v1", dockerfile)
        self.assertIn("hybrid-h13-ct-input-scale", runtime)


    def test_h14_changes_only_postload_input_scale_registration(self) -> None:
        patch = (ROOT / "scripts" / "patch-v029-ct-moe-postload-register-input-scale.py").read_text(encoding="utf-8")
        dockerfile = (ROOT / "scripts" / "Dockerfile.v029-h14-ct-input-scale-postload").read_text(encoding="utf-8")
        runtime = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"w13_input_scale",', patch)
        self.assertIn("torch.nn.Parameter(a13_scale", patch)
        self.assertIn("FROM vllm-orcarouter-v029-h12-ct-postload-preserve:v1", dockerfile)
        self.assertIn("compressed-tensors-postload-input-scale-parameter-v1", dockerfile)
        self.assertIn("hybrid-h14-ct-input-scale-postload", runtime)


    def test_h15_reuses_h14_image_and_disables_mtp_only(self) -> None:
        runtime = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('hybrid-h15-mtp-off) NAME="qwen38-h15-mtp-off-v029"; IMAGE="vllm-orcarouter-v029-h14-ct-input-scale-postload:v1"', runtime)
        self.assertIn('if [[ "${PROFILE_CASE}" != hybrid-h15-mtp-off && "${PROFILE_CASE}" != hybrid-h16-single-seq ]]; then', runtime)
        self.assertIn('speculative_args=(--speculative-config \'{"method":"mtp","num_speculative_tokens":2}\')', runtime)
        self.assertIn('"${speculative_args[@]}"', runtime)
        self.assertIn('SERVED_NAME="hybrid-h15-mtp-off/Qwen3.8-Flash-Next-Uncensored-NVFP4"', runtime)


    def test_h16_reuses_h14_image_disables_mtp_and_sets_single_sequence(self) -> None:
        runtime = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('hybrid-h16-single-seq) NAME="qwen38-h16-single-seq-v029"; IMAGE="vllm-orcarouter-v029-h14-ct-input-scale-postload:v1"', runtime)
        self.assertIn('if [[ "${PROFILE_CASE}" != hybrid-h15-mtp-off && "${PROFILE_CASE}" != hybrid-h16-single-seq ]]; then', runtime)
        self.assertIn('if [[ "${PROFILE_CASE}" == hybrid-h16-single-seq ]]; then', runtime)
        self.assertIn('max_num_seqs=1', runtime)
        self.assertIn('--max-num-seqs "${max_num_seqs}"', runtime)
        self.assertIn('SERVED_NAME="hybrid-h16-single-seq/Qwen3.8-Flash-Next-Uncensored-NVFP4"', runtime)


    def test_h17_patch_executes_against_h12_postload_shape(self) -> None:
        patch = ROOT / "scripts" / "patch-v029-ct-moe-postload-weight-scale2-lifecycle.py"
        fixture = """class CompressedTensorsW4A4Nvfp4MoEMethod:
    def process_weights_after_loading(self, layer):
        # Use a single gscale for w13.
        if self.moe.is_act_and_mul and not torch.allclose(
            layer.w13_weight_global_scale[:, 0], layer.w13_weight_global_scale[:, 1]
        ):
            pass
        w13_weight_global_scale = layer.w13_weight_global_scale[:, 0].contiguous()
        values = convert(
            w13_scale_2=(1.0 / w13_weight_global_scale),
            a13_scale=(1.0 / layer.w13_input_global_scale),
            w2_scale_2=(1.0 / layer.w2_weight_global_scale),
            a2_scale=(1.0 / layer.w2_input_global_scale),
        )
        replace_parameter(layer, "w13_weight_scale_2", w13_scale_2)
        replace_parameter(layer, "w2_weight_scale_2", w2_scale_2)
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "ct.py"
            target.write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                ["python3", str(patch), str(target)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            patched = target.read_text(encoding="utf-8")
        self.assertIn('register_parameter("w13_weight_scale_2", w13_weight_scale_2_param)', patched)
        self.assertIn('register_parameter("w2_weight_scale_2", w2_weight_scale_2_param)', patched)
        self.assertIn("layer.w13_weight_scale_2[:, 0], layer.w13_weight_scale_2[:, 1]", patched)
        self.assertIn("w13_weight_scale_2 = layer.w13_weight_scale_2[:, 0].contiguous()", patched)
        self.assertIn("w13_scale_2=(1.0 / w13_weight_scale_2)", patched)
        self.assertIn("w2_scale_2=(1.0 / layer.w2_weight_scale_2)", patched)
        self.assertIn("a13_scale=(1.0 / layer.w13_input_global_scale)", patched)
        self.assertIn("a2_scale=(1.0 / layer.w2_input_global_scale)", patched)


    def test_h17_canonicalizes_weight_scale2_before_postload_replace(self) -> None:
        patch = (ROOT / "scripts" / "patch-v029-ct-moe-postload-weight-scale2-lifecycle.py").read_text(encoding="utf-8")
        dockerfile = (ROOT / "scripts" / "Dockerfile.v029-h17-ct-weight-scale2-postload").read_text(encoding="utf-8")
        runtime = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('register_parameter("w13_weight_scale_2", w13_weight_scale_2_param)', patch)
        self.assertIn('register_parameter("w2_weight_scale_2", w2_weight_scale_2_param)', patch)
        self.assertIn('delattr(layer, "w13_weight_global_scale")', patch)
        self.assertIn('delattr(layer, "w2_weight_global_scale")', patch)
        self.assertIn("w13_scale_2=(1.0 / w13_weight_scale_2)", patch)
        self.assertIn("w2_scale_2=(1.0 / layer.w2_weight_scale_2)", patch)
        self.assertIn("FROM vllm-orcarouter-v029-h12-ct-postload-preserve:v1", dockerfile)
        self.assertIn("compressed-tensors-postload-weight-scale2-lifecycle-v1", dockerfile)
        self.assertIn("hybrid-h17-ct-weight-scale2-postload", runtime)


    def test_h18_patch_executes_against_h12_input_scale_shape(self) -> None:
        patch = ROOT / "scripts" / "patch-v029-ct-moe-postload-input-scale-lifecycle.py"
        fixture = """class CompressedTensorsW4A4Nvfp4MoEMethod:
    def process_weights_after_loading(self, layer):
        # Use a single gscale for w13.
        values = convert(
            w13_scale_2=(1.0 / w13_weight_global_scale),
            a13_scale=(1.0 / layer.w13_input_global_scale),
            w2_scale_2=(1.0 / layer.w2_weight_global_scale),
            a2_scale=(1.0 / layer.w2_input_global_scale),
        )
        replace_parameter(layer, "w13_weight_scale_2", w13_scale_2)
        replace_parameter(layer, "w2_weight_scale_2", w2_scale_2)
        layer.w13_input_scale = a13_scale
        layer.w2_input_scale = a2_scale
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "ct.py"
            target.write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                ["python3", str(patch), str(target)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            patched = target.read_text(encoding="utf-8")
        self.assertIn('register_parameter("w13_input_scale", w13_input_scale_param)', patched)
        self.assertIn('register_parameter("w2_input_scale", w2_input_scale_param)', patched)
        self.assertIn("a13_scale=(1.0 / layer.w13_input_scale)", patched)
        self.assertIn("a2_scale=(1.0 / layer.w2_input_scale)", patched)
        self.assertIn('replace_parameter(layer, "w13_input_scale", a13_scale)', patched)
        self.assertIn('replace_parameter(layer, "w2_input_scale", a2_scale)', patched)
        self.assertIn("w13_scale_2=(1.0 / w13_weight_global_scale)", patched)
        self.assertIn("w2_scale_2=(1.0 / layer.w2_weight_global_scale)", patched)


    def test_h18_canonicalizes_input_scale_without_h17_weight_scale2_change(self) -> None:
        patch = (ROOT / "scripts" / "patch-v029-ct-moe-postload-input-scale-lifecycle.py").read_text(encoding="utf-8")
        dockerfile = (ROOT / "scripts" / "Dockerfile.v029-h18-ct-input-scale-lifecycle").read_text(encoding="utf-8")
        runtime = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('register_parameter("w13_input_scale", w13_input_scale_param)', patch)
        self.assertIn('register_parameter("w2_input_scale", w2_input_scale_param)', patch)
        self.assertIn('delattr(layer, "w13_input_global_scale")', patch)
        self.assertIn('delattr(layer, "w2_input_global_scale")', patch)
        self.assertIn("a13_scale=(1.0 / layer.w13_input_scale)", patch)
        self.assertIn("a2_scale=(1.0 / layer.w2_input_scale)", patch)
        self.assertNotIn("w13_weight_scale_2_param", patch)
        self.assertIn("FROM vllm-orcarouter-v029-h12-ct-postload-preserve:v1", dockerfile)
        self.assertIn("compressed-tensors-postload-input-scale-lifecycle-v1", dockerfile)
        self.assertIn("hybrid-h18-ct-input-scale-lifecycle", runtime)


    def test_h19_composes_h17_then_h18_against_h12_shape(self) -> None:
        h17 = ROOT / "scripts" / "patch-v029-ct-moe-postload-weight-scale2-lifecycle.py"
        h18 = ROOT / "scripts" / "patch-v029-ct-moe-postload-input-scale-lifecycle.py"
        fixture = """class CompressedTensorsW4A4Nvfp4MoEMethod:
    def process_weights_after_loading(self, layer):
        # Use a single gscale for w13.
        if self.moe.is_act_and_mul and not torch.allclose(
            layer.w13_weight_global_scale[:, 0], layer.w13_weight_global_scale[:, 1]
        ):
            pass
        w13_weight_global_scale = layer.w13_weight_global_scale[:, 0].contiguous()
        values = convert(
            w13_scale_2=(1.0 / w13_weight_global_scale),
            a13_scale=(1.0 / layer.w13_input_global_scale),
            w2_scale_2=(1.0 / layer.w2_weight_global_scale),
            a2_scale=(1.0 / layer.w2_input_global_scale),
        )
        replace_parameter(layer, "w13_weight_scale_2", w13_scale_2)
        replace_parameter(layer, "w2_weight_scale_2", w2_scale_2)
        layer.w13_input_scale = a13_scale
        layer.w2_input_scale = a2_scale
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "ct.py"
            target.write_text(fixture, encoding="utf-8")
            for patch in (h17, h18):
                result = subprocess.run(
                    ["python3", str(patch), str(target)],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            patched = target.read_text(encoding="utf-8")
        self.assertIn('register_parameter("w13_weight_scale_2", w13_weight_scale_2_param)', patched)
        self.assertIn('register_parameter("w2_weight_scale_2", w2_weight_scale_2_param)', patched)
        self.assertIn('register_parameter("w13_input_scale", w13_input_scale_param)', patched)
        self.assertIn('register_parameter("w2_input_scale", w2_input_scale_param)', patched)
        self.assertIn("w13_scale_2=(1.0 / w13_weight_scale_2)", patched)
        self.assertIn("w2_scale_2=(1.0 / layer.w2_weight_scale_2)", patched)
        self.assertIn("a13_scale=(1.0 / layer.w13_input_scale)", patched)
        self.assertIn("a2_scale=(1.0 / layer.w2_input_scale)", patched)


    def test_h19_image_combines_only_h17_and_h18_over_h12(self) -> None:
        dockerfile = (ROOT / "scripts" / "Dockerfile.v029-h19-ct-combined-lifecycle").read_text(encoding="utf-8")
        runtime = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("FROM vllm-orcarouter-v029-h12-ct-postload-preserve:v1", dockerfile)
        self.assertIn("patch-v029-ct-moe-postload-weight-scale2-lifecycle.py", dockerfile)
        self.assertIn("patch-v029-ct-moe-postload-input-scale-lifecycle.py", dockerfile)
        self.assertIn("H19 combined CT post-load lifecycle patches installed", dockerfile)
        self.assertIn("compressed-tensors-postload-combined-lifecycle-v1", dockerfile)
        self.assertIn("hybrid-h19-ct-combined-lifecycle", runtime)


    def test_h20_diagnostic_patcher_is_bounded_and_normalized(self) -> None:
        patch = (ROOT / "scripts" / "patch-v029-nvfp4-moe-convert-diagnostics.py").read_text(encoding="utf-8")
        collector = (ROOT / "scripts" / "diagnostics" / "h20-nvfp4-moe.py").read_text(encoding="utf-8")
        self.assertIn("QWEN38_H20_DIAG_MAX_CALLS", patch)
        self.assertIn("QWEN38_H20_DIAG_FULL_HASH_MAX_BYTES", patch)
        self.assertIn("head-middle-tail-elements", patch)
        self.assertIn("metadata-only-noncontiguous", patch)
        self.assertIn('source="ct"', patch)
        self.assertIn('source="modelopt"', patch)
        self.assertIn('"w13_scale_2"', patch)
        self.assertIn('"a13_scale"', patch)
        self.assertIn("QWEN38_H20_MOE_DIAG ", patch)
        self.assertIn("first_mismatch", collector)
        self.assertIn("hash_scope", collector)
        self.assertIn("sha256", collector)
        self.assertIn("phase=\"quant_config\"", patch)
        self.assertIn("phase=\"kernel_created\"", patch)
        self.assertIn("phase=\"fused_postload\"", patch)
        self.assertIn("left is None and right is None", collector)

    def test_h20_images_are_h12_ct_vs_h6_modelopt_diagnostics(self) -> None:
        ct = (ROOT / "scripts" / "Dockerfile.v029-h20-ct-convert-diag").read_text(encoding="utf-8")
        mo = (ROOT / "scripts" / "Dockerfile.v029-h20-modelopt-convert-diag").read_text(encoding="utf-8")
        runtime = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("FROM vllm-orcarouter-v029-h12-ct-postload-preserve:v1", ct)
        self.assertIn(" ct", ct)
        self.assertIn("ct-nvfp4-convert-diag-v21", ct)
        self.assertIn("FROM vllm-orcarouter-v029:v1", mo)
        self.assertIn(" modelopt", mo)
        self.assertIn("modelopt-nvfp4-convert-diag-v13", mo)
        self.assertIn("hybrid-h20-ct-convert-diag", runtime)
        self.assertIn("hybrid-h20-modelopt-convert-diag", runtime)
        self.assertIn("QWEN38_H20_DIAG_MAX_CALLS=4", runtime)
        self.assertIn("QWEN38_H20_DIAG_SAMPLE_ELEMS=1024", runtime)
        self.assertIn('QWEN38_H20_CUDA_LAUNCH_BLOCKING:-0', runtime)
        self.assertIn('h20_env+=( -e CUDA_LAUNCH_BLOCKING=1 )', runtime)
        self.assertIn('QWEN38_H20U_CAPTURE_LAYER14="${QWEN38_H20U_CAPTURE_LAYER14:-1}"', runtime)
        self.assertIn('QWEN38_H20U_LAYER14_GROUP="${QWEN38_H20U_LAYER14_GROUP:-all}"', runtime)
        self.assertIn('VLLM_CACHE_ROOT="/root/.cache/vllm/h20u-layer14-${QWEN38_H20U_LAYER14_GROUP:-all}"', runtime)
        self.assertIn("QWEN38_H20C_MAX_CALLS=128", runtime)
        self.assertIn("QWEN38_H20C_SAMPLE_ELEMS=1024", runtime)
        self.assertIn("QWEN38_H20D_TARGET_LAYER=language_model.model.layers.0.mlp.experts", runtime)
        self.assertIn("h20_image_ok()", runtime)


    def test_h20_fp8_batch_invariant_repair_profile_is_diagnostic_free(self) -> None:
        dockerfile = (
            ROOT / "scripts" / "Dockerfile.v029-h20-fp8-bi-repair"
        ).read_text(encoding="utf-8")
        runtime = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(
            "FROM vllm-orcarouter-v029-h12-ct-postload-preserve:v1",
            dockerfile,
        )
        self.assertIn(
            "patch-v029-h20-humming-fp8-batch-invariant.py",
            dockerfile,
        )
        self.assertIn(
            'LABEL qwen38.h20repair="ct-h12-humming-fp8-batch-invariant-v1"',
            dockerfile,
        )
        self.assertNotIn("patch-v029-h20-linear-attn-layer0.py", dockerfile)
        self.assertNotIn("patch-v029-h20c-runtime-moe-trace.py", dockerfile)
        self.assertNotIn("patch-v029-h20-upstream-layer0.py", dockerfile)
        self.assertIn("hybrid-h20-ct-fp8-bi-repair", runtime)
        self.assertIn("qwen38-h20-ct-fp8-bi-repair-v029", runtime)
        self.assertIn("vllm-orcarouter-v029-h20-fp8-bi-repair:v1", runtime)
        self.assertIn("ct-h12-humming-fp8-batch-invariant-v1", runtime)
        self.assertIn("runtime-repair-candidate", runtime)

    def test_h20_patcher_executes_on_v029_ct_and_modelopt_shapes(self) -> None:
        patch = ROOT / "scripts" / "patch-v029-nvfp4-moe-convert-diagnostics.py"
        ct_block = """import torch
logger = init_logger(__name__)
class CompressedTensorsW4A4Nvfp4MoEMethod:
    def process_weights_after_loading(self, layer):
        # Shuffle weights into the NvFp4 kernel format.
        (
            w13,
            w13_scale,
            w13_scale_2,
            a13_scale,
            w2,
            w2_scale,
            w2_scale_2,
            a2_scale,
        ) = convert_to_nvfp4_moe_kernel_format(
            nvfp4_backend=self.nvfp4_backend,
            layer=layer,
            w13=layer.w13_weight,
            w13_scale=layer.w13_weight_scale,
            w13_scale_2=(1.0 / w13_weight_global_scale),
            a13_scale=(1.0 / layer.w13_input_global_scale),
            w2=layer.w2_weight,
            w2_scale=layer.w2_weight_scale,
            w2_scale_2=(1.0 / layer.w2_weight_global_scale),
            a2_scale=(1.0 / layer.w2_input_global_scale),
            is_act_and_mul=self.moe.is_act_and_mul,
            use_a16=self.use_a16,
        )
        self.moe_quant_config = self.get_fused_moe_quant_config(layer)
        assert self.experts_cls is not None
        self.moe_kernel = make_nvfp4_moe_kernel(
            moe_quant_config=self.moe_quant_config,
            moe_config=self.moe,
            experts_cls=self.experts_cls,
            backend=self.nvfp4_backend,
            routing_tables=layer._expert_routing_tables(),
        )
        self.moe_kernel.fused_experts.process_weights_after_loading(layer)
"""
        mo_block = """import torch
logger = init_logger(__name__)
class ModelOptNvFp4FusedMoE:
    def process_weights_after_loading(self, layer):
        (
            w13,
            w13_scale,
            w13_scale_2,
            a13_scale,
            w2,
            w2_scale,
            w2_scale_2,
            a2_scale,
        ) = convert_to_nvfp4_moe_kernel_format(
            nvfp4_backend=self.nvfp4_backend,
            layer=layer,
            w13=layer.w13_weight,
            w13_scale=layer.w13_weight_scale,
            w13_scale_2=w13_weight_scale_2,
            a13_scale=layer.w13_input_scale,
            w2=layer.w2_weight,
            w2_scale=layer.w2_weight_scale,
            w2_scale_2=layer.w2_weight_scale_2,
            a2_scale=layer.w2_input_scale,
            is_act_and_mul=self.moe.is_act_and_mul,
            use_a16=self.use_a16,
        )
        self.moe_quant_config = self.get_fused_moe_quant_config(layer)
        assert self.experts_cls is not None
        self.moe_kernel = make_nvfp4_moe_kernel(
            moe_quant_config=self.moe_quant_config,
            moe_config=self.moe,
            experts_cls=self.experts_cls,
            backend=self.nvfp4_backend,
            routing_tables=layer._expert_routing_tables(),
        )
        self.moe_kernel.fused_experts.process_weights_after_loading(layer)

    def another_method(self, layer):
        return helper(
            routing_tables=layer._expert_routing_tables(),
        )
"""
        with tempfile.TemporaryDirectory() as tmp:
            for mode, source in (("ct", ct_block), ("modelopt", mo_block)):
                target = Path(tmp) / f"{mode}.py"
                target.write_text(source, encoding="utf-8")
                result = subprocess.run(
                    ["python3", str(patch), str(target), mode],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                patched = target.read_text(encoding="utf-8")
                self.assertIn("QWEN38_H20_MOE_DIAG ", patched)
                self.assertIn(f'source="{mode}"', patched)
                self.assertIn('phase="pre"', patched)
                self.assertIn('phase="post"', patched)
                self.assertIn('phase="quant_config"', patched)
                self.assertIn('phase="kernel_created"', patched)
                self.assertIn('phase="fused_postload"', patched)
                self.assertIn("routing_tables=h20_routing_tables", patched)
                if mode == "modelopt":
                    self.assertIn(
                        "routing_tables=layer._expert_routing_tables()",
                        patched.split("def another_method", 1)[1],
                    )


    def test_h20c_runtime_trace_patcher_executes_on_internal_nvfp4_apply(self) -> None:
        trace_patch = ROOT / "scripts" / "patch-v029-h20c-runtime-moe-trace.py"
        fixtures = {
            "ct": """import torch
import json
import os
logger = init_logger(__name__)
def _qwen38_h20_fingerprint(tensor): return {"sha256": "x"}
class CompressedTensorsW4A4Nvfp4MoEMethod:
    def apply(
        self,
        layer: RoutedExperts,
        x: torch.Tensor,
        topk_weights: torch.Tensor,
        topk_ids: torch.Tensor,
        shared_experts: SharedExperts | None,
        shared_experts_input: torch.Tensor | None,
    ) -> torch.Tensor:
        assert self.moe_kernel is not None
        return self.moe_kernel.apply(
            x,
            layer.w13_weight,
            layer.w2_weight,
            topk_weights,
            topk_ids,
            activation=layer.activation,
            global_num_experts=layer.global_num_experts,
            expert_map=layer.expert_map,
            apply_router_weight_on_input=layer.apply_router_weight_on_input,
            shared_experts=shared_experts,
            shared_experts_input=shared_experts_input,
        )
QWEN38_H20_MOE_DIAG = "present"
""",
            "modelopt": """import torch
import json
import os
logger = init_logger(__name__)
def _qwen38_h20_fingerprint(tensor): return {"sha256": "x"}
class ModelOptNvFp4FusedMoE:
    def apply(
        self,
        layer: RoutedExperts,
        x: torch.Tensor,
        topk_weights: torch.Tensor,
        topk_ids: torch.Tensor,
        shared_experts: SharedExperts | None,
        shared_experts_input: torch.Tensor | None,
    ) -> torch.Tensor:
        assert not self.is_monolithic
        assert self.moe_kernel is not None
        return self.moe_kernel.apply(
            x,
            layer.w13_weight,
            layer.w2_weight,
            topk_weights,
            topk_ids,
            activation=layer.activation,
            global_num_experts=layer.global_num_experts,
            expert_map=layer.expert_map,
            apply_router_weight_on_input=layer.apply_router_weight_on_input,
            shared_experts=shared_experts,
            shared_experts_input=shared_experts_input,
        )
QWEN38_H20_MOE_DIAG = "present"

class AnotherModelOptMoE:
    def apply(
        self,
        layer: RoutedExperts,
        x: torch.Tensor,
        topk_weights: torch.Tensor,
        topk_ids: torch.Tensor,
        shared_experts: SharedExperts | None,
        shared_experts_input: torch.Tensor | None,
    ) -> torch.Tensor:
        assert not self.is_monolithic
        assert self.moe_kernel is not None
        return self.moe_kernel.apply(
            x,
            layer.w13_weight,
            layer.w2_weight,
            topk_weights,
            topk_ids,
            activation=layer.activation,
            global_num_experts=layer.global_num_experts,
            expert_map=layer.expert_map,
            apply_router_weight_on_input=layer.apply_router_weight_on_input,
            shared_experts=shared_experts,
            shared_experts_input=shared_experts_input,
        )
""",
        }
        with tempfile.TemporaryDirectory() as tmp:
            for source, fixture in fixtures.items():
                target = Path(tmp) / f"{source}.py"
                target.write_text(fixture, encoding="utf-8")
                result = subprocess.run(
                    ["python3", str(trace_patch), str(target), source],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                patched = target.read_text(encoding="utf-8")
                compile(patched, str(target), "exec")
                self.assertIn("QWEN38_H20C_RUNTIME ", patched)
                self.assertIn("QWEN38_H20D_TWIN ", patched)
                self.assertIn("QWEN38_H20D_SINGLE ", patched)
                self.assertIn("_qwen38_h20d_single_request_id", patched)
                self.assertIn("h20d_single_x_ref = x.clone()", patched)
                self.assertIn(f'_QWEN38_H20C_SOURCE = "{source}"', patched)
                self.assertIn("@torch.compiler.disable", patched)
                self.assertIn("_qwen38_h20c_enabled", patched)
                self.assertIn("_qwen38_h20d_request_id", patched)
                self.assertIn("h20d_x_ref = x.clone()", patched)
                self.assertIn("h20d_x_run2 = x.clone()", patched)
                self.assertIn("h20d_topk_weights_ref = topk_weights.clone()", patched)
                self.assertIn("h20d_topk_weights_run2 = topk_weights.clone()", patched)
                self.assertIn("h20d_output1 = output.clone()", patched)
                self.assertIn("h20d_output2 = self.moe_kernel.apply(", patched)
                self.assertIn("return h20d_output1", patched)
                self.assertIn("output = self.moe_kernel.apply(", patched)
                self.assertIn('"topk_weights": topk_weights', patched)
                self.assertIn('"topk_ids": topk_ids', patched)
                self.assertIn('tensors={"output": output}', patched)
                self.assertIn("return output", patched)
                if source == "modelopt":
                    other = patched.split("class AnotherModelOptMoE", 1)[1]
                    self.assertIn("return self.moe_kernel.apply(", other)
                    self.assertNotIn("QWEN38_H20C_RUNTIME ", other)

    def test_h20_upstream_patcher_executes_on_qwen4exp_layer(self) -> None:
        patch = ROOT / "scripts" / "patch-v029-h20-upstream-layer0.py"
        fixture = """from itertools import islice

import torch
from torch import nn

from .hyperconnection import GatedResidual, HyperConnectionConfig

class Qwen4ExpDecoderLayer(nn.Module):
    def forward(
        self,
        hidden_states: torch.Tensor,
        prev_block_output: torch.Tensor | None,
        prev_injection: torch.Tensor | None,
        positions: torch.Tensor,
        *,
        input_ids: torch.Tensor | None,
        query_start_loc: torch.Tensor | None,
        ngram_context: torch.Tensor | None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        attn_hc = self.attn_hyper_connection
        if self.ple is not None:
            pass

        # Fuse a pending combine with this HC module's mix when possible.
        if prev_block_output is not None and prev_injection is not None:
            hidden_states, block_input, injection = attn_hc.combine_and_mix(
                hidden_states, prev_block_output, prev_injection
            )
        else:
            hidden_states, block_input, injection = attn_hc.mix(hidden_states)

        if self.layer_type == "linear_attention":
            attn_out = self.linear_attn(hidden_states=block_input)
        elif self.layer_type == "full_attention":
            attn_out = self.self_attn(
                hidden_states=block_input,
                positions=positions,
            )
        else:
            raise ValueError("Invalid layer_type")

        mlp_hc = self.mlp_hyper_connection
        hidden_states, block_input, injection = mlp_hc.combine_and_mix(
            hidden_states, attn_out, injection
        )
        mlp_out = self.mlp(block_input)
        return hidden_states, mlp_out, injection

class AfterLayer:
    pass
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "model.py"
            target.write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(patch), str(target)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            patched = target.read_text(encoding="utf-8")
            compile(patched, str(target), "exec")
            self.assertIn("QWEN38_H20U_LAYER0 ", patched)
            self.assertIn("@torch.library.custom_op(", patched)
            self.assertIn('"qwen38_h20u::capture"', patched)
            self.assertIn('mutates_args={"tensor"}', patched)
            self.assertIn("_qwen38_h20u_capture(hidden_states, 0, self.layer_idx)", patched)
            self.assertIn("_qwen38_h20u_capture(block_input, 1, self.layer_idx)", patched)
            self.assertIn("_qwen38_h20u_capture(attn_out, 2, self.layer_idx)", patched)
            self.assertIn("_qwen38_h20u_capture(block_input, 3, self.layer_idx)", patched)
            self.assertIn("_qwen38_h20u_capture(mlp_out, 4, self.layer_idx)", patched)
            self.assertNotIn("\n@torch.compiler.disable\n", patched)
            self.assertIn('_QWEN38_H20U_CAPTURE_LAYER14 = os.environ.get(', patched)
            self.assertIn('(0, 1, 3, 7, 14, 15, 31, 47)', patched)
            self.assertIn('(0, 1, 3, 7, 15, 31, 47)', patched)
            self.assertIn('"layer_idx": layer_idx', patched)
            self.assertIn("_QWEN38_H20U_LAST_LAYER", patched)
            self.assertIn("_qwen38_h20u_emit_if_complete()", patched)
            self.assertIn('"missing_tensors": [name for name in names if name not in captured]', patched)
            self.assertIn('"prev_block_output"', patched)
            self.assertIn('"prev_injection"', patched)
            self.assertIn('"pre_attn_hc_hidden"', patched)
            self.assertIn('"post_attn_hc_hidden"', patched)
            self.assertIn('"attn_injection"', patched)
            self.assertIn('"post_mlp_hc_hidden"', patched)
            self.assertIn('"post_mlp_hc_injection"', patched)
            self.assertIn('"attention" in _QWEN38_H20U_LAYER14_GROUPS', patched)
            self.assertIn('"mlp_hc"', patched)
            self.assertIn('"mlp_block"', patched)
            self.assertIn("_QWEN38_H20U_LAYER14_MLP_HC", patched)
            self.assertIn("_QWEN38_H20U_LAYER14_MLP_BLOCK", patched)
            self.assertIn('"schema": 7', patched)
            self.assertIn('def _qwen38_h20u_rowwise_compare(', patched)
            self.assertIn('"changed_elements_by_row"', patched)
            self.assertIn('"first_mismatch_index"', patched)

    def test_h20_upstream_probe_summarizes_layer14_causally_and_keeps_legacy_layers(self) -> None:
        import contextlib
        import importlib.util
        import io
        import json
        import tempfile

        diagnostic = ROOT / "scripts" / "diagnostics" / "h20-nvfp4-moe.py"
        spec = importlib.util.spec_from_file_location("h20_nvfp4_moe", diagnostic)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        def fingerprint(value: str) -> dict[str, str]:
            return {"sha256": value}

        records = []
        layer14_names = (
            "entry_hidden",
            "prev_block_output",
            "prev_injection",
            "pre_attn_hc_hidden",
            "post_attn_hc_hidden",
            "attn_injection",
            "attn_block_input",
            "attn_out",
            "post_mlp_hc_hidden",
            "post_mlp_hc_injection",
            "mlp_block_input",
            "mlp_out",
        )
        layer15_names = (
            "entry_hidden",
            "prev_block_output",
            "prev_injection",
            "pre_attn_hc_hidden",
            "post_attn_hc_hidden",
            "attn_injection",
            "attn_block_input",
            "attn_out",
            "mlp_block_input",
            "mlp_out",
        )
        for layer in (14, 15):
            names = layer14_names if layer == 14 else layer15_names
            for request_id in (0, 1):
                tensors = {name: fingerprint(name) for name in names}
                if layer == 14 and request_id == 1:
                    tensors["mlp_out"] = fingerprint("changed")
                if layer == 15 and request_id == 1:
                    tensors["prev_block_output"] = fingerprint("changed")
                records.append(
                    {
                        "schema": 6,
                        "phase": "sparse-layer-upstream",
                        "layer_idx": layer,
                        "request_id": request_id,
                        "tensors": tensors,
                    }
                )
        for layer in (0, 1, 3, 7, 31, 47):
            for request_id in (0, 1):
                records.append(
                    {
                        "schema": 6,
                        "phase": "sparse-layer-upstream",
                        "layer_idx": layer,
                        "request_id": request_id,
                        "tensors": {name: fingerprint(name) for name in (
                            "entry_hidden", "attn_block_input", "attn_out",
                            "mlp_block_input", "mlp_out",
                        )},
                    }
                )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "probe.jsonl"
            module._container_exists = lambda _: True
            module._docker_exec = lambda *_: None

            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *_):
                    return False

                def read(self):
                    return b"{}"

            original_urlopen = module.urllib.request.urlopen
            original_run = module.subprocess.run
            module.urllib.request.urlopen = lambda *args, **kwargs: Response()
            module.subprocess.run = lambda *args, **kwargs: subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout="\n".join(
                    "QWEN38_H20U_LAYER0 " + json.dumps(record)
                    for record in records
                ),
                stderr="",
            )
            stream = io.StringIO()
            partial_stream = io.StringIO()
            try:
                with contextlib.redirect_stdout(stream):
                    result = module.upstream_probe(
                        container="container",
                        model="model",
                        output=output,
                        prompt="probe",
                        api_base="http://127.0.0.1:8888",
                    )
                records[:] = []
                for request_id in (0, 1):
                    tensors = {
                        name: fingerprint(name)
                        for name in (
                            "entry_hidden",
                            "prev_block_output",
                            "prev_injection",
                        )
                    }
                    if request_id == 1:
                        tensors["prev_block_output"] = fingerprint("changed")
                    records.append(
                        {
                            "schema": 6,
                            "phase": "sparse-layer-upstream",
                            "layer_idx": 14,
                            "request_id": request_id,
                            "tensors": tensors,
                        }
                    )
                with contextlib.redirect_stdout(partial_stream):
                    partial_result = module.upstream_probe(
                        container="container",
                        model="model",
                        output=output,
                        prompt="probe",
                        api_base="http://127.0.0.1:8888",
                    )
            finally:
                module.urllib.request.urlopen = original_urlopen
                module.subprocess.run = original_run

            self.assertEqual(result, 0)
            summary = stream.getvalue()
            self.assertIn(
                "upstream_repeat layer=14 all_equal=False "
                "first_mismatch=mlp_out",
                summary,
            )
            self.assertIn(
                "upstream_repeat layer=15 all_equal=False "
                "first_mismatch=prev_block_output",
                summary,
            )
            for layer in (0, 1, 3, 7, 31, 47):
                self.assertIn(
                    f"upstream_repeat layer={layer} all_equal=True",
                    summary,
                )
            self.assertEqual(partial_result, 0)
            self.assertIn(
                "upstream_repeat layer=14 all_equal=False "
                "first_mismatch=prev_block_output "
                "fields={'entry_hidden': True, 'prev_block_output': False, 'prev_injection': True}",
                partial_stream.getvalue(),
            )

    def test_h20_linear_attn_patcher_installs_boundaries(self) -> None:
        patch = ROOT / "scripts" / "patch-v029-h20-linear-attn-layer0.py"
        source = """import os
from typing import Literal
import torch
logger = init_logger(__name__)
class QwenGatedDeltaNetAttention(GatedDeltaNetAttention):
    def __init__(self, config, vllm_config, prefix=""):
        super().__init__(config, vllm_config, prefix)

        self.num_k_heads = config.linear_num_key_heads
        self.hidden_size = 4096
        self.key_dim = 1024
        self.value_dim = 1024
        self.quant_config = None
        self.in_proj_qkvz = self.create_qkvz_proj(
            hidden_size=self.hidden_size,
            key_dim=self.key_dim,
            value_dim=self.value_dim,
            quant_config=self.quant_config,
            prefix=f"{prefix}.in_proj_qkvz",
        )

    def forward_cuda(self, hidden_states: torch.Tensor) -> torch.Tensor:
        num_tokens = hidden_states.size(0)
        # ============================================================
        # Part 1: Input Projection
        # ============================================================
        mixed_qkvz, _ = self.in_proj_qkvz(hidden_states)
        ba, _ = self.in_proj_ba(hidden_states)

        use_fused_gdn_decode = (
            self.enable_fused_gdn_decode
            and hidden_states.dtype == torch.bfloat16
            and self.norm.weight.dtype in (torch.bfloat16, torch.float32)
        )
        if use_fused_gdn_decode:
            core_attn_out = torch.zeros((num_tokens, 1, 128))
            torch.ops.vllm.qwen_gdn_attention_core_fused_norm_packed(
                mixed_qkvz,
                ba,
                core_attn_out,
                layer_name=_encode_layer_name(self.prefix),
            )
            output, _ = self.out_proj(core_attn_out.flatten(-2))
            return output

        if self.gqa_interleaved_layout:
            query, key, value, z, b, a = self.fix_query_key_value_ordering(
                mixed_qkvz, ba
            )
            mixed_qkv = torch.cat((query, key, value), dim=-1)
        else:
            qkv_size = (self.key_dim * 2 + self.value_dim) // self.tp_size
            z_size = self.value_dim // self.tp_size
            mixed_qkv, z = mixed_qkvz.split([qkv_size, z_size], dim=-1)
            z = z.reshape(z.size(0), -1, self.head_v_dim)
            b, a = self.split_ba(ba)

        # ============================================================
        # Part 2: Core Attention (Custom Op)
        # ============================================================
        core_attn_out = torch.zeros((num_tokens, 1, 128))
        torch.ops.vllm.qwen_gdn_attention_core(
            mixed_qkv,
            b.contiguous(),
            a.contiguous(),
            core_attn_out,
            layer_name=_encode_layer_name(self.prefix),
        )

        # ============================================================
        # Part 3: Output Projection
        # ============================================================
        return self._output_projection(core_attn_out, z)
"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "qwen_gdn_linear_attn.py"
            target.write_text(source, encoding="utf-8")
            result = subprocess.run(
                ["python3", str(patch), str(target)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            patched = target.read_text(encoding="utf-8")
            compile(patched, str(target), "exec")
            self.assertIn("QWEN38_H20L_LINEAR ", patched)
            self.assertIn('"qwen38_h20l::capture"', patched)
            self.assertIn("mixed_qkvz, 1, self._qwen38_h20_layer_idx", patched)
            self.assertIn("_qwen38_h20l_capture(ba, 2, self._qwen38_h20_layer_idx)", patched)
            self.assertIn("core_attn_out, 7, self._qwen38_h20_layer_idx", patched)
            self.assertIn("output, 8, self._qwen38_h20_layer_idx", patched)
            self.assertIn("QWEN38_H20P_QKVZ ", patched)
            self.assertIn('"qwen38_h20p::qkvz_twin"', patched)
            self.assertIn("_QWEN38_H20P_QKVZ_PROJ = self.in_proj_qkvz", patched)
            self.assertIn("_qwen38_h20p_qkvz_twin(", patched)
            self.assertIn("QWEN38_H20P_META layer=0", patched)
            self.assertIn("QWEN38_H20P_BACKEND layer=0", patched)
            self.assertIn('"compiled_vs_natural_equal"', patched)
            self.assertIn('"zeroed_repeat_equal"', patched)
            self.assertIn('"natural_vs_zeroed_equal"', patched)
            self.assertIn('"lock_pre"', patched)
            self.assertIn("locks.zero_()", patched)

    def test_h20_v15_ct_image_localizes_batch_invariant_to_fp8(self) -> None:
        dockerfile = (
            ROOT / "scripts" / "Dockerfile.v029-h20-ct-convert-diag"
        ).read_text(encoding="utf-8")
        patch = (
            ROOT / "scripts" / "patch-v029-h20-humming-fp8-batch-invariant.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("ENV VLLM_BATCH_INVARIANT=1", dockerfile)
        self.assertIn("patch-v029-h20-humming-fp8-batch-invariant.py", dockerfile)
        self.assertIn("QWEN38_H20Q_FP8_BATCH_INVARIANT", dockerfile)
        self.assertIn('LABEL qwen38.h20="ct-nvfp4-convert-diag-v21"', dockerfile)
        self.assertIn('class HummingFP8ScaledMMLinearKernel', patch)
        self.assertIn('_qwen38_h20_compute["use_batch_invariant"] = True', patch)
        self.assertIn('class HummingInt8ScaledMMLinearKernel', patch)

    def test_h20_v13_dockerfiles_drop_v12_qkvz_key(self) -> None:
        for name in (
            "Dockerfile.v029-h20-ct-convert-diag",
            "Dockerfile.v029-h20-modelopt-convert-diag",
        ):
            dockerfile = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn('"zeroed_repeat_equal"', dockerfile)
            self.assertIn('"natural_vs_zeroed_equal"', dockerfile)
            self.assertNotIn('"compiled_vs_eager_equal"', dockerfile)

    def test_h20_upstream_dockerfiles_smoke_fullgraph_custom_op(self) -> None:
        for name in (
            "Dockerfile.v029-h20-ct-convert-diag",
            "Dockerfile.v029-h20-modelopt-convert-diag",
        ):
            dockerfile = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("h20u_fullgraph_smoke", dockerfile)
            self.assertIn("torch.compile(fullgraph=True, backend=\"eager\")", dockerfile)
            self.assertIn("_qwen38_h20u_capture", dockerfile)

    def test_h20c_cli_supports_triggered_trace_and_runtime_compare(self) -> None:
        script = (
            ROOT / "scripts" / "diagnostics" / "h20-nvfp4-moe.py"
        ).read_text(encoding="utf-8")
        self.assertIn('sub.add_parser("trace")', script)
        self.assertIn('sub.add_parser("runtime-compare")', script)
        self.assertIn("/tmp/qwen38_h20c_trace.enable", script)
        self.assertIn("/tmp/qwen38_h20c_request_id", script)
        self.assertIn('"max_tokens": 1', script)
        self.assertIn("ct_repeat_stability", script)
        self.assertIn("modelopt_repeat_stability", script)
        self.assertIn("_container_exists", script)
        self.assertIn("H20-C container not found", script)
        self.assertIn('sub.add_parser("single-probe")', script)
        self.assertIn('sub.add_parser("single-compare")', script)
        self.assertIn("/tmp/qwen38_h20d_single.enable", script)
        self.assertIn("QWEN38_H20D_SINGLE ", script)
        self.assertIn('sub.add_parser("twin-probe")', script)
        self.assertIn('sub.add_parser("twin-compare")', script)
        self.assertIn("/tmp/qwen38_h20d_twin.enable", script)
        self.assertIn("QWEN38_H20D_TWIN ", script)
        self.assertIn("output1_equal", script)
        self.assertIn("input_equal", script)
        self.assertIn("shared_experts_input", script)
        self.assertIn("input {name}", script)
        self.assertIn('sub.add_parser("upstream-probe")', script)
        self.assertIn("upstream_repeat layer=", script)
        self.assertIn('record.get("layer_idx", 0)', script)
        self.assertIn('sub.add_parser("upstream-compare")', script)
        self.assertIn("/tmp/qwen38_h20u_layer0.enable", script)
        self.assertIn("QWEN38_H20U_LAYER0 ", script)
        self.assertIn("entry_hidden", script)
        self.assertIn("attn_block_input", script)
        self.assertIn("mlp_block_input", script)
        self.assertIn("prev_block_output", script)
        self.assertIn("prev_injection", script)
        self.assertIn("pre_attn_hc_hidden", script)
        self.assertIn("post_attn_hc_hidden", script)
        self.assertIn("attn_injection", script)
        self.assertIn("post_mlp_hc_hidden", script)
        self.assertIn("post_mlp_hc_injection", script)
        self.assertIn('"entry_hidden",\n        "prev_block_output",', script)
        self.assertIn('"prev_injection",\n        "pre_attn_hc_hidden",', script)
        self.assertIn('"attn_injection",\n        "attn_block_input",', script)
        self.assertIn('sub.add_parser("linear-probe")', script)
        self.assertIn('sub.add_parser("linear-compare")', script)
        self.assertIn("/tmp/qwen38_h20l_linear.enable", script)
        self.assertIn("QWEN38_H20L_LINEAR ", script)
        self.assertIn("mixed_qkvz", script)
        self.assertIn("core_attn_out", script)
        self.assertIn('sub.add_parser("qkvz-twin-probe")', script)
        self.assertIn("/tmp/qwen38_h20p_qkvz_twin.enable", script)
        self.assertIn("QWEN38_H20P_QKVZ ", script)
        self.assertIn("qkvz_repeat", script)
        self.assertIn("compiled_vs_natural_equal", script)
        self.assertIn("natural_vs_zeroed_equal", script)
        self.assertIn("zeroed_repeat_equal", script)
        self.assertIn("qkvz_locks", script)
        self.assertIn("zeroed_eager1_equal", script)


if __name__ == "__main__":
    unittest.main()
