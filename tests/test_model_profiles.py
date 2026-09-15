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


if __name__ == "__main__":
    unittest.main()
