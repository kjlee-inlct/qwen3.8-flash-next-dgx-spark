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

    def test_manifest_migration_adds_runtime_safety_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "state" / "qwen38-spark"
            state.mkdir(parents=True)
            manifest = state / "install.env"
            manifest.write_text(
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
                [str(ROOT / "install.sh"), "--migrate-manifest", "--lang", "en"],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            migrated = manifest.read_text(encoding="utf-8")
            self.assertIn("SCHEMA_VERSION=3", migrated)
            self.assertIn("MONITOR_HEARTBEAT=60", migrated)

    def test_monitor_cli_settings_appear_in_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = subprocess.run(
                [
                    str(ROOT / "install.sh"), "--lang", "en", "--yes", "--no-start",
                    "--dry-run", "--protect", "--monitor-min-available-gib", "7",
                    "--monitor-min-swap-free-gib", "9", "--monitor-consecutive", "6",
                    "--monitor-heartbeat", "30",
                ],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("monitor     : enabled", result.stdout)
            self.assertIn("available=7 GiB", result.stdout)
            self.assertIn("swapfree=9 GiB", result.stdout)
            self.assertIn("6 samples, heartbeat=30s", result.stdout)


if __name__ == "__main__":
    unittest.main()
