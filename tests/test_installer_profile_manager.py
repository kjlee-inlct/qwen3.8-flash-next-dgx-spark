from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class InstalledProfileWizardTests(unittest.TestCase):
    def write_manifest(
        self,
        home: Path,
        phase: str = "complete",
        image: str = "vllm-skinny-tp1:v1",
    ) -> Path:
        state = home / "state" / "qwen38-spark"
        state.mkdir(parents=True)
        manifest = state / "install.env"
        manifest.write_text(
            "\n".join(
                [
                    "SCHEMA_VERSION=4",
                    f"PHASE={phase}",
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
                    "UI_LANG=en",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return manifest

    def run_installer(
        self,
        home: Path,
        answers: str,
        *,
        dry_run: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        args = [str(ROOT / "install.sh"), "--lang", "en", "--no-start"]
        if dry_run:
            args.append("--dry-run")
        return subprocess.run(
            args,
            cwd=ROOT,
            env={**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")},
            input=answers,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_complete_install_wizard_can_preview_profile_switch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            manifest = self.write_manifest(home)
            before = manifest.read_bytes()

            result = self.run_installer(home, "1\n2\ny\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[1/1] Installed setup management", result.stdout)
            self.assertIn("Current profile: orcarouter", result.stdout)
            self.assertIn("[1/1] Model selection", result.stdout)
            self.assertIn("profile     : nvidia", result.stdout)
            self.assertIn("switch      : orcarouter -> nvidia", result.stdout)
            self.assertNotIn("[3/6] Model storage", result.stdout)
            self.assertNotIn("[4/6] Runtime settings", result.stdout)
            self.assertNotIn("[5/6] API and service", result.stdout)
            self.assertIn("DRY-RUN complete", result.stdout)
            self.assertEqual(manifest.read_bytes(), before)

    def test_complete_install_wizard_defaults_to_current_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            manifest = self.write_manifest(home)
            before = manifest.read_bytes()

            result = self.run_installer(home, "1\n\ny\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[1/1] Installed setup management", result.stdout)
            self.assertIn("Current profile: orcarouter", result.stdout)
            self.assertIn("profile     : orcarouter", result.stdout)
            self.assertNotIn("switch      :", result.stdout)
            self.assertIn("DRY-RUN complete", result.stdout)
            self.assertEqual(manifest.read_bytes(), before)

    def test_complete_install_settings_editor_builds_normalized_preview(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            manifest = self.write_manifest(home)
            before = manifest.read_bytes()

            answers = "\n".join(
                [
                    "2",  # edit settings
                    "1",  # keep config
                    "y",  # enable monitor
                    "y",  # enable protection
                    "y",  # customize thresholds
                    "7",
                    "3",
                    "11",
                    "9",
                    "6",
                    "30",
                    "3",  # LAN API
                    "8010",
                    "192.0.2.55",
                    "8011",
                    "n",  # disable service in preview
                    "n",  # keep settings preview-only
                    "y",  # final plan confirmation
                    "",
                ]
            )
            result = self.run_installer(home, answers, dry_run=False)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[1/1] Installed setup management", result.stdout)
            self.assertIn("Edit runtime / API / service settings", result.stdout)
            self.assertNotIn("[1/1] Model selection", result.stdout)
            self.assertIn("profile     : orcarouter", result.stdout)
            self.assertNotIn("switch      :", result.stdout)
            self.assertIn("protection  : enabled", result.stdout)
            self.assertIn(
                "monitor     : enabled (available=7 GiB warn, free=3/11 GiB gate, "
                "swapfree=9 GiB, 6 samples, heartbeat=30s)",
                result.stdout,
            )
            self.assertIn(
                "API access  : Docker apps: 8010; LAN: 192.0.2.55:8011 -> 127.0.0.1:8888",
                result.stdout,
            )
            self.assertIn("service     : Docker container via immutable current release", result.stdout)
            self.assertIn("DRY-RUN complete", result.stdout)
            self.assertEqual(manifest.read_bytes(), before)

    def test_complete_install_wizard_can_preview_profile_default_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            manifest = self.write_manifest(home, image="vllm-skinny-tp1:legacy")
            before = manifest.read_bytes()

            result = self.run_installer(home, "3\ny\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[1/1] Installed setup management", result.stdout)
            self.assertNotIn("[1/1] Model selection", result.stdout)
            self.assertIn("profile     : orcarouter", result.stdout)
            self.assertIn("image change: vllm-skinny-tp1:legacy -> vllm-skinny-tp1:v1", result.stdout)
            self.assertIn("DRY-RUN complete", result.stdout)
            self.assertEqual(manifest.read_bytes(), before)

    def test_complete_install_manager_can_cancel_without_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            manifest = self.write_manifest(home)
            before = manifest.read_bytes()

            result = self.run_installer(home, "4\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[1/1] Installed setup management", result.stdout)
            self.assertIn("Cancelled", result.stdout)
            self.assertNotIn("[6/6] Review installation plan", result.stdout)
            self.assertEqual(manifest.read_bytes(), before)

    def test_incomplete_install_keeps_resume_flow_without_profile_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.write_manifest(home, phase="downloading")

            result = self.run_installer(home, "y\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Resuming installation from phase: downloading", result.stdout)
            self.assertNotIn("Installed setup management", result.stdout)
            self.assertNotIn("Current profile:", result.stdout)
            self.assertNotIn("[1/1] Model selection", result.stdout)
            self.assertIn("DRY-RUN complete", result.stdout)


if __name__ == "__main__":
    unittest.main()
