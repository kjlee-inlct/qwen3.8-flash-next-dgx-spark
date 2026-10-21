"""OrcaRouter Wizard: installed manifest vs registry vs live runtime (synthetic only)."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OrcaRouterInstalledBackendWizardTests(unittest.TestCase):
    @staticmethod
    def write_manifest(home: Path, image: str) -> Path:
        state = home / "state" / "qwen38-spark"
        state.mkdir(parents=True, exist_ok=True)
        path = state / "install.env"
        path.write_text("\n".join([
            "SCHEMA_VERSION=4",
            "PHASE=complete",
            f"INSTALL_ROOT={ROOT}",
            "MODEL_PROFILE=orcarouter",
            "MODEL_REPO=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
            "MODEL_REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306",
            f"MODEL_DIR={home / 'models/qwen3.8-flash-next-orcarouter'}",
            "MODEL_OWNED=0",
            "SWAP_FILE=/swap-ple.img",
            "SWAP_OWNED=0",
            f"VLLM_IMAGE={image}",
            "IMAGE_OWNED=0",
            "SERVED_NAME=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
            "CONTAINER_NAME=qwen38-flash-next",
            "CONFIG_OVERRIDE=",
            "CONFIG_OWNED=0",
            "MONITOR_PROTECT=0",
            "MONITOR_ENABLED=0",
            "MONITOR_MIN_AVAILABLE_GIB=6",
            "MONITOR_MIN_FREE_GIB=2",
            "MONITOR_FREE_GATE_GIB=10",
            "MONITOR_MIN_SWAP_FREE_GIB=8",
            "MONITOR_CONSECUTIVE=5",
            "MONITOR_HEARTBEAT=60",
            "API_ACCESS_MODE=local",
            "API_DOCKER_PORT=8000",
            "API_LAN_ADDRESS=",
            "API_LAN_PORT=8001",
            "PROXY_ENABLED=0",
            "PROXY_OWNED=0",
            "PROXY_PORT=8000",
            "SERVICE_ENABLED=1",
            "SERVICE_OWNED=1",
            "SERVICE_UNIT=qwen38-flash-next.service",
            "UI_LANG=ko",
            "",
        ]), encoding="utf-8")
        return path

    @staticmethod
    def run_wizard(home: Path) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "HOME": str(home),
               "XDG_STATE_HOME": str(home / "state")}
        env.pop("MODEL_PROFILE", None)
        return subprocess.run(
            ["bash", str(ROOT / "wizard.sh"), "--lang", "ko"],
            cwd=ROOT, env=env, input="3\n7\n5\n0\n0\n0\n",
            capture_output=True, text=True, check=False, timeout=30,
        )

    def test_legacy_installed_image_does_not_display_registry_v029_as_installed(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            manifest = self.write_manifest(home, "vllm-skinny-tp1:v1")
            initial = manifest.read_bytes()
            result = self.run_wizard(home)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Manifest: valid (phase=complete)", result.stdout)
            self.assertIn("ORCAROUTER_MANIFEST_STATE=valid", result.stdout)
            self.assertIn("ORCAROUTER_CONFIGURED_PROFILE=orcarouter", result.stdout)
            self.assertIn("ORCAROUTER_CONFIGURED_IMAGE=vllm-skinny-tp1:v1", result.stdout)
            self.assertIn("ORCAROUTER_CONFIGURED_VARIANT=LEGACY_SKINNY_MANIFEST_IMAGE", result.stdout)
            self.assertIn("Registry default candidate", result.stdout)
            self.assertIn("ORCAROUTER_LIVE_RUNTIME=NOT_PROBED", result.stdout)
            self.assertIn("ORCAROUTER_OFFICIAL_ARM64_C_INSTALL_SWITCH=DISABLED_UNQUALIFIED", result.stdout)
            self.assertIn("WIZARD_MUTATION=NONE", result.stdout)
            self.assertEqual(manifest.read_bytes(), initial)
            self.assertFalse((home / "state/qwen38-spark/operation.lock").exists())

    def test_v029_configured_manifest_is_not_runtime_ready_proof(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            manifest = self.write_manifest(home, "vllm-orcarouter-v029:v1")
            result = self.run_wizard(home)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ORCAROUTER_CONFIGURED_IMAGE=vllm-orcarouter-v029:v1", result.stdout)
            self.assertIn("ORCAROUTER_CONFIGURED_VARIANT=V029_MANIFEST_IMAGE", result.stdout)
            self.assertIn("ORCAROUTER_LIVE_RUNTIME=NOT_PROBED", result.stdout)
            self.assertIn("WIZARD_MUTATION=NONE", result.stdout)
            self.assertTrue(manifest.is_file())

    def test_custom_manifest_image_is_not_assumed_to_be_v029_or_legacy(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            self.write_manifest(home, "custom-runtime-image:unverified")
            result = self.run_wizard(home)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ORCAROUTER_CONFIGURED_VARIANT=OTHER_IMAGE_NOT_CLASSIFIED", result.stdout)
            self.assertIn("ORCAROUTER_CONFIGURED_IMAGE=custom-runtime-image:unverified", result.stdout)
            self.assertIn("ORCAROUTER_LIVE_RUNTIME=NOT_PROBED", result.stdout)

    def test_symlink_manifest_remains_invalid_and_never_source_executed(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            state = home / "state" / "qwen38-spark"
            state.mkdir(parents=True)
            target = home / "dangerous.txt"
            target.write_text('VLLM_IMAGE=$(touch /tmp/not-allowed)\n', encoding="utf-8")
            (state / "install.env").symlink_to(target)
            result = self.run_wizard(home)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ORCAROUTER_MANIFEST_STATE=invalid", result.stdout)
            self.assertIn("ORCAROUTER_CONFIGURED_IMAGE=NOT_AVAILABLE", result.stdout)
            self.assertIn("ORCAROUTER_CONFIGURED_VARIANT=UNKNOWN", result.stdout)
            self.assertNotIn("ORCAROUTER_CONFIGURED_IMAGE=vllm-orcarouter-v029:v1", result.stdout)
            self.assertIn("WIZARD_MUTATION=NONE", result.stdout)

    def test_missing_manifest_does_not_claim_installed_image(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            result = self.run_wizard(home)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ORCAROUTER_MANIFEST_STATE=missing", result.stdout)
            self.assertIn("ORCAROUTER_CONFIGURED_IMAGE=NOT_AVAILABLE", result.stdout)
            self.assertIn("ORCAROUTER_LIVE_RUNTIME=NOT_PROBED", result.stdout)
            self.assertFalse((home / "state").exists())


if __name__ == "__main__":
    unittest.main()
