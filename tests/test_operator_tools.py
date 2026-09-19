from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
MANAGE_MODELS = ROOT / "scripts" / "manage-models.sh"
WAIT_READY = ROOT / "scripts" / "wait-ready.sh"


class OperatorToolsTests(unittest.TestCase):
    def test_wait_ready_help_documents_health_and_model_checks(self) -> None:
        result = subprocess.run(
            ["bash", str(WAIT_READY), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/health", result.stdout)
        self.assertIn("/v1/models", result.stdout)
        self.assertIn("--container", result.stdout)
        self.assertIn("--model", result.stdout)

    def test_manage_models_lists_and_dry_runs_inactive_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            model = home / "models" / "old-qwen38"
            model.mkdir(parents=True)
            (model / ".qwen38-model-manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": "complete",
                        "repository": "example/qwen38",
                        "revision": "a" * 40,
                        "files": [{"path": "config.json", "size": 1, "sha256": None}],
                    }
                ),
                encoding="utf-8",
            )
            env = {**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")}
            listed = subprocess.run(
                ["bash", str(MANAGE_MODELS), "list"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn("example/qwen38", listed.stdout)
            self.assertIn(str(model), listed.stdout)
            self.assertIn("no", listed.stdout)

            removed = subprocess.run(
                ["bash", str(MANAGE_MODELS), "remove", str(model), "--dry-run", "--yes"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertIn("DRY-RUN: no files removed.", removed.stdout)
            self.assertTrue(model.is_dir())

    def test_manage_models_has_active_model_deletion_guard(self) -> None:
        script = MANAGE_MODELS.read_text(encoding="utf-8")
        self.assertIn("refusing active model deletion", script)
        self.assertIn("./uninstall.sh --purge-model", script)
        self.assertIn(".qwen38-model-manifest.json", script)
        self.assertIn('"${HOME}/models/"*', script)


if __name__ == "__main__":
    unittest.main()
