"""Synthetic Hybrid Phase-0 safety and Wizard navigation tests; no DGX access."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/wizard/hybrid-phase0-readonly.sh"
MENU = ROOT / "scripts/wizard/model-menu.sh"

class HybridPhase0Tests(unittest.TestCase):
    def test_script_contract_and_syntax(self):
        check = subprocess.run(["/bin/bash", "-n", str(SCRIPT)],
                               capture_output=True, text=True, check=False)
        self.assertEqual(check.returncode, 0, check.stderr)
        body = SCRIPT.read_text(encoding="utf-8")
        for token in ("verify-managed-idle.py", "validate-orcarouter-hybrid.py",
                      "--runtime-only", "docker ps -a", "docker inspect",
                      "sha256sum", "MULTILINK_REGULAR_FILES",
                      "HYBRID_BENCH_AUTHORIZED=NO",
                      "HYBRID_STAGE_DELETION_AUTHORIZED=NO",
                      "PASS_STATIC_INVENTORY_ONLY"):
            self.assertIn(token, body)
        for forbidden in ("docker rm", "docker start", "docker run",
                          "docker system prune", "systemctl start", "systemctl stop",
                          "rm -rf", "git reset", "swapoff"):
            self.assertNotIn(forbidden, body)

    def test_missing_root_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            env = {**os.environ, "HOME": str(home),
                   "XDG_STATE_HOME": str(home / "xdg"),
                   "QWEN38_PHASE0_MODELS_ROOT": str(home / "missing")}
            result = subprocess.run(["/bin/bash", str(SCRIPT)], cwd=ROOT,
                                    env=env, capture_output=True, text=True,
                                    check=False, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("HYBRID_PHASE0_READONLY=BLOCKED", result.stderr)
            self.assertFalse((home / "xdg").exists())

    def test_wizard_menu_7_is_readonly_delegation(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            bin_dir = home / "bin"
            bin_dir.mkdir()
            stub = bin_dir / "bash"
            stub.write_text('#!/bin/sh\n'
                            'printf "%s\\n" "$*" >> "$HOME/calls"\n'
                            'exit 0\n', encoding="utf-8")
            stub.chmod(0o700)
            env = {**os.environ, "HOME": str(home),
                   "XDG_STATE_HOME": str(home / "xdg"),
                   "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", "")}
            result = subprocess.run(
                ["/bin/bash", str(ROOT / "wizard.sh"), "--lang", "en"],
                cwd=ROOT, env=env, input="3\n7\n0\n0\n",
                capture_output=True, text=True, check=False, timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            calls = (home / "calls").read_text(encoding="utf-8")
            self.assertIn("hybrid-phase0-readonly.sh", calls)
            self.assertNotIn("install.sh", calls)
            self.assertNotIn("reclaim-mazinb", calls)
            self.assertFalse((home / "xdg").exists())

    def test_cleanup_success_does_not_report_failure(self):
        source = MENU.read_text(encoding="utf-8")
        self.assertNotIn("wizard_mazinb_retirement_audit  else", source)
        self.assertIn("wizard_mazinb_retirement_audit\n  else\n", source)

if __name__ == "__main__":
    unittest.main()
