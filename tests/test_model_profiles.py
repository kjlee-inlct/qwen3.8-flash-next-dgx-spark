from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class ModelProfileTests(unittest.TestCase):
    def run_install(self, profile: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            return subprocess.run(
                [str(ROOT / "install.sh"), "--model", profile, "--lang", "en", "--yes", "--no-start", "--dry-run"],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
                text=True,
                capture_output=True,
                check=False,
            )

    def test_model_registry_marks_orcarouter_as_only_stable_default(self) -> None:
        result = subprocess.run(
            [str(ROOT / "install.sh"), "--list-models"],
            cwd=ROOT,
            env=os.environ,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("orcarouter   stable", result.stdout)
        self.assertIn("nvidia       experimental", result.stdout)
        self.assertIn("mazinb       candidate", result.stdout)
        self.assertIn("lychee888    candidate", result.stdout)

    def test_candidate_profiles_are_not_installable(self) -> None:
        for profile in ("mazinb", "lychee888"):
            with self.subTest(profile=profile):
                result = self.run_install(profile)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("is a candidate profile and is not installable yet", result.stderr)

    def test_backend_registry_keeps_vllm_stable_and_sglang_planned(self) -> None:
        result = subprocess.run(
            [str(ROOT / "install.sh"), "--list-backends"],
            cwd=ROOT,
            env=os.environ,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("vllm", result.stdout)
        self.assertIn("stable", result.stdout)
        self.assertIn("sglang", result.stdout)
        self.assertIn("planned", result.stdout)

    def test_orcarouter_profile(self) -> None:
        result = self.run_install("orcarouter")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4", result.stdout)
        self.assertIn("profile     : orcarouter", result.stdout)
        self.assertIn("vllm-skinny-tp1:v1", result.stdout)

    def test_nvidia_profile(self) -> None:
        result = self.run_install("nvidia")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nvidia/Qwen3.8-Flash-Next-NVFP4", result.stdout)
        self.assertIn("fc694b54fb0174e0913e6adf86691ef85a4ead47", result.stdout)
        self.assertIn("profile     : nvidia", result.stdout)

    def test_unknown_profile_fails(self) -> None:
        result = self.run_install("unknown")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown model profile", result.stderr)

    def test_dry_run_can_preview_another_installed_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "state" / "qwen38-spark"
            state.mkdir(parents=True)
            (state / "install.env").write_text(
                "\n".join([
                    "SCHEMA_VERSION=2",
                    "PHASE=complete",
                    f"INSTALL_ROOT={ROOT}",
                    "MODEL_PROFILE=orcarouter",
                    "MODEL_REPO=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "MODEL_REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306",
                    f"MODEL_DIR={home / 'model'}",
                    "MODEL_OWNED=0",
                    "SWAP_FILE=/swap-ple.img",
                    "SWAP_OWNED=0",
                    "VLLM_IMAGE=test-image",
                    "IMAGE_OWNED=0",
                    "CONTAINER_NAME=qwen38-flash-next",
                    "CONFIG_OVERRIDE=",
                    "CONFIG_OWNED=0",
                    "MONITOR_PROTECT=0",
                    "PROXY_ENABLED=0",
                    "PROXY_OWNED=0",
                    "PROXY_PORT=8000",
                    "SERVICE_ENABLED=1",
                    "SERVICE_OWNED=1",
                    "UI_LANG=en",
                    "",
                ]),
                encoding="utf-8",
            )
            result = subprocess.run(
                [str(ROOT / "install.sh"), "--model", "nvidia", "--lang", "en", "--yes", "--no-start", "--dry-run"],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("profile     : nvidia", result.stdout)
            self.assertNotIn("Resuming installation", result.stdout)

    def test_refresh_profile_defaults_previews_new_orcarouter_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "state" / "qwen38-spark"
            state.mkdir(parents=True)
            (state / "install.env").write_text(
                "\n".join([
                    "SCHEMA_VERSION=4",
                    "PHASE=complete",
                    f"INSTALL_ROOT={ROOT}",
                    "MODEL_PROFILE=orcarouter",
                    "MODEL_REPO=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "MODEL_REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306",
                    f"MODEL_DIR={home / 'model'}",
                    "MODEL_OWNED=0",
                    "SWAP_FILE=/swap-ple.img",
                    "SWAP_OWNED=0",
                    "VLLM_IMAGE=vllm/vllm-openai:qwen38-flash-next-arm64-cu130",
                    "IMAGE_OWNED=0",
                    "SERVED_NAME=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "CONTAINER_NAME=qwen38-flash-next",
                    f"CONFIG_OVERRIDE={home / 'config.vllm.json'}",
                    "CONFIG_OWNED=1",
                    "MONITOR_PROTECT=0",
                    "MONITOR_ENABLED=0",
                    "MONITOR_MIN_AVAILABLE_GIB=6",
                    "MONITOR_MIN_FREE_GIB=2",
                    "MONITOR_FREE_GATE_GIB=10",
                    "MONITOR_MIN_SWAP_FREE_GIB=8",
                    "MONITOR_CONSECUTIVE=5",
                    "MONITOR_HEARTBEAT=60",
                    "API_ACCESS_MODE=docker",
                    "API_DOCKER_PORT=8000",
                    "API_LAN_ADDRESS=",
                    "API_LAN_PORT=8001",
                    "PROXY_ENABLED=1",
                    "PROXY_OWNED=1",
                    "PROXY_PORT=8000",
                    "SERVICE_ENABLED=1",
                    "SERVICE_OWNED=1",
                    "SERVICE_UNIT=qwen38-flash-next.service",
                    "UI_LANG=en",
                    "",
                ]),
                encoding="utf-8",
            )
            (home / "config.vllm.json").write_text("{}", encoding="utf-8")
            before = (state / "install.env").read_bytes()
            result = subprocess.run(
                [
                    str(ROOT / "install.sh"),
                    "--model", "orcarouter",
                    "--lang", "en",
                    "--yes",
                    "--no-start",
                    "--refresh-profile-defaults",
                    "--dry-run",
                ],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("vllm-skinny-tp1:v1", result.stdout)
            self.assertIn(
                "image change: vllm/vllm-openai:qwen38-flash-next-arm64-cu130 -> vllm-skinny-tp1:v1",
                result.stdout,
            )
            self.assertEqual((state / "install.env").read_bytes(), before)

    def test_refresh_profile_defaults_requires_manifest(self) -> None:
        result = self.run_install("orcarouter")
        self.assertEqual(result.returncode, 0, result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = subprocess.run(
                [
                    str(ROOT / "install.sh"),
                    "--model", "orcarouter",
                    "--lang", "en",
                    "--yes",
                    "--no-start",
                    "--refresh-profile-defaults",
                    "--dry-run",
                ],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires an existing installation manifest", result.stderr)


if __name__ == "__main__":
    unittest.main()
