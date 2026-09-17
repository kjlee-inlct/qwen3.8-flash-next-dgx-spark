from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
HELPER = ROOT / "scripts" / "diagnostics" / "runtime-commit-observability.sh"


class RuntimeCommitObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state_dir = self.root / "state" / "qwen38-spark"
        self.release_dir = self.root / "data" / "qwen38-spark" / "releases" / ("a" * 40)
        self.current_link = self.root / "data" / "qwen38-spark" / "current"
        self.bin_dir = self.root / "bin"
        self.state_dir.mkdir(parents=True)
        self.release_dir.mkdir(parents=True)
        self.current_link.parent.mkdir(parents=True, exist_ok=True)
        self.current_link.symlink_to(self.release_dir)
        self.bin_dir.mkdir()
        docker = self.bin_dir / "docker"
        docker.write_text(
            """#!/usr/bin/env bash
set -e
[[ \"${1:-}\" == inspect ]] || exit 1
if [[ \"${2:-}\" == --format ]]; then
  case \"${3:-}\" in
    '{{.Id}}') printf '%s\\n' \"${TEST_CONTAINER_ID}\" ;;
    '{{.State.Status}}') printf '%s\\n' \"${TEST_CONTAINER_STATE:-running}\" ;;
    *) exit 2 ;;
  esac
  exit 0
fi
[[ \"${2:-}\" == qwen38-flash-next ]] || exit 1
exit 0
""",
            encoding="utf-8",
        )
        docker.chmod(0o755)
        self.container_id = "b" * 64
        self.env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "TEST_CONTAINER_ID": self.container_id,
            "TEST_CONTAINER_STATE": "running",
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_attestation(self, *, container_id: str | None = None, runtime_root: Path | None = None) -> None:
        marker = self.state_dir / "runtime-commit.env"
        marker.write_text(
            "\n".join(
                [
                    "RUNTIME_COMMIT_SCHEMA_VERSION=1",
                    f"RUNTIME_ROOT={runtime_root or self.release_dir}",
                    "RUNTIME_CONTAINER_NAME=qwen38-flash-next",
                    f"RUNTIME_CONTAINER_ID={container_id or self.container_id}",
                    "COMMITTED_AT=2026-09-17T01:00:58Z",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def run_helper(self) -> subprocess.CompletedProcess[str]:
        script = f'''\
set -u
STATE_DIR={self.state_dir!s}
SCRIPT_DIR={ROOT / "scripts"!s}
RUNTIME_CONTAINER=qwen38-flash-next
OBS_CURRENT_LINK={self.current_link!s}
pass() {{ printf '[PASS] %s\\n' "$*"; }}
fail() {{ printf '[FAIL] %s\\n' "$*"; }}
source {HELPER!s}
'''
        return subprocess.run(
            ["bash", "-c", script],
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_attestation_matches_current_release_and_running_container(self) -> None:
        self.write_attestation()
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[PASS] runtime commit attestation is strictly parsed", result.stdout)
        self.assertIn("[PASS] runtime commit root matches current immutable release", result.stdout)
        self.assertIn("[PASS] runtime commit container name matches managed runtime", result.stdout)
        self.assertIn("[PASS] runtime commit container ID matches running container", result.stdout)
        self.assertIn("[PASS] attested runtime container is running", result.stdout)
        self.assertNotIn("[FAIL]", result.stdout)

    def test_container_id_drift_is_reported_as_failure(self) -> None:
        self.write_attestation(container_id="c" * 64)
        result = self.run_helper()
        self.assertIn("[FAIL] runtime commit container-ID mismatch", result.stdout)

    def test_runtime_root_drift_is_reported_as_failure(self) -> None:
        other_release = self.release_dir.parent / ("d" * 40)
        other_release.mkdir()
        self.write_attestation(runtime_root=other_release)
        result = self.run_helper()
        self.assertIn("[FAIL] runtime commit root mismatch", result.stdout)

    def test_missing_attestation_is_reported_as_failure(self) -> None:
        result = self.run_helper()
        self.assertIn("[FAIL] runtime commit attestation is missing or unsafe", result.stdout)

    def test_malformed_attestation_is_rejected_by_strict_parser(self) -> None:
        (self.state_dir / "runtime-commit.env").write_text(
            "RUNTIME_COMMIT_SCHEMA_VERSION=1\nRUNTIME_ROOT=$(touch /tmp/should-not-run)\n",
            encoding="utf-8",
        )
        result = self.run_helper()
        self.assertIn("[FAIL] runtime commit attestation failed strict parsing", result.stdout)


if __name__ == "__main__":
    unittest.main()
