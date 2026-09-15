from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "release-manager.sh"


class ReleaseManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.data_home = self.root / "data"
        self.source.mkdir()
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.name", "Release Test"], check=True)
        (self.source / "app.txt").write_text("one\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.source), "add", "app.txt"], check=True)
        subprocess.run(["git", "-C", str(self.source), "commit", "-q", "-m", "one"], check=True)
        self.first = self.rev_parse("HEAD")
        (self.source / "app.txt").write_text("two\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.source), "commit", "-qam", "two"], check=True)
        self.second = self.rev_parse("HEAD")
        self.env = os.environ.copy()
        self.env.update(
            {
                "QWEN38_SOURCE_ROOT": str(self.source),
                "XDG_DATA_HOME": str(self.data_home),
                "HOME": str(self.root / "home"),
            }
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def rev_parse(self, revision: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(self.source), "rev-parse", revision], text=True
        ).strip()

    @property
    def release_root(self) -> Path:
        return self.data_home / "qwen38-spark" / "releases"

    def run_manager(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["bash", str(SCRIPT), *args],
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(
                f"release-manager {' '.join(args)} failed with {result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def test_stage_exports_only_committed_payload_and_reuses_verified_release(self) -> None:
        (self.source / "secret.env").write_text("TOKEN=secret\n", encoding="utf-8")
        first = self.run_manager("stage", self.first)
        release = self.release_root / self.first

        self.assertIn("Release staged", first.stdout)
        self.assertEqual((release / "app.txt").read_text(encoding="utf-8"), "one\n")
        self.assertFalse((release / "secret.env").exists())
        self.assertTrue((release / ".release-manifest.json").is_file())

        second = self.run_manager("stage", self.first)
        self.assertIn("already staged and verified", second.stdout)

    def test_verify_rejects_modified_release(self) -> None:
        self.run_manager("stage", self.first)
        release = self.release_root / self.first
        (release / "app.txt").write_text("tampered\n", encoding="utf-8")

        result = self.run_manager("verify", self.first, check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("differs from immutable manifest", result.stderr)

    def test_activate_and_rollback_swap_release_pointers(self) -> None:
        self.run_manager("stage", self.first)
        self.run_manager("stage", self.second)
        self.run_manager("activate", self.first)
        self.run_manager("activate", self.second)

        status = self.run_manager("status")
        self.assertIn(f"CURRENT_RELEASE={self.second}", status.stdout)
        self.assertIn(f"PREVIOUS_RELEASE={self.first}", status.stdout)

        self.run_manager("rollback")
        status = self.run_manager("status")
        self.assertIn(f"CURRENT_RELEASE={self.first}", status.stdout)
        self.assertIn(f"PREVIOUS_RELEASE={self.second}", status.stdout)

    def test_activate_refuses_tampered_release(self) -> None:
        self.run_manager("stage", self.first)
        release = self.release_root / self.first
        (release / "app.txt").write_text("tampered\n", encoding="utf-8")

        result = self.run_manager("activate", self.first, check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.data_home / "qwen38-spark" / "current").exists())


if __name__ == "__main__":
    unittest.main()
