from __future__ import annotations

import fcntl
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
HELPER = ROOT / "scripts" / "lifecycle" / "profile-switch-transition.sh"


class ProfileSwitchTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.state_dir = self.home / "state" / "qwen38-spark"
        self.data_dir = self.home / "data" / "qwen38-spark"
        self.release = self.data_dir / "releases" / ("1" * 40)
        self.bin_dir = self.home / "bin"
        self.state_dir.mkdir(parents=True)
        self.release.mkdir(parents=True)
        self.bin_dir.mkdir()
        (self.data_dir / "current").symlink_to(self.release)
        self.install = self.state_dir / "install.env"
        self.candidate = self.state_dir / "install.env.profile-switch-candidate"
        self.backup = self.state_dir / "install.env.profile-switch-backup"
        self.transition = self.state_dir / "profile-switch-transition.env"
        self.runtime_commit = self.state_dir / "runtime-commit.env"
        self.old_model = self.home / "models" / "old"
        self.target_model = self.home / "models" / "target"
        self.fake_docker = self.bin_dir / "docker"
        self.fake_docker.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
[[ "${1:-}" == inspect ]] || exit 0
if [[ "${2:-}" != --format ]]; then
  exit 0
fi
format="${3:-}"
case "${format}" in
  '{{.Id}}') printf '%s\\n' "${FAKE_DOCKER_ID}" ;;
  '{{.Config.Image}}') printf '%s\\n' "${FAKE_DOCKER_IMAGE}" ;;
  '{{range .Mounts}}{{if eq .Destination "/model"}}{{.Source}}{{end}}{{end}}')
    printf '%s\\n' "${FAKE_DOCKER_MODEL}"
    ;;
  '{{json .Config.Cmd}}') printf '%s\\n' "${FAKE_DOCKER_CMD}" ;;
  *) exit 2 ;;
