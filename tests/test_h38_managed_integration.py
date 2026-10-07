from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class H38ManagedIntegrationTests(unittest.TestCase):
    def test_orcarouter_registry_selects_h38_decoder_image(self) -> None:
        text = (ROOT / "scripts" / "model" / "model-profiles.sh").read_text(encoding="utf-8")
        start = text.index("    orcarouter)\n", text.index("load_download_profile()"))
        end = text.index("    nvidia)\n", start)
        block = text[start:end]
        self.assertIn('PROFILE_IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"', block)

    def test_managed_orcarouter_uses_qualified_h38_runtime_controls(self) -> None:
        text = (ROOT / "scripts" / "serve.sh").read_text(encoding="utf-8")
        start = text.index("  orcarouter)\n")
        end = text.index("  nvidia)\n", start)
        block = text[start:end]
        self.assertIn("vllm-orcarouter-v029-h38-decoder-scope:v1", block)
        self.assertIn("DEFAULT_QSA_EXACT_TOPK=1", block)
        self.assertIn("PLE_MODE=mmap", block)
        self.assertIn("KV_MEMORY_FLAG=--kv-cache-memory-bytes", block)
        self.assertIn("DEFAULT_KV_MEM=17179869184", block)
        self.assertNotIn("DEFAULT_KV_MEM=25769803776", block)
        self.assertIn("QWEN38_MARLIN_CANONICAL_ORDER=1", block)
        self.assertIn("QWEN38_MARLIN_CANONICAL_SCOPE=decoder", block)
        self.assertIn("h38-marlin-canonical-decoder-managed-v1", block)
        self.assertIn('"${RUNTIME_ENV[@]}"', text)

    def test_clean_host_builder_contains_complete_h38_parent_chain(self) -> None:
        text = (ROOT / "scripts" / "runtime" / "prepare-h38-image.sh").read_text(
            encoding="utf-8"
        )
        chain = [
            "vllm-orcarouter-v029:v1",
            "vllm-orcarouter-v029-h9-ct-modelweight:v1",
            "vllm-orcarouter-v029-h10-ct-global-scale:v1",
            "vllm-orcarouter-v029-h11-ct-packed-modelweight:v1",
            "vllm-orcarouter-v029-h12-ct-postload-preserve:v1",
        ]
        positions = [text.index(f'build_stage "{image}"') for image in chain]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('build_stage "${TARGET_IMAGE}" "Dockerfile.v029-h38-decoder-scope"', text)
        self.assertIn('EXPECTED_SCOPE="decoder-v1"', text)
        self.assertIn("qwen38.h38scope", text)

    def test_installer_uses_h38_builder_instead_of_pulling_local_image(self) -> None:
        text = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn(
            'if [[ "${MODEL_PROFILE}" == orcarouter && "${IMAGE}" == vllm-orcarouter-v029-h38-decoder-scope:v1 ]]',
            text,
        )
        self.assertIn('bash "${ROOT_DIR}/scripts/runtime/prepare-h38-image.sh" build', text)

    def test_preflight_and_doctor_fail_closed_on_h38_scope_drift(self) -> None:
        preflight = (ROOT / "scripts" / "runtime" / "preflight-runtime.sh").read_text(
            encoding="utf-8"
        )
        doctor = (ROOT / "scripts" / "doctor.sh").read_text(encoding="utf-8")
        for text in (preflight, doctor):
            self.assertIn("qwen38.h38scope", text)
            self.assertIn("decoder-v1", text)
        self.assertIn("managed OrcaRouter runtime image drift", preflight)
        self.assertIn("H38 decoder-scope image label", doctor)
        self.assertIn("QWEN38_MARLIN_CANONICAL_ORDER=1", doctor)
        self.assertIn("QWEN38_MARLIN_CANONICAL_SCOPE=decoder", doctor)

    def test_production_gate_can_target_managed_served_alias(self) -> None:
        text = (ROOT / "scripts" / "benchmark" / "run-h38-production-gate.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("H38_GATE_MODEL", text)
        self.assertIn("H38_GATE_OUT", text)

    def test_legacy_orcarouter_image_remains_bootable_until_explicit_refresh(self) -> None:
        serve = (ROOT / "scripts" / "serve.sh").read_text(encoding="utf-8")
        preflight = (ROOT / "scripts" / "runtime" / "preflight-runtime.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('if [[ "${IMAGE}" == vllm-orcarouter-v029-h38-decoder-scope:v1 ]]', serve)
        self.assertIn('LEGACY_IMAGE="vllm-skinny-tp1:v1"', preflight)
        self.assertIn("pending explicit --refresh-profile-defaults migration", preflight)

    def test_installer_tracks_h38_parent_image_ownership(self) -> None:
        text = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("asset_track_h38_image_chain()", text)
        for image in (
            "vllm-orcarouter-v029:v1",
            "vllm-orcarouter-v029-h9-ct-modelweight:v1",
            "vllm-orcarouter-v029-h10-ct-global-scale:v1",
            "vllm-orcarouter-v029-h11-ct-packed-modelweight:v1",
            "vllm-orcarouter-v029-h12-ct-postload-preserve:v1",
            "vllm-orcarouter-v029-h38-decoder-scope:v1",
        ):
            self.assertIn(image, text)
        self.assertGreaterEqual(text.count("asset_track_h38_image_chain"), 3)

    def test_operator_asset_registry_tracks_promoted_orcarouter_image(self) -> None:
        text = (ROOT / "scripts" / "model-assets.sh").read_text(encoding="utf-8")
        start = text.index("    orcarouter)\n")
        end = text.index("    mazinb)\n", start)
        block = text[start:end]
        self.assertIn(
            'MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"',
            block,
        )
        self.assertIn(
            'MODEL_ASSET_IMAGE_DEPENDS_ON="hybrid-h12-ct-postload-preserve"',
            block,
        )


if __name__ == "__main__":
    unittest.main()
