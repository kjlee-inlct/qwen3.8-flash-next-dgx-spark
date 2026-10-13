"""Interactive installer menu recovery, using only disposable HOME/XDG dry-runs.

These tests deliberately never execute a real Docker, swap, service or GPU action.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WizardMenuValidationTests(unittest.TestCase):
    def run_wizard(
        self, home: Path, answers: str, *, language: str | None = "en"
    ) -> subprocess.CompletedProcess[str]:
        cmd = [str(ROOT / "install.sh"), "--no-start", "--dry-run"]
        if language is not None:
            cmd.extend(("--lang", language))
        env = {**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")}
        env.pop("MODEL_PROFILE", None)
        env.pop("QWEN38_MODEL_ROOT", None)
        return subprocess.run(
            cmd, cwd=ROOT, env=env, input=answers,
            capture_output=True, text=True, check=False, timeout=25,
        )

    @staticmethod
    def create_existing_store(home: Path) -> Path:
        root = home / "models"
        checkpoint = root / "qwen3.8-flash-next-orcarouter"
        checkpoint.mkdir(parents=True)
        (checkpoint / ".qwen38-model-manifest.json").write_text(
            '{"status":"complete"}\n', encoding="utf-8"
        )
        return root

    def test_language_invalid_then_english(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            r = self.run_wizard(home, "99\n2\n2\n\nn\nn\n1\ny\ny\n", language=None)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Invalid language selection.", r.stdout)
            self.assertIn("[2/6] Model selection", r.stdout)
            self.assertIn("profile     : nvidia", r.stdout)
            self.assertIn("DRY-RUN complete", r.stdout)
            self.assertFalse((home / "state").exists())

    def test_language_cancel_before_model_menu(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            r = self.run_wizard(home, "q\n", language=None)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Cancelled / 취소됨", r.stdout)
            self.assertNotIn("[2/6]", r.stdout)
            self.assertFalse((home / "state").exists())

    def test_storage_invalid_then_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.create_existing_store(home)
            r = self.run_wizard(home, "2\n9\n2\nn\nn\n1\ny\ny\n")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Invalid storage selection.", r.stdout)
            self.assertIn(f"storage root: {ROOT / 'models'}", r.stdout)
            self.assertIn("DRY-RUN complete", r.stdout)
            self.assertFalse((home / "state").exists())

    def test_storage_cancel_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.create_existing_store(home)
            r = self.run_wizard(home, "2\n4\n")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("4) Cancel", r.stdout)
            self.assertIn("Cancelled", r.stdout)
            self.assertNotIn("DRY-RUN complete", r.stdout)
            self.assertFalse((home / "state").exists())

    def test_storage_custom_root_is_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.create_existing_store(home)
            custom = home / "custom-store"
            r = self.run_wizard(home, f"2\n3\n{custom}\nn\nn\n1\ny\ny\n")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(f"storage root: {custom}", r.stdout)
            self.assertIn("DRY-RUN complete", r.stdout)
            self.assertFalse((home / "state").exists())

    def test_storage_blank_enter_reuses_existing_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            root = self.create_existing_store(home)
            r = self.run_wizard(home, "2\n\nn\nn\n1\ny\ny\n")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(f"storage root: {root}", r.stdout)
            self.assertIn("DRY-RUN complete", r.stdout)

    def test_storage_eof_after_invalid_never_selects_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.create_existing_store(home)
            r = self.run_wizard(home, "2\n9\n")
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("Input stream closed (EOF)", r.stderr)
            self.assertNotIn("DRY-RUN complete", r.stdout)
            self.assertFalse((home / "state").exists())


if __name__ == "__main__":
    unittest.main()
