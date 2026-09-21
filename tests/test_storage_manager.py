from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "manage-storage.sh"
MODEL_MANAGER = ROOT / "scripts" / "manage-models.sh"


class StorageManagerTests(unittest.TestCase):
    def test_help_documents_safe_boundaries(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for text in (
            "active MODEL_DIR",
            "active manifest VLLM_IMAGE",
            "current or previous immutable releases",
            "PLE swap",
            "Hugging Face cache",
            "manage-models.sh",
        ):
            self.assertIn(text, result.stdout)

    def test_script_uses_strict_manifest_parser(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('install-maintenance "${STATE_FILE}"', script)
        self.assertIn('ACTIVE_MODEL="${value}"', script)
        self.assertIn('ACTIVE_IMAGE="${value}"', script)

    def test_default_prune_does_not_delete_models_swap_or_hf_cache(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('rm -rf --one-file-system -- "${ACTIVE_MODEL}"', script)
        self.assertNotIn("swapoff", script)
        self.assertNotIn('rm -rf -- "${HF_CACHE}"', script)
        self.assertIn("HF cache were preserved", script)

    def test_current_and_previous_releases_are_excluded(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(
            '[[ "${id}" == "${current_release}" || "${id}" == "${previous_release}" ]] && continue',
            script,
        )
        self.assertIn('bash "${RELEASE_MANAGER}" discard "${id}"', script)

    def test_experiment_image_cleanup_is_opt_in_and_active_image_is_protected(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("PRUNE_EXPERIMENTS=0", script)
        self.assertIn("vllm-skinny-qsa-det:v1", script)
        self.assertIn("vllm-skinny-qsa-exact:v1", script)
        self.assertIn('if [[ "${image}" == "${ACTIVE_IMAGE}" ]]', script)
        self.assertIn("PROTECTED active image", script)

    def test_storage_asset_registry_classifies_images(self) -> None:
        assets = (ROOT / "scripts" / "storage" / "assets.sh").read_text(encoding="utf-8")
        self.assertIn('STORAGE_IMAGE_CLASS="stable"', assets)
        self.assertIn('STORAGE_IMAGE_CLASS="baseline"', assets)
        self.assertIn('STORAGE_IMAGE_CLASS="optional"', assets)
        self.assertIn('STORAGE_IMAGE_CLASS="experiment"', assets)
        self.assertIn("vllm-skinny-tp1:v1", assets)
        self.assertIn("vllm-skinny-qsa-det:v1", assets)
        self.assertIn("vllm-skinny-qsa-exact:v1", assets)
        self.assertIn("vllm-skinny-stable-candidate:v1", assets)
        self.assertIn("vllm-orcarouter-v029:v1", assets)

    def test_manager_uses_disposable_registry_instead_of_hardcoded_function(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('source "${STORAGE_ASSETS}"', script)
        self.assertIn("list_disposable_storage_images", script)
        self.assertNotIn("experiment_images()", script)
        self.assertIn("logical sizes", script)

    def test_recommend_action_delegates_to_read_only_helper(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        helper = (ROOT / "scripts" / "storage" / "recommend.sh").read_text(encoding="utf-8")
        self.assertIn("recommend", script)
        self.assertIn('bash "${SCRIPT_ROOT}/scripts/storage/recommend.sh"', script)
        self.assertIn("[1. Inactive managed checkpoints]", helper)
        self.assertIn("[2. Docker reclaimable]", helper)
        self.assertIn("[3. Hugging Face cache - report only]", helper)
        self.assertIn("manage-models.sh remove", helper)
        self.assertNotIn("rm -rf", helper)
        self.assertNotIn("docker image rm", helper)

    def test_mutating_prune_checks_transition_state_and_operation_lock(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("runtime transition is active", script)
        self.assertIn("update transition is active", script)
        self.assertIn('acquire_operation_lock "${STATE_DIR}" "storage prune"', script)

    def test_build_cache_and_benchmark_retention_are_bounded(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("BUILD_CACHE_DAYS=7", script)
        self.assertIn("BENCHMARK_DAYS=30", script)
        self.assertIn('docker builder prune -f --filter "until=${hours}h"', script)
        self.assertIn('-mtime "+${BENCHMARK_DAYS}"', script)

    def test_model_manager_discovers_and_removes_hybrid_manifests(self) -> None:
        script = MODEL_MANAGER.read_text(encoding="utf-8")
        self.assertIn(".qwen38-hybrid-manifest.json", script)
        self.assertIn("hybrid:", script)
        self.assertIn("model/hybrid manifest missing", script)

    def test_model_manager_protects_running_container_mounts(self) -> None:
        script = MODEL_MANAGER.read_text(encoding="utf-8")
        self.assertIn("mounted_by_running_container()", script)
        self.assertIn("docker inspect --format", script)
        self.assertIn("checkpoint is mounted by a running Docker container", script)

    def test_storage_recommend_discovers_hybrid_manifests(self) -> None:
        source = (ROOT / "scripts" / "storage" / "recommend.sh").read_text(encoding="utf-8")
        self.assertIn(".qwen38-hybrid-manifest.json", source)
        self.assertIn(".qwen38-model-manifest.json", source)


if __name__ == "__main__":
    unittest.main()
