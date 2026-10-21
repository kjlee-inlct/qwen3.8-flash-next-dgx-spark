"""Isolated non-host tests for freshly authorized 8-root orphaned receipt cleanup."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qwen38_fresh_residual_recovery_fixture",
    ROOT / "scripts/lifecycle/fresh-residual-recovery.py",
)
assert SPEC and SPEC.loader
fresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fresh)


class FreshResidualRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.home = base / "home"
        self.checkout = self.home / "Workspace/llm/qwen3.8-flash-next-dgx-spark"
        self.state = self.home / ".local/state/qwen38-spark"
        self.data = self.home / ".local/share/qwen38-spark"
        self.bench = self.home / "Workspace/llm/qwen38-m1-bench-results"
        for path in (
            self.checkout, self.state, self.data, self.bench,
            self.checkout / "docs/model-reports/evidence",
            self.checkout / "scripts/benchmark/evidence",
            self.home / ".cache/flashinfer-v029",
            self.home / ".cache/vllm-qwen38",
            self.home / ".cache/vllm-qwen38-v029",
        ):
            path.mkdir(parents=True, exist_ok=True)
        (self.state / "operation.lock").write_bytes(b"")
        self.scope = {
            "home": str(self.home), "checkout": str(self.checkout),
            "state": str(self.state), "data": str(self.data),
            "models": str(self.checkout / "models"),
            "units": "/etc/systemd/system", "swap": "/swap-ple.img",
            "hf": str(self.home / ".cache/huggingface"),
            "fstab": "/etc/fstab",
        }
        self.receipt = self.home / fresh.RECEIPT_BASENAME
        self.patchers = [
            patch.object(fresh, "expected_scope", return_value=self.scope),
            patch.object(fresh, "ROOT", self.checkout),
            patch.object(fresh, "receipt_path", side_effect=self.local_receipt_path),
            patch.object(fresh.os, "geteuid", return_value=0),
            patch.object(fresh.support, "missing_other_assets"),
            patch.object(fresh.support, "mounted_paths", return_value=set()),
        ]
        for p in self.patchers:
            p.start()
            self.addCleanup(p.stop)

    def local_receipt_path(self, path, scope):
        if path != self.receipt or path.is_symlink():
            raise fresh.Refused("unapproved_receipt_destination")

    def make_plan(self) -> dict:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(fresh.run("snapshot", self.receipt, None, None), 0)
        self.assertIn("NEW_RESIDUAL_RECEIPT=CREATED", buf.getvalue())
        plan = json.loads(self.receipt.read_text())
        self.assertEqual(plan["mode"], fresh.MODE)
        return plan

    def test_fresh_snapshot_contains_only_fixed_8_project_roots(self):
        plan = self.make_plan()
        self.assertEqual(len(plan["targets"]), 8)
        self.assertEqual(
            {x["kind"] for x in plan["targets"]},
            {"project-cache", "forensic", "data-root", "state-root"},
        )
        self.assertTrue(all(x["id"].startswith(str(self.home) + "/")
                            for x in plan["targets"]))
        self.assertEqual(
            fresh.validate(plan, plan["sha256"]), plan["targets"])
        self.assertFalse((self.home / ".cache/flashinfer").exists())
        with self.assertRaisesRegex(fresh.Refused, "no_overwrite"):
            fresh.save_new_receipt(self.receipt, plan, self.scope)

    def test_audit_read_only_refuses_bad_sha(self):
        plan = self.make_plan()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(
                fresh.run("audit", self.receipt, plan["sha256"], None), 0)
        self.assertIn("RESIDUAL_ROOTS_EXACT=8", output.getvalue())
        self.assertIn("FRESH_RECOVERY_AUDIT=READ_ONLY_PASS", output.getvalue())
        self.assertTrue(self.state.exists())
        with self.assertRaisesRegex(fresh.Refused, "integrity"):
            fresh.run("audit", self.receipt, "f"*64, None)

    def test_unapproved_targets_and_fingerprints_refused(self):
        plan = self.make_plan()
        spoof = json.loads(json.dumps(plan))
        spoof["targets"][0]["id"] = str(self.home / ".cache/flashinfer")
        spoof["sha256"] = fresh.full.digest(
            {k:v for k,v in spoof.items() if k != "sha256"})
        with self.assertRaises((fresh.Refused, fresh.full.Blocked)):
            fresh.validate(spoof, spoof["sha256"])
        spoof = json.loads(json.dumps(plan))
        spoof["targets"][0]["fingerprint"]["ino"] += 1
        spoof["sha256"] = fresh.full.digest(
            {k:v for k,v in spoof.items() if k != "sha256"})
        fresh.validate(spoof, spoof["sha256"])
        fresh.support.full_scope = self.scope
        with self.assertRaisesRegex(fresh.support.RecoveryBlocked, "identity_changed"):
            fresh.support.classify_roots(spoof["targets"])

    def test_apply_deletes_only_eight_project_roots_without_following_symlinks(self):
        outside = self.home / "personal-important"
        outside.mkdir()
        (outside / "preserve.txt").write_text("unrelated")
        cache = self.home / ".cache/flashinfer-v029"
        (cache / "nested").mkdir()
        (cache / "nested" / "generated.cu").write_text("data")
        (cache / "foreign-link").symlink_to(outside, target_is_directory=True)
        (self.data / "current").symlink_to(outside, target_is_directory=True)
        plan = self.make_plan()
        with patch.object(fresh.full, "verify_removed", return_value=(True, [])):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(
                    fresh.run("apply", self.receipt, plan["sha256"], fresh.CONFIRM), 0)
        self.assertIn("FRESH_RECOVERY_POSTCHECK=PROJECT_SCOPED_EMPTY", buf.getvalue())
        self.assertEqual((outside / "preserve.txt").read_text(), "unrelated")
        self.assertTrue(self.receipt.is_file())
        self.assertTrue(self.checkout.exists())
        for item in plan["targets"]:
            self.assertFalse(Path(item["id"]).exists())

    def test_fail_closed_before_deleting_on_missing_or_mount_root(self):
        plan = self.make_plan()
        roots = [Path(t["id"]) for t in plan["targets"]]
        missing = roots[0]
        missing.rmdir()
        with patch.object(fresh.support, "delete_one",
                          side_effect=AssertionError("must not delete")):
            with self.assertRaises((fresh.Refused, fresh.full.Blocked)):
                fresh.run("apply", self.receipt, plan["sha256"], fresh.CONFIRM)

    def test_requires_privilege_consent_and_trusted_receipt_location(self):
        plan = self.make_plan()
        with patch.object(fresh.os, "geteuid", return_value=1000):
            with self.assertRaisesRegex(fresh.Refused, "root_required"):
                fresh.run("apply", self.receipt, plan["sha256"], fresh.CONFIRM)
        with self.assertRaisesRegex(fresh.Refused, "explicit_sha_and_exact_approval"):
            fresh.run("apply", self.receipt, plan["sha256"], None)
        with self.assertRaisesRegex(fresh.Refused, "approval_or_sha"):
            fresh.run("snapshot", self.receipt, plan["sha256"], None)

    def test_read_only_snapshot_refuses_nested_mount(self):
        marker = self.home / ".cache/flashinfer-v029/nested"
        marker.mkdir()
        with patch.object(fresh.support, "mounted_paths", return_value={marker}):
            with self.assertRaisesRegex(fresh.support.RecoveryBlocked, "nested_mount"):
                fresh.run("snapshot", self.receipt, None, None)
        self.assertFalse(self.receipt.exists())

    def test_apply_does_not_accept_receipt_content_tamper(self):
        plan = self.make_plan()
        payload = json.loads(self.receipt.read_text())
        payload["targets"][0]["fingerprint"]["dev"] += 1
        self.receipt.write_text(json.dumps(payload))
        with patch.object(fresh.support, "delete_one",
                          side_effect=AssertionError("no deletion with tamper")):
            with self.assertRaisesRegex(fresh.Refused, "integrity"):
                fresh.run("apply", self.receipt, plan["sha256"], fresh.CONFIRM)


if __name__ == "__main__":
    unittest.main()
