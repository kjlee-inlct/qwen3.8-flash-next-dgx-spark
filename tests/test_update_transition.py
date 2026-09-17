from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
RELEASE_MANAGER = ROOT / "scripts" / "release-manager.sh"
UPDATE = ROOT / "scripts" / "update-transition.sh"


class UpdateTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.data = self.root / "data"
        self.state = self.root / "state"
        self.source.mkdir()
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.name", "Update Test"], check=True)
        (self.source / "app.txt").write_text("one\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.source), "add", "app.txt"], check=True)
        subprocess.run(["git", "-C", str(self.source), "commit", "-q", "-m", "one"], check=True)
        self.first = self.rev("HEAD")
        (self.source / "app.txt").write_text("two\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.source), "commit", "-qam", "two"], check=True)
        self.second = self.rev("HEAD")
        self.env = os.environ.copy()
        self.env.update({
            "QWEN38_SOURCE_ROOT": str(self.source),
            "XDG_DATA_HOME": str(self.data),
            "XDG_STATE_HOME": str(self.state),
            "HOME": str(self.root / "home"),
        })
        self.stage_and_mark_qualified(self.first)
        self.stage_and_mark_qualified(self.second)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def rev(self, ref: str) -> str:
        return subprocess.check_output(["git", "-C", str(self.source), "rev-parse", ref], text=True).strip()

    def run_script(self, script: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(script), *args], env=self.env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check,
        )

    def qualification_marker(self, release_id: str) -> Path:
        return self.data / "qwen38-spark" / "qualified" / f"{release_id}.env"

    def release_manifest(self, release_id: str) -> Path:
        return self.data / "qwen38-spark" / "releases" / release_id / ".release-manifest.json"

    def stage_and_mark_qualified(self, release_id: str) -> None:
        self.run_script(RELEASE_MANAGER, "stage", release_id)
        qualified = self.data / "qwen38-spark" / "qualified"
        qualified.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(self.release_manifest(release_id).read_bytes()).hexdigest()
        self.qualification_marker(release_id).write_text(
            "\n".join([
                "QUALIFICATION_SCHEMA_VERSION=2",
                f"QUALIFIED_RELEASE={release_id}",
                f"RELEASE_MANIFEST_SHA256={digest}",
                "QUALIFIED_AT=2026-09-16T01:00:00Z",
                "",
            ]),
            encoding="utf-8",
        )

    def status(self) -> str:
        return self.run_script(RELEASE_MANAGER, "status").stdout

    def test_prepare_then_commit_keeps_target_current(self) -> None:
        self.run_script(RELEASE_MANAGER, "activate", self.first)
        self.run_script(UPDATE, "prepare", self.second)
        self.assertIn(f"CURRENT_RELEASE={self.second}", self.status())
        self.run_script(UPDATE, "commit")
        self.assertIn("UPDATE_STATE=idle", self.run_script(UPDATE, "status").stdout)
        self.assertIn(f"CURRENT_RELEASE={self.second}", self.status())
        self.assertIn(f"PREVIOUS_RELEASE={self.first}", self.status())

    def test_rollback_restores_exact_previous_pointers(self) -> None:
        self.run_script(RELEASE_MANAGER, "activate", self.first)
        self.run_script(UPDATE, "prepare", self.second)
        self.run_script(UPDATE, "rollback")
        status = self.status()
        self.assertIn(f"CURRENT_RELEASE={self.first}", status)
        self.assertIn("PREVIOUS_RELEASE=none", status)

    def test_recover_restores_previous_pointers(self) -> None:
        self.run_script(RELEASE_MANAGER, "activate", self.first)
        self.run_script(UPDATE, "prepare", self.second)
        self.run_script(UPDATE, "recover")
        status = self.status()
        self.assertIn(f"CURRENT_RELEASE={self.first}", status)
        self.assertIn("PREVIOUS_RELEASE=none", status)
        self.assertIn("UPDATE_STATE=idle", self.run_script(UPDATE, "status").stdout)

    def test_prepare_rejects_unqualified_release(self) -> None:
        self.qualification_marker(self.second).unlink()
        result = self.run_script(UPDATE, "prepare", self.second, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not qualified", result.stderr)
        self.assertIn("UPDATE_STATE=idle", self.run_script(UPDATE, "status").stdout)

    def test_prepare_rejects_legacy_unbound_qualification(self) -> None:
        self.qualification_marker(self.second).write_text(
            f"QUALIFICATION_SCHEMA_VERSION=1\nQUALIFIED_RELEASE={self.second}\nQUALIFIED_AT=2026-09-16T01:00:00Z\n",
            encoding="utf-8",
        )
        result = self.run_script(UPDATE, "prepare", self.second, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not manifest-bound", result.stderr)
        self.assertIn("UPDATE_STATE=idle", self.run_script(UPDATE, "status").stdout)

    def test_prepare_rejects_qualification_manifest_digest_mismatch(self) -> None:
        marker = self.qualification_marker(self.second)
        lines = marker.read_text(encoding="utf-8").splitlines()
        marker.write_text(
            "\n".join(
                "RELEASE_MANIFEST_SHA256=" + "0" * 64
                if line.startswith("RELEASE_MANIFEST_SHA256=") else line
                for line in lines
            ) + "\n",
            encoding="utf-8",
        )
        result = self.run_script(UPDATE, "prepare", self.second, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("qualification manifest digest mismatch", result.stderr)
        self.assertIn("UPDATE_STATE=idle", self.run_script(UPDATE, "status").stdout)

    def test_commit_rechecks_qualification_manifest_digest(self) -> None:
        self.run_script(RELEASE_MANAGER, "activate", self.first)
        self.run_script(UPDATE, "prepare", self.second)
        marker = self.qualification_marker(self.second)
        lines = marker.read_text(encoding="utf-8").splitlines()
        marker.write_text(
            "\n".join(
                "RELEASE_MANIFEST_SHA256=" + "f" * 64
                if line.startswith("RELEASE_MANIFEST_SHA256=") else line
                for line in lines
            ) + "\n",
            encoding="utf-8",
        )
        result = self.run_script(UPDATE, "commit", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("qualification manifest digest mismatch", result.stderr)
        self.assertIn("UPDATE_STATE=staged", self.run_script(UPDATE, "status").stdout)

    def test_recover_rejects_executable_state_payload_without_running_it(self) -> None:
        app_state = self.state / "qwen38-spark"
        app_state.mkdir(parents=True, exist_ok=True)
        executed = self.root / "executed"
        (app_state / "update-transition.env").write_text(
            "\n".join(
                [
                    "UPDATE_SCHEMA_VERSION=1",
                    "UPDATE_STATE=staged",
                    f"TARGET_RELEASE=$(touch {executed})",
                    f"OLD_CURRENT_RELEASE={self.first}",
                    "OLD_PREVIOUS_RELEASE=",
                    "UPDATED_AT=2026-09-16T01:00:00Z",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        result = self.run_script(UPDATE, "recover", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid update transition state file", result.stderr)
        self.assertFalse(executed.exists())


if __name__ == "__main__":
    unittest.main()
