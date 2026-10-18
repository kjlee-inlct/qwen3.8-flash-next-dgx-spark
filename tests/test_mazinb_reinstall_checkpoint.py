"""Host-free tests for bounded reinstall preflight and separate download approval."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/wizard/mazinb-restore.sh"
CONTROLLER = ROOT / "scripts/runtime/mazinb-m1.py"


class MzinbReinstallTests(unittest.TestCase):
    def test_no_manifest_never_contacts_hub_or_creates_model_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = {**os.environ, "HOME": tmp, "XDG_STATE_HOME": str(home / "xdg")}
            env.pop("QWEN38_MAZINB_RESTORE_APPROVED", None)
            for cmd in ("preflight", "apply"):
                r = subprocess.run(
                    ["bash", str(SCRIPT), cmd], env=env, cwd=ROOT,
                    capture_output=True, text=True, timeout=10, check=False)
                self.assertEqual(r.returncode, 2, r.stdout+r.stderr)
                self.assertIn("BLOCKED_MANIFEST_OR_MODEL_ROOT_UNSAFE", r.stderr)
                self.assertFalse((home / "xdg").exists())

    def test_pinned_model_identity_and_no_managed_service_reactivation(self):
        script = SCRIPT.read_text()
        registry = (ROOT / "scripts/model/model-profiles.sh").read_text()
        sha = "f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f"
        self.assertIn(sha, script)
        self.assertIn(sha, registry)
        self.assertIn("verify-managed-idle.py", script)
        self.assertIn('d.get("SERVICE_ENABLED") != "0"', script)
        self.assertIn('d.get("SERVICE_OWNED")', CONTROLLER.read_text())
        self.assertIn('bash "$ROOT_DIR/scripts/download-weights.sh" --candidate --check', script)
        self.assertIn('bash "$ROOT_DIR/scripts/download-weights.sh" --candidate ||', script)
        self.assertIn("QWEN38_MAZINB_RESTORE_APPROVED", script)
        self.assertIn("MAZINB_RESTORE_GPU_START=NOT_PERFORMED", script)
        for forbidden in ("systemctl start", "docker start", "docker rm", "rm -rf",
                          "uninstall.sh", "manage-settings --no-service"):
            self.assertNotIn(forbidden, script)


if __name__ == "__main__":
    unittest.main()
