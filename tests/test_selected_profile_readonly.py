"""Synthetic-only coverage for the read-only selected-profile status snapshot."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/lifecycle/inspect-selected-profile.py"


class SelectedProfileSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.state = self.home / "state" / "qwen38-spark"
        self.state.mkdir(parents=True)
        self.bin = self.home / "fake-bin"
        self.bin.mkdir()
        self.calls = self.home / "readonly-queries.log"
        self.stub_docker("exited")
        systemctl = self.bin / "systemctl"
        systemctl.write_text(
            "#!/usr/bin/env bash\n"
            f'printf "systemctl %s\\n" "$*" >> "{self.calls}"\n'
            "printf 'LoadState=loaded\\nActiveState=inactive\\n'\n",
            encoding="utf-8",
        )
        systemctl.chmod(0o700)
        for name in ("sudo", "swapoff", "swapon", "nvidia-smi"):
            stub = self.bin / name
            stub.write_text("#!/bin/sh\necho 'forbidden host command' >&2\nexit 99\n", encoding="utf-8")
            stub.chmod(0o700)

    def stub_docker(self, status: str = "exited", image: str = "synthetic:image") -> None:
        obj = [{
            "State": {"Status": status},
            "Config": {"Image": image, "Cmd": ["--served-model-name", "synthetic/model"]},
            "Mounts": [{"Destination": "/model", "Source": str(self.home / "model")}],
            "Id": "a" * 64,
        }]
        docker = self.bin / "docker"
        docker.write_text(
            "#!/usr/bin/env bash\n"
            f'printf "docker %s\\n" "$*" >> "{self.calls}"\n'
            "cat <<'JSON'\n"
            + json.dumps(obj) + "\nJSON\n",
            encoding="utf-8",
        )
        docker.chmod(0o700)

    def write_manifest(self, phase: str = "complete") -> None:
        fields = {
            "SCHEMA_VERSION": "3", "PHASE": phase,
            "INSTALL_ROOT": str(ROOT),
            "MODEL_PROFILE": "mazinb", "MODEL_REPO": "synthetic/model",
            "MODEL_REVISION": "a" * 40, "MODEL_DIR": str(self.home / "model"),
            "MODEL_OWNED": "0", "SWAP_FILE": str(self.home / "swap.bin"),
            "SWAP_OWNED": "0", "VLLM_IMAGE": "synthetic:image",
            "IMAGE_OWNED": "0", "CONTAINER_NAME": "qwen38-flash-next",
            "CONFIG_OVERRIDE": "", "CONFIG_OWNED": "0",
            "MONITOR_PROTECT": "1", "MONITOR_ENABLED": "1",
            "MONITOR_MIN_AVAILABLE_GIB": "6", "MONITOR_MIN_FREE_GIB": "2",
            "MONITOR_FREE_GATE_GIB": "10", "MONITOR_MIN_SWAP_FREE_GIB": "8",
            "MONITOR_CONSECUTIVE": "5", "MONITOR_HEARTBEAT": "60",
            "PROXY_ENABLED": "0", "PROXY_OWNED": "0", "PROXY_PORT": "8000",
            "SERVICE_ENABLED": "1", "SERVICE_OWNED": "1", "UI_LANG": "en",
            "SERVED_NAME": "synthetic/model",
        }
        (self.state / "install.env").write_text(
            "".join(f"{key}={value}\n" for key, value in fields.items()),
            encoding="utf-8",
        )

    def run_snapshot(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT)], cwd=ROOT,
            env={
                **os.environ, "HOME": str(self.home),
                "XDG_STATE_HOME": str(self.home / "state"),
                "PATH": str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            capture_output=True, text=True, check=False, timeout=15,
        )

    def test_missing_manifest_never_invents_selected_profile(self) -> None:
        result = self.run_snapshot()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MANIFEST_STATUS=MISSING", result.stdout)
        self.assertIn("SELECTED_PROFILE=NONE", result.stdout)
        self.assertIn("ACTUAL_SERVED_PROFILE=NOT_VERIFIED", result.stdout)

    def test_stopped_container_does_not_become_selected_running_profile(self) -> None:
        self.write_manifest()
        result = self.run_snapshot()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SELECTED_PROFILE=mazinb", result.stdout)
        self.assertIn("MONITOR_PROTECT=1", result.stdout)
        self.assertIn("CONTAINER_STATE=EXITED", result.stdout)
        self.assertIn("SERVICE_STATE=INACTIVE", result.stdout)
        self.assertIn("PROFILE_STATUS_SUMMARY=CONTAINER_NOT_RUNNING", result.stdout)
        self.assertIn("ACTUAL_SERVED_PROFILE=NOT_VERIFIED", result.stdout)
        self.assertTrue(self.calls.exists())

    def test_uninstalled_manifest_shows_recorded_but_none_selected(self) -> None:
        self.write_manifest("uninstalled")
        result = self.run_snapshot()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SELECTED_PROFILE=NONE", result.stdout)
        self.assertIn("RECORDED_PROFILE=mazinb", result.stdout)
        self.assertIn("PROFILE_STATUS_SUMMARY=UNINSTALLED_NOT_SERVING", result.stdout)

    def test_malformed_manifest_fails_closed(self) -> None:
        (self.state / "install.env").write_text(
            "SCHEMA_VERSION=4\nMODEL_PROFILE=orcarouter\n", encoding="utf-8"
        )
        result = self.run_snapshot()
        self.assertEqual(result.returncode, 3)
        self.assertIn("MANIFEST_STATUS=INVALID", result.stdout)
        self.assertIn("SELECTED_PROFILE=UNKNOWN", result.stdout)
        self.assertIn("PROFILE_STATUS_SUMMARY=INVALID_MANIFEST", result.stdout)

    def test_pending_transaction_file_blocks_summary_success(self) -> None:
        self.write_manifest()
        (self.state / "profile-switch-transition.env").write_text(
            "PROFILE_SWITCH_STATE=not-valid\n", encoding="utf-8"
        )
        result = self.run_snapshot()
        self.assertEqual(result.returncode, 3)
        self.assertIn("PROFILE_SWITCH_STATE=INVALID", result.stdout)
        self.assertIn("PROFILE_STATUS_SUMMARY=TRANSITION_OR_ARTIFACT_PENDING", result.stdout)

    def test_running_config_alignment_does_not_assert_readiness(self) -> None:
        self.write_manifest()
        self.stub_docker("running")
        result = self.run_snapshot()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RUNTIME_CONFIGURATION=MATCHED_NOT_READINESS", result.stdout)
        self.assertIn("PROFILE_STATUS_SUMMARY=RUNNING_CONFIG_ALIGNED_NOT_HEALTH_QUALIFIED", result.stdout)
        self.assertIn("RUNTIME_ATTESTATION=MISSING", result.stdout)
        self.assertIn("HOST_HEALTH_QUALIFICATION=NOT_ESTABLISHED_BY_THIS_SNAPSHOT", result.stdout)

    def test_running_wrong_image_never_qualifies_profile(self) -> None:
        self.write_manifest()
        self.stub_docker("running", "unrelated:image")
        result = self.run_snapshot()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RUNTIME_CONFIGURATION=MISMATCH_OR_UNKNOWN", result.stdout)
        self.assertIn("PROFILE_STATUS_SUMMARY=RUNNING_UNVERIFIED_OR_DRIFTED", result.stdout)

    def test_symlinked_manifest_is_rejected(self) -> None:
        target = self.home / "other-manifest"
        target.write_text("SCHEMA_VERSION=4\n", encoding="utf-8")
        (self.state / "install.env").symlink_to(target)
        result = self.run_snapshot()
        self.assertEqual(result.returncode, 3)
        self.assertIn("MANIFEST_STATUS=INVALID", result.stdout)


if __name__ == "__main__":
    unittest.main()
