from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
HELPER = ROOT / "scripts" / "doctor-observability.sh"
CANONICAL_HELPER = ROOT / "scripts" / "diagnostics" / "doctor-observability.sh"
MANIFEST_TOOL = ROOT / "scripts" / "release_manifest.py"


class DoctorObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data_home = self.root / "data"
        self.state_home = self.root / "state"
        self.app_data = self.data_home / "qwen38-spark"
        self.app_state = self.state_home / "qwen38-spark"
        self.app_data.mkdir(parents=True)
        self.app_state.mkdir(parents=True)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        for name in ("systemctl", "docker"):
            tool = self.bin_dir / name
            tool.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            tool.chmod(0o755)
        self.env = {**os.environ, "HOME": str(self.root / "home"), "XDG_DATA_HOME": str(self.data_home),
                    "XDG_STATE_HOME": str(self.state_home), "PATH": f"{self.bin_dir}:{os.environ['PATH']}"}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def stage_release(self, release_id: str, *, legacy: bool = False) -> None:
        release_dir = self.app_data / "releases" / release_id
        release_dir.mkdir(parents=True)
        (release_dir / "payload.txt").write_text("known-good\n", encoding="utf-8")
        subprocess.run(["python3", str(MANIFEST_TOOL), "build", str(release_dir), release_id],
                       check=True, text=True, capture_output=True)
        qualified = self.app_data / "qualified"
        qualified.mkdir(exist_ok=True)
        marker = qualified / f"{release_id}.env"
        if legacy:
            marker.write_text(
                f"QUALIFICATION_SCHEMA_VERSION=1\nQUALIFIED_RELEASE={release_id}\n"
                "QUALIFIED_AT=2026-09-16T01:00:00Z\n",
                encoding="utf-8",
            )
        else:
            digest = hashlib.sha256((release_dir / ".release-manifest.json").read_bytes()).hexdigest()
            marker.write_text(
                "\n".join([
                    "QUALIFICATION_SCHEMA_VERSION=2",
                    f"QUALIFIED_RELEASE={release_id}",
                    f"RELEASE_MANIFEST_SHA256={digest}",
                    "QUALIFIED_AT=2026-09-16T01:00:00Z",
                    "",
                ]),
                encoding="utf-8",
            )
        (self.app_data / "current").symlink_to(release_dir)

    def run_helper(self) -> subprocess.CompletedProcess[str]:
        script = f'''\
set -u
STATE_DIR={self.app_state!s}
SCRIPT_DIR={ROOT / "scripts"!s}
RUNTIME_CONTAINER=qwen38-flash-next
SERVICE_UNIT=qwen38-flash-next.service
pass() {{ printf '[PASS] %s\\n' "$*"; }}
warn() {{ printf '[WARN] %s\\n' "$*"; }}
fail() {{ printf '[FAIL] %s\\n' "$*"; }}
source {HELPER!s}
'''
        return subprocess.run(["bash", "-c", script], env=self.env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_verified_current_release_and_idle_update_are_reported_healthy(self) -> None:
        release_id = "a" * 40
        self.stage_release(release_id)
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[PASS] no incomplete update transition exists", result.stdout)
        self.assertIn(f"[PASS] current immutable release is verified ({release_id})", result.stdout)
        self.assertIn("[PASS] current immutable release qualification matches release manifest digest", result.stdout)
        self.assertIn("[PASS] no previous immutable release is registered", result.stdout)
        self.assertIn("[PASS] no stale runtime stop marker exists", result.stdout)
        self.assertIn("[PASS] API access mode is local-only", result.stdout)

    def test_legacy_qualification_is_reported_as_warning(self) -> None:
        release_id = "c" * 40
        self.stage_release(release_id, legacy=True)
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[WARN] current immutable release has legacy unbound qualification", result.stdout)
        self.assertNotIn("qualification matches release manifest digest", result.stdout)

    def test_qualification_digest_drift_is_reported_as_failure(self) -> None:
        release_id = "d" * 40
        self.stage_release(release_id)
        marker = self.app_data / "qualified" / f"{release_id}.env"
        lines = marker.read_text(encoding="utf-8").splitlines()
        marker.write_text(
            "\n".join(
                "RELEASE_MANIFEST_SHA256=" + "0" * 64
                if line.startswith("RELEASE_MANIFEST_SHA256=") else line
                for line in lines
            ) + "\n",
            encoding="utf-8",
        )
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[FAIL] current immutable release qualification manifest digest mismatch", result.stdout)

    def test_active_update_transaction_is_reported_as_failure(self) -> None:
        release_id = "b" * 40
        self.stage_release(release_id)
        (self.app_state / "update-transition.env").write_text(
            "UPDATE_SCHEMA_VERSION=1\nUPDATE_STATE=staged\n", encoding="utf-8")
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[FAIL] update transition is incomplete (staged)", result.stdout)

    def test_doctor_strictly_parses_install_manifest(self) -> None:
        doctor = (ROOT / "scripts" / "doctor.sh").read_text(encoding="utf-8")
        self.assertIn('install-doctor "${STATE_FILE}"', doctor)
        self.assertIn("installation manifest failed strict parsing", doctor)
        self.assertNotIn('source "${STATE_FILE}"', doctor)

    def test_doctor_treats_disabled_monitor_as_configured_state(self) -> None:
        doctor = (ROOT / "scripts" / "doctor.sh").read_text(encoding="utf-8")
        self.assertIn('pass "runtime memory monitor is disabled by configuration"', doctor)
        self.assertNotIn('warn "runtime memory monitor is disabled"', doctor)

    def test_doctor_checks_configured_api_listeners(self) -> None:
        helper = CANONICAL_HELPER.read_text(encoding="utf-8")
        self.assertIn("API_ACCESS_MODE", helper)
        self.assertIn("Docker-app API listener is configured", helper)
        self.assertIn("LAN API listener matches", helper)
        self.assertIn("managed API access socket is active", helper)

    def test_operations_guide_documents_observability_signals(self) -> None:
        operations = (ROOT / "OPERATIONS.md").read_text(encoding="utf-8")
        self.assertIn("current immutable release", operations)
        self.assertIn("runtime-stop.env", operations)
        self.assertIn("disabled by configuration", operations)
        self.assertIn("managed Docker-app and LAN API listeners", operations)


if __name__ == "__main__":
    unittest.main()
