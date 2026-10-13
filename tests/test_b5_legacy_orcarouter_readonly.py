"""B5 source-state and invalid-argument tests, with no Docker access."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/diagnostics/check-legacy-orcarouter-b5-readonly.sh"


class B5ReadOnlyTests(unittest.TestCase):
    def invoke(self, add: dict[str, str]) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        for name in (
            "QWEN38_B5_TARGET_SHA", "QWEN38_B5_RELEASE_SHA",
            "QWEN38_B5_PREVIOUS_CONTAINER_ID",
        ):
            env.pop(name, None)
        env.update(add)
        return subprocess.run(
            ["bash", str(SCRIPT)], cwd=ROOT,
            env=env, text=True, capture_output=True, check=False, timeout=10,
        )

    def test_requires_exact_source_sha(self) -> None:
        r = self.invoke({})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("exact_sha_required", r.stderr)
        self.assertNotIn("B5_READONLY=BEGIN", r.stdout)

    def test_requires_installed_release_identity(self) -> None:
        r = self.invoke({"QWEN38_B5_TARGET_SHA": "a" * 40})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("release_sha_required", r.stderr)

    def test_requires_full_previous_container_id(self) -> None:
        r = self.invoke({
            "QWEN38_B5_TARGET_SHA": "a" * 40,
            "QWEN38_B5_RELEASE_SHA": "b" * 40,
            "QWEN38_B5_PREVIOUS_CONTAINER_ID": "f6bfee5a",
        })
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("previous_container_id_required", r.stderr)

    def test_different_checkout_is_refused(self) -> None:
        r = self.invoke({
            "QWEN38_B5_TARGET_SHA": "0" * 40,
            "QWEN38_B5_RELEASE_SHA": "b" * 40,
            "QWEN38_B5_PREVIOUS_CONTAINER_ID": "c" * 64,
        })
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("checkout_sha_mismatch", r.stderr)

    def test_no_mutating_commands_are_present(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("BLOCKED_PENDING_CONTAINER_ID_DECISION_AND_ROLLBACK_PLAN", source)
        self.assertIn("manifest_unmodified", source)
        self.assertIn("dedicated_swap_active", source)
        for forbidden in (
            "docker start", "docker rename", "docker rm ", "systemctl start",
            "systemctl restart", "sudo ", "swapoff ", "git reset --hard",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
