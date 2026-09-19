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
            "STOCK          stock Qwen3.8 vLLM image + MTP k=2",
            "STOCK-NOSPEC   stock Qwen3.8 vLLM image + no speculative decoding",
            "SKINNY         skinny-GEMM image + MTP k=2",
            "SKINNY-NOSPEC  skinny-GEMM image + no speculative decoding",
            "SKINNY-DET     skinny-GEMM image + deterministic QSA top-k + MTP k=2",
            "MODEL_PROFILE=orcarouter",
            "NSPEC=2",
            "MAXLEN=262144",
            "KV_MEM=25769803776",
            "MAXSEQS=3",
            "PREFIX_CACHE=0",
            "INDEX_SHARE=0",
            "AUTOTUNE=0",
            "SPEC=mtp except *-NOSPEC cases",
            "QSA_DET_TOPK=1 only for SKINNY-DET",
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

    def test_skinny_det_changes_only_image_and_qsa_kernel_toggle(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('SKINNY-DET)', script)
        self.assertIn('IMAGE="${SKINNY_DET_IMAGE}"', script)
        self.assertIn('SPEC_VALUE=mtp', script)
        self.assertIn('QSA_DET_VALUE=1', script)
        self.assertIn('QSA_DET_TOPK="${QSA_DET_VALUE}"', script)
        self.assertIn('vllm-skinny-qsa-det:v1', script)

    def test_nospec_cases_disable_speculation_without_changing_image(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('STOCK-NOSPEC)', script)
        self.assertIn('SKINNY-NOSPEC)', script)
        self.assertIn('SPEC_VALUE=none', script)
        self.assertIn('SPEC="${SPEC_VALUE}"', script)

    def test_deterministic_qsa_image_is_pinned_and_opt_in(self) -> None:
        dockerfile = (ROOT / "scripts" / "Dockerfile.qsa-det").read_text(encoding="utf-8")
        serve = (ROOT / "scripts" / "serve.sh").read_text(encoding="utf-8")
        self.assertIn("e0ef69d4f5575dad00d34e05479eaf4c6547bace", dockerfile)
        self.assertIn("ADD --checksum=sha256:", dockerfile)
        self.assertIn("VLLM_QSA_DET_TOPK", dockerfile)
        self.assertIn('QSA_DET_TOPK="${QSA_DET_TOPK:-0}"', serve)
        self.assertIn("VLLM_QSA_DET_LIB=/opt/qwen38/kernel-det/_C_det.so", serve)

    def test_invalid_case_is_rejected(self) -> None:
        result = subprocess.run(
            ["bash", str(SCRIPT), "start", "INVALID"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("case must be STOCK, STOCK-NOSPEC, SKINNY, SKINNY-NOSPEC, or SKINNY-DET", result.stderr)


if __name__ == "__main__":
    unittest.main()
