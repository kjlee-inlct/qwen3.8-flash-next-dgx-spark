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

    def test_orcarouter_profile(self) -> None:
        result = self.run_install("orcarouter")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4", result.stdout)
        self.assertIn("profile     : orcarouter", result.stdout)

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


if __name__ == "__main__":
    unittest.main()
