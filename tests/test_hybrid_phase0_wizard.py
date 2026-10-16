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

    def test_retired_wizard_hybrid_routes_are_unreachable(self):
        # The former 7-10 menu routes were retired after physical cleanup.
        # No network, GPU or host services are required for the navigation test.
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            env = {**os.environ, "HOME": str(home),
                   "XDG_STATE_HOME": str(home / "xdg")}
            result = subprocess.run(
                ["/bin/bash", str(ROOT / "wizard.sh"), "--lang", "en"],
                cwd=ROOT, env=env, input="3\\n8\\n9\\n10\\n0\\n0\\n",
                capture_output=True, text=True, check=False, timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.count("Invalid selection"), 3)
            self.assertIn("7) Candidate Hub metadata", result.stdout)
            self.assertNotIn("Hybrid H6 Phase-0 inventory", result.stdout)
            self.assertNotIn("Hybrid H6 launch admission", result.stdout)
            self.assertNotIn("hybrid-phase0-readonly.sh", MENU.read_text())
            self.assertTrue(SCRIPT.is_file())  # historical read-only probe retained
            self.assertFalse((home / "xdg").exists())

    def test_cleanup_success_does_not_report_failure(self):
        source = MENU.read_text(encoding="utf-8")
        self.assertNotIn("wizard_mazinb_retirement_audit  else", source)
        self.assertIn("wizard_mazinb_retirement_audit\n  else\n", source)

if __name__ == "__main__":
    unittest.main()
