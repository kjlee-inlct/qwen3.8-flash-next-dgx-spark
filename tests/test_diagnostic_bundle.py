from __future__ import annotations

import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "collect-diagnostics.sh"


class DiagnosticBundleTests(unittest.TestCase):
    def test_dry_run_creates_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle.tar.gz"
            result = subprocess.run(
                [str(SCRIPT), "--lang", "en", "--dry-run", "--output", str(output)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DRY-RUN", result.stdout)
            self.assertFalse(output.exists())

    def test_bundle_excludes_secret_manifest_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state" / "qwen38-spark"
            state.mkdir(parents=True)
            (state / "install.env").write_text(
                "MODEL_PROFILE=orcarouter\nHF_TOKEN=hf_thismustnotleak123456789\n",
                encoding="utf-8",
            )
            output = root / "bundle.tar.gz"
            result = subprocess.run(
                [str(SCRIPT), "--lang", "en", "--no-logs", "--output", str(output)],
                cwd=ROOT,
                env={**os.environ, "HOME": str(root), "XDG_STATE_HOME": str(root / "state")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            with tarfile.open(output, "r:gz") as archive:
                names = archive.getnames()
                self.assertIn("qwen38-diagnostics/ABOUT.txt", names)
                for member in archive.getmembers():
                    self.assertEqual(member.uid, 0)
                    self.assertEqual(member.gid, 0)
                    expected_mode = 0o700 if member.isdir() else 0o600
                    self.assertEqual(member.mode & 0o777, expected_mode)
                payload = b"".join(
                    archive.extractfile(name).read()
                    for name in names
                    if archive.getmember(name).isfile()
                )
            self.assertNotIn(b"hf_thismustnotleak", payload)
            self.assertNotIn(str(root).encode(), payload)


if __name__ == "__main__":
    unittest.main()
