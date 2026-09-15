from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class DryRunTests(unittest.TestCase):
    def test_install_dry_run_does_not_create_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = subprocess.run(
                [str(ROOT / "install.sh"), "--lang", "en", "--yes", "--no-start", "--dry-run"],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DRY-RUN complete", result.stdout)
            self.assertIn("systemd boot service", result.stdout)
            self.assertFalse((home / "state").exists())

    def test_uninstall_dry_run_preserves_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "state" / "qwen38-spark"
            state.mkdir(parents=True)
            manifest = state / "install.env"
            manifest.write_text(
                "\n".join([
                    f"INSTALL_ROOT={ROOT}",
                    "CONTAINER_NAME=qwen38-flash-next",
                    f"MODEL_DIR={home / 'model'}",
                    "MODEL_OWNED=1",
                    "SWAP_FILE=/swap-ple.img",
                    "SWAP_OWNED=1",
                    "VLLM_IMAGE=test-image",
                    "IMAGE_OWNED=1",
                    "CONFIG_OWNED=0",
                    "PROXY_OWNED=0",
                    "UI_LANG=en",
                    "",
                ]),
                encoding="utf-8",
            )
            before = manifest.read_bytes()
            result = subprocess.run(
                [str(ROOT / "uninstall.sh"), "--lang", "en", "--yes", "--purge-all", "--dry-run"],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DRY-RUN complete", result.stdout)
            self.assertEqual(manifest.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
