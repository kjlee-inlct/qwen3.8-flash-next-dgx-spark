from __future__ import annotations

import subprocess
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
        self.assertIn("ct-nvfp4-convert-diag-v2", ct)
        self.assertIn("FROM vllm-orcarouter-v029:v1", mo)
        self.assertIn(" modelopt", mo)
        self.assertIn("modelopt-nvfp4-convert-diag-v2", mo)
        self.assertIn("hybrid-h20-ct-convert-diag", runtime)
        self.assertIn("hybrid-h20-modelopt-convert-diag", runtime)
        self.assertIn("QWEN38_H20_DIAG_MAX_CALLS=4", runtime)
        self.assertIn("QWEN38_H20_DIAG_SAMPLE_ELEMS=1024", runtime)
        self.assertIn("h20_image_ok()", runtime)


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


if __name__ == "__main__":
    unittest.main()
