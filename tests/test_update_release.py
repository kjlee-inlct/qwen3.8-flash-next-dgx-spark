from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
UPDATE_RELEASE = ROOT / "scripts" / "update-release.sh"
MANIFEST = ROOT / "scripts" / "release_manifest.py"


class UpdateReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data" / "qwen38-spark"
        self.state = self.root / "state"
        self.releases = self.data / "releases"
        self.qualified = self.data / "qualified"
        self.releases.mkdir(parents=True)
        self.qualified.mkdir(parents=True)
        self.env = os.environ.copy()
        self.env.update(
            {
                "HOME": str(self.root / "home"),
                "XDG_DATA_HOME": str(self.root / "data"),
                "XDG_STATE_HOME": str(self.state),
            }
        )
        self.baseline = "1" * 40
        self.target = "2" * 40
        self.make_release(self.baseline, "baseline\n")
        self.make_release(self.target, "target\n")
        (self.data / "current").symlink_to(self.releases / self.baseline)
        (self.qualified / f"{self.target}.env").write_text(
            f"QUALIFICATION_SCHEMA_VERSION=1\nQUALIFIED_RELEASE={self.target}\nQUALIFIED_AT=2026-09-16T01:00:00Z\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def make_release(self, release_id: str, body: str) -> None:
        release = self.releases / release_id
        release.mkdir()
        (release / "payload.txt").write_text(body, encoding="utf-8")
        subprocess.run(
            ["python3", str(MANIFEST), "build", str(release), release_id],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_update(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(UPDATE_RELEASE), *args],
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )

    def test_dry_run_does_not_mutate_release_or_update_state(self) -> None:
        before = os.readlink(self.data / "current")

        result = self.run_update(self.target, "--dry-run")

        self.assertIn("DRY-RUN", result.stdout)
        self.assertEqual(os.readlink(self.data / "current"), before)
        self.assertFalse((self.state / "qwen38-spark" / "update-transition.env").exists())

    def test_cutover_refuses_missing_baseline(self) -> None:
        (self.data / "current").unlink()

        result = self.run_update(self.target, "--dry-run", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no immutable baseline", result.stderr)

    def test_cutover_refuses_unqualified_target(self) -> None:
        (self.qualified / f"{self.target}.env").unlink()

        result = self.run_update(self.target, "--dry-run", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not qualified", result.stderr)

    def test_update_commits_only_after_managed_service_returns(self) -> None:
        script = UPDATE_RELEASE.read_text(encoding="utf-8")
        service_call = 'sudo bash "${MANAGE_SERVICE}" create --runtime-root "${CURRENT_LINK}" --start --yes'
        update_commit = 'bash "${UPDATE_TRANSITION}" commit'
        self.assertIn(service_call, script)
        self.assertIn(update_commit, script)
        self.assertLess(script.index(service_call), script.index(update_commit))


if __name__ == "__main__":
    unittest.main()