esac
""",
            encoding="utf-8",
        )
        self.fake_docker.chmod(self.fake_docker.stat().st_mode | stat.S_IXUSR)
        self.write_manifest(
            self.install,
            profile="orcarouter",
            phase="complete",
            model_dir=self.old_model,
            image="old-image",
            served="old/model",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_manifest(
        self,
        path: Path,
        *,
        profile: str,
        phase: str,
        model_dir: Path,
        image: str,
        served: str,
    ) -> None:
        repo = {
            "orcarouter": "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
            "nvidia": "nvidia/Qwen3.8-Flash-Next-NVFP4",
        }[profile]
        revision = "a" * 40
        path.write_text(
            "\n".join(
                [
                    "SCHEMA_VERSION=4",
                    f"PHASE={phase}",
                    f"INSTALL_ROOT={ROOT}",
                    f"MODEL_PROFILE={profile}",
                    f"MODEL_REPO={repo}",
                    f"MODEL_REVISION={revision}",
                    f"MODEL_DIR={model_dir}",
                    "MODEL_OWNED=0",
                    "SWAP_FILE=/swap-ple.img",
                    "SWAP_OWNED=1",
                    f"VLLM_IMAGE={image}",
                    "IMAGE_OWNED=0",
                    f"SERVED_NAME={served}",
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

    def write_target_candidate(self) -> None:
        self.write_manifest(
            self.candidate,
            profile="nvidia",
            phase="service_ready",
            model_dir=self.target_model,
            image="target-image",
            served="target/model",
        )

    def docker_env(self, profile: str) -> dict[str, str]:
        if profile == "old":
            image = "old-image"
            model = self.old_model
            served = "old/model"
            container_id = "b" * 64
        else:
            image = "target-image"
            model = self.target_model
            served = "target/model"
            container_id = "a" * 64
        return {
            "FAKE_DOCKER_ID": container_id,
            "FAKE_DOCKER_IMAGE": image,
            "FAKE_DOCKER_MODEL": str(model),
            "FAKE_DOCKER_CMD": f'["python","--served-model-name","{served}"]',
        }

    def env(self, profile: str = "old") -> dict[str, str]:
        return {
            **os.environ,
            "HOME": str(self.home),
            "XDG_STATE_HOME": str(self.home / "state"),
            "XDG_DATA_HOME": str(self.home / "data"),
            "PATH": f"{self.bin_dir}:{os.environ.get('PATH', '')}",
            **self.docker_env(profile),
        }

    def run_helper(self, *args: str, profile: str = "old") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(HELPER), *args],
            cwd=ROOT,
            env=self.env(profile),
            text=True,
            capture_output=True,
            check=False,
        )

    def prepare_and_activate(self) -> None:
        result = self.run_helper("prepare", "orcarouter", "nvidia")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.write_target_candidate()
        result = self.run_helper("activate")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def write_target_attestation(self) -> None:
        self.runtime_commit.write_text(
            "\n".join(
                [
                    "RUNTIME_COMMIT_SCHEMA_VERSION=1",
                    f"RUNTIME_ROOT={self.release}",
                    "RUNTIME_CONTAINER_NAME=qwen38-flash-next",
                    f"RUNTIME_CONTAINER_ID={'a' * 64}",
                    "COMMITTED_AT=2026-09-29T12:00:00Z",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def test_prepare_persists_transaction_before_candidate(self) -> None:
        result = self.run_helper("prepare", "orcarouter", "nvidia")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.transition.is_file())
        text = self.transition.read_text(encoding="utf-8")
        self.assertIn("PROFILE_SWITCH_STATE=preparing", text)
        self.assertIn("FROM_PROFILE=orcarouter", text)
        self.assertIn("TO_PROFILE=nvidia", text)
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.candidate.exists())

    def test_recover_power_loss_after_live_activation_before_state_update(self) -> None:
        result = self.run_helper("prepare", "orcarouter", "nvidia")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.write_target_candidate()
        self.backup.write_bytes(self.install.read_bytes())
        self.install.write_bytes(self.candidate.read_bytes())

        result = self.run_helper("recover", profile="target")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        live = self.install.read_text(encoding="utf-8")
        self.assertIn("MODEL_PROFILE=orcarouter", live)
        self.assertIn("PHASE=complete", live)
        self.assertFalse(self.transition.exists())
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.candidate.exists())

    def test_recover_activated_switch_rolls_back_when_previous_runtime_is_provable(self) -> None:
        self.prepare_and_activate()

        result = self.run_helper("recover", profile="old")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MODEL_PROFILE=orcarouter", self.install.read_text(encoding="utf-8"))
        self.assertFalse(self.transition.exists())

    def test_recover_runtime_committed_switch_finishes_target_manifest(self) -> None:
        self.prepare_and_activate()
        self.write_target_attestation()

        result = self.run_helper("runtime-committed", profile="target")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PROFILE_SWITCH_STATE=runtime_committed", self.transition.read_text(encoding="utf-8"))

        result = self.run_helper("recover", profile="target")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        live = self.install.read_text(encoding="utf-8")
        self.assertIn("MODEL_PROFILE=nvidia", live)
        self.assertIn("PHASE=complete", live)
        self.assertFalse(self.transition.exists())
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.candidate.exists())

    def test_recover_fails_closed_after_runtime_commit_without_attestation(self) -> None:
        self.prepare_and_activate()

        result = self.run_helper("recover", profile="target")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing ambiguous rollback", result.stderr)
        self.assertTrue(self.transition.is_file())
        self.assertIn("MODEL_PROFILE=nvidia", self.install.read_text(encoding="utf-8"))
        self.assertTrue(self.backup.is_file())

    def test_service_recovery_defers_while_installer_lock_is_held(self) -> None:
        result = self.run_helper("prepare", "orcarouter", "nvidia")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lock_path = self.state_dir / "operation.lock"
        with lock_path.open("r+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_helper("service-recover")
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("deferred", result.stdout)
        self.assertTrue(self.transition.is_file())


if __name__ == "__main__":
    unittest.main()
