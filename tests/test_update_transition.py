from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
RELEASE_MANAGER = ROOT / "scripts" / "release-manager.sh"
QUALIFY = ROOT / "scripts" / "qualify-release.sh"
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

    def stage_and_mark_qualified(self, release_id: str) -> None:
        self.run_script(RELEASE_MANAGER, "stage", release_id)
        qualified = self.data / "qwen38-spark" / "qualified"
        qualified.mkdir(parents=True, exist_ok=True)
        (qualified / f"{release_id}.env").write_text(
            f"QUALIFICATION_SCHEMA_VERSION=1\nQUALIFIED_RELEASE={release_id}\nQUALIFIED_AT=test\n",
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
        marker = self.data / "qwen38-spark" / "qualified" / f"{self.second}.env"
        marker.unlink()
        result = self.run_script(UPDATE, "prepare", self.second, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not qualified", result.stderr)
        self.assertIn("UPDATE_STATE=idle", self.run_script(UPDATE, "status").stdout)


if __name__ == "__main__":
    unittest.main()
