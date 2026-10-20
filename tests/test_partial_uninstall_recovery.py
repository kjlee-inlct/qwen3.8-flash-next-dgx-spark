"""Synthetic-only partial-uninstall recovery tests. No sudo or real Docker calls."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qwen_partial_uninstall_recovery_fixture",
    ROOT / "scripts/lifecycle/partial-uninstall-recovery.py",
)
assert SPEC and SPEC.loader
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


class RecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        self.home = base / "home"
        self.checkout = self.home / "Workspace/llm/qwen3.8-flash-next-dgx-spark"
        self.state = self.home / ".local/state/qwen38-spark"
        self.data = self.home / ".local/share/qwen38-spark"
        self.cache = self.home / ".cache"
        self.benchmark = self.home / "Workspace/llm/qwen38-m1-bench-results"
        for p in (self.checkout, self.state, self.data, self.cache,
                  self.benchmark, self.checkout / "docs/model-reports/evidence",
                  self.checkout / "scripts/benchmark/evidence"):
            p.mkdir(parents=True, exist_ok=True)
        self.fstab = base / "fstab"
        self.fstab.write_text("")
        self.scope = {
            "home": str(self.home), "checkout": str(self.checkout),
            "state": str(self.state), "data": str(self.data),
            "models": str(self.checkout / "models"),
            "units": str(base / "units"),
            "fstab": str(self.fstab), "swap": "/swap-ple.img",
            "hf": str(self.cache / "huggingface"),
        }
        self.targets = []
        paths = {
            "project-cache": [
                self.cache / "flashinfer-v029", self.cache / "vllm-qwen38",
                self.cache / "vllm-qwen38-v029",
            ],
            "forensic": [
                self.checkout / "docs/model-reports/evidence",
                self.checkout / "scripts/benchmark/evidence",
                self.benchmark,
            ],
            "data-root": [self.data],
            "state-root": [self.state],
        }
        for kind, items in paths.items():
            for root in items:
                root.mkdir(parents=True, exist_ok=True)
                s = root.lstat()
                self.targets.append({
                    "kind": kind, "id": str(root),
                    "fingerprint": {"dev": s.st_dev, "ino": s.st_ino,
                                    "mode": s.st_mode},
                })
        self.state.joinpath("operation.lock").write_text("")
        for i in range(8):
            self.targets.append({"kind": "container", "id": format(i, "064x")})
        for i in range(7):
            self.targets.append({"kind": "image", "id": f"vllm-test{i}:v1"})
        for i in range(2):
            self.targets.append({"kind": "model", "id": f"model-{i}"})
        self.targets.extend([
            {"kind": "legacy-model-link", "id": str(self.checkout / "model")},
            {"kind": "release-link", "id": str(self.data / "current")},
            {"kind": "release-link", "id": str(self.data / "previous")},
            {"kind": "swap", "id": "/swap-ple.img"},
        ])
        self.owner_exception = {
            "entries": [{"kind": "image", "locator": str(i)}
                        for i in range(9)]
        }
        body = {
            "schema": 1, "mode": "EXACT_PROJECT_RESET",
            "scope": self.scope, "targets": self.targets,
            "owner_exception": self.owner_exception,
        }
        self.plan = {**body, "sha256": recovery.full.digest(body)}
        self.plan_file = self.home / "saved-full-receipt.json"
        self.plan_file.write_text(json.dumps(self.plan))

    def bound_roots(self):
        with patch.object(recovery, "ROOT", self.checkout):
            return recovery.check_scope(self.plan, self.plan["sha256"])

    def test_exact_old_receipt_scoped_eight_remaining_roots(self) -> None:
        roots = self.bound_roots()
        self.assertEqual(len(roots), 8)
        self.assertEqual(roots[0]["kind"], "project-cache")
        self.assertEqual(roots[-1]["kind"], "state-root")
        with patch.object(recovery, "ROOT", self.checkout):
            with self.assertRaisesRegex(recovery.RecoveryBlocked,
                                        "original_receipt_sha_mismatch"):
                recovery.check_scope(self.plan, "f" * 64)

    def test_root_identity_changed_is_blocked(self) -> None:
        with patch.object(recovery, "ROOT", self.checkout):
            roots = self.bound_roots()
            recovery.full_scope = self.scope
            roots[0]["fingerprint"]["ino"] += 1
            with self.assertRaisesRegex(recovery.RecoveryBlocked,
                                        "residual_root_identity_changed"):
                recovery.classify_roots(roots)

    def test_same_device_nested_mount_is_blocked(self) -> None:
        roots = self.bound_roots()
        recovery.full_scope = self.scope
        with patch.object(recovery, "mounted_paths",
                          return_value={Path(roots[0]["id"]) / "nested"}):
            with self.assertRaisesRegex(recovery.RecoveryBlocked, "nested_mount"):
                recovery.classify_roots(roots)

    def test_fd_relative_symlink_unlinked_without_traversal(self) -> None:
        outside = self.home / "foreign-data"
        outside.mkdir()
        (outside / "must-stay.txt").write_text("untouched")
        root = self.cache / "flashinfer-v029"
        (root / "nested").mkdir()
        (root / "nested" / "generated.cu").write_text("kernel")
        (root / "external").symlink_to(outside, target_is_directory=True)
        t = next(t for t in self.targets if t["id"] == str(root))
        recovery.delete_one(t)
        self.assertFalse(root.exists())
        self.assertEqual((outside / "must-stay.txt").read_text(), "untouched")

    def test_nonproject_target_cannot_be_approved(self) -> None:
        bad = self.plan["targets"][0]
        bad["id"] = str(self.home / ".cache/flashinfer")
        self.home.joinpath(".cache/flashinfer").mkdir()
        with patch.object(recovery, "ROOT", self.checkout):
            with self.assertRaisesRegex(recovery.full.Blocked,
                                        "unverified_runtime_cache"):
                recovery.check_scope(self.plan, self.plan["sha256"])

    def test_remaining_foreign_docker_must_be_visible_and_unrelated(self) -> None:
        entries = [
            {"ID": "9219d017e6caca2cfb77fb640388c3f6517bb5e2ccedb649b162eb6f78adbb28"},
            {"ID": "12c2de1bae669dcb4163ca4588df290581f69b05935488c9d8d06096d1331658"},
            {"ID": "360cc353a9459cbbc01affea80526272fffa1329ae9609ea42bc0ce1a20c0257"},
        ]
        fake = {"scope": self.scope, "resources": [], "issues": []}
        def docker(*args: str):
            return entries if args[0] == "ps" else []

        with (patch.object(recovery.full.inventory, "gather", return_value=fake),
              patch.object(recovery.full.inventory, "run_docker", side_effect=docker),
              patch.object(recovery.full.inventory, "reference_audit",
                           return_value={"result": "NO_OBSERVED_CONFLICTS",
                                         "external_container_count": 3,
                                         "project_container_count": 0})):
            recovery.missing_other_assets(self.plan)

        with (patch.object(recovery.full.inventory, "gather", return_value=fake),
              patch.object(recovery.full.inventory, "run_docker",
                           side_effect=lambda *args: entries[:2] if args[0] == "ps" else []),
              patch.object(recovery.full.inventory, "reference_audit",
                           side_effect=AssertionError("no audit on incomplete Docker set"))):
            with self.assertRaisesRegex(recovery.RecoveryBlocked,
                                        "foreign_docker_containers_not_all_visible"):
                recovery.missing_other_assets(self.plan)

        with (patch.object(recovery.full.inventory, "gather", return_value=fake),
              patch.object(recovery.full.inventory, "run_docker", side_effect=docker),
              patch.object(recovery.full.inventory, "reference_audit",
                           return_value={"result": "CONFLICTS",
                                         "external_container_count": 3,
                                         "project_container_count": 0})):
            with self.assertRaisesRegex(recovery.RecoveryBlocked, "reference_or_count_changed"):
                recovery.missing_other_assets(self.plan)

    def test_docker_reappearance_blocks_recovery(self) -> None:
        fake = {"scope": self.scope, "resources": [], "issues": []}
        with (patch.object(recovery.full.inventory, "gather", return_value=fake),
              patch.object(recovery.full.inventory, "run_docker",
                           return_value=[{"ID": "0" * 64}])):
            with self.assertRaisesRegex(recovery.RecoveryBlocked,
                                        "container_reappeared"):
                recovery.missing_other_assets(self.plan)

    def test_read_only_audit_does_not_delete(self) -> None:
        args = [str(ROOT / "scripts/lifecycle/partial-uninstall-recovery.py"),
                "audit", "--plan-file", str(self.plan_file),
                "--plan-sha", self.plan["sha256"]]
        output = io.StringIO()
        with (patch.object(sys, "argv", args),
              patch.object(recovery, "ROOT", self.checkout),
              patch.object(recovery, "missing_other_assets"),
              patch.object(recovery, "mounted_paths", return_value=set()),
              patch.object(recovery, "delete_one", side_effect=AssertionError(
                  "audit called destructive delete")),
              contextlib.redirect_stdout(output)):
            self.assertEqual(recovery.main(), 0)
        self.assertIn("RECOVERY_AUDIT=READ_ONLY_COMPLETE", output.getvalue())
        self.assertTrue((self.cache / "flashinfer-v029").exists())

    def test_apply_cannot_run_without_root_and_typed_approval(self) -> None:
        args = [str(ROOT / "scripts/lifecycle/partial-uninstall-recovery.py"),
                "apply", "--plan-file", str(self.plan_file),
                "--plan-sha", self.plan["sha256"]]
        with patch.object(sys, "argv", args):
            with self.assertRaisesRegex(recovery.RecoveryBlocked,
                                        "typed_recovery_approval_missing"):
                recovery.main()
        args += ["--confirm", recovery.CONFIRM]
        with (patch.object(sys, "argv", args),
              patch.object(recovery.os, "geteuid", return_value=1000)):
            with self.assertRaisesRegex(recovery.RecoveryBlocked, "root_required"):
                recovery.main()


if __name__ == "__main__":
    unittest.main()
