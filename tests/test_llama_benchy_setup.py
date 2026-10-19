"""Synthetic-only pinned benchmark tool setup admission tests; no network/install."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/wizard/llama-benchy-setup.sh"


class PinnedBenchySetupTests(unittest.TestCase):
    def test_shell_syntax(self) -> None:
        proc = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_plan_is_no_mutation_even_without_lifecycle_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "HOME": tmp,
                   "XDG_STATE_HOME": str(Path(tmp) / "none")}
            result = subprocess.run(
                ["bash", str(SCRIPT), "--plan"],
                cwd=ROOT, env=env, capture_output=True,
                text=True, timeout=15, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("BENCHY_SETUP=PLAN_ONLY_NO_NETWORK_OR_MUTATION",
                          result.stdout)
            self.assertIn("BENCHY_SETUP_MODEL_DOCKER_GPU_SERVICE_CHANGE=NONE",
                          result.stdout)
            self.assertIn("e9be344578cec17745066b220798b80a0d2686d3",
                          result.stdout)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_install_default_no(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "HOME": tmp}
            result = subprocess.run(
                ["bash", str(SCRIPT), "--install"], input="INSTALL_PINNED_BENCHY\n",
                cwd=ROOT, env=env, capture_output=True,
                text=True, timeout=15, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("BLOCKED_INTERACTIVE_DEFAULT_NO_APPROVAL_REQUIRED",
                          result.stderr)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_wizard_exposes_post_stop_pinned_install_only(self):
        menu = (ROOT / "scripts/wizard/benchmark-menu.sh").read_text(encoding="utf-8")
        self.assertIn("wizard_menu_option 5 'Pinned llama-benchy setup (post-STOP ONLY)", menu)
        self.assertIn("llama-benchy-setup.sh\" --plan", menu)
        self.assertIn("QWEN38_BENCHY_SETUP_APPROVED=1 bash", menu)
        self.assertIn("wizard_yes_no 'Install pinned llama-benchy", menu)

    def test_script_has_explicit_session_safety_and_pinned_version(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for value in ("flock -n -x", "docker ps", "ss -H -ltn",
                      "QWEN38_BENCHY_SETUP_APPROVED",
                      "INSTALL_PINNED_BENCHY", "python3 -m venv",
                      "git+https://github.com/eugr/llama-benchy.git@",
                      "0.4.1.dev1+ge9be34457",
                      "BENCHY_SETUP_REQUIRES_NEW_EXPLICIT_M1_TRIAL"):
            self.assertIn(value, source)
        for forbidden in ("docker run", "docker start", "docker rm",
                          "rm -rf", "sudo ", "systemctl start",
                          "pip install --system"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
