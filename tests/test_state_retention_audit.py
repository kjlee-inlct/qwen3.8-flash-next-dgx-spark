"""Synthetic tests for non-destructive DGX Spark state retention audits."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/storage/state-retention-audit.py"
spec = importlib.util.spec_from_file_location("state_retention_audit", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class StateRetentionAuditTests(unittest.TestCase):
    def test_protects_runtime_and_distinct_archives(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "qwen38-spark"
            root.mkdir()
            (root / "install.env").write_text("PRIVATE_SECRETS_NEVER_ECHO\n")
            (root / "asset-ownership.json").write_text("{}")
            (root / "stability-29.json").write_text("{}")
            (root / "hybrid-retirement-evidence").mkdir()
            archive = root / "retirement-archives"
            archive.mkdir()
            (archive / "hybrid-docker-17-20261015").mkdir()
            (archive / "mazinb-docker-example").mkdir()
            (archive / "hybrid-docker-17-20261015" / "private.log").write_text("secret")
            (root / "unknown-state").write_text("unknown")

            before = {str(p.relative_to(root)): (p.read_bytes() if p.is_file() else None)
                      for p in root.rglob("*")}
            report = mod.audit(root)
            after = {str(p.relative_to(root)): (p.read_bytes() if p.is_file() else None)
                     for p in root.rglob("*")}
            self.assertEqual(before, after)
            by_name = {e["name"]: e for e in report["entries"]}
            self.assertEqual(by_name["install.env"]["category"], "RETAIN_LIFECYCLE")
            self.assertEqual(by_name["asset-ownership.json"]["category"], "RETAIN_LIFECYCLE")
            self.assertEqual(by_name["stability-29.json"]["category"], "REVIEW_ONLY")
            self.assertEqual(by_name["hybrid-retirement-evidence"]["category"], "REVIEW_ONLY")
            self.assertEqual(by_name["retirement-archives/hybrid-docker-17-20261015"]["category"],
                             "RETAIN_UNIQUE_RAW_EVIDENCE")
            self.assertEqual(by_name["retirement-archives/mazinb-docker-example"]["category"],
                             "RETAIN_OTHER_MODEL_EVIDENCE")
            self.assertEqual(by_name["unknown-state"]["category"], "REVIEW_UNKNOWN_PROTECT")
            self.assertFalse(report["delete_authorized"])
            self.assertEqual(report["files_deleted"], 0)
            self.assertNotIn("PRIVATE_SECRETS_NEVER_ECHO", json.dumps(report))

    def test_never_follows_state_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "qwen38-spark"
            root.mkdir()
            external = base / "external"
            external.mkdir()
            (external / "a.log").write_text("private")
            (root / "linked-history").symlink_to(external, target_is_directory=True)
            (root / "linked-log").symlink_to(external / "a.log")
            report = mod.audit(root)
            entries = {e["name"]: e for e in report["entries"]}
            self.assertEqual(entries["linked-history"]["symlinks"], 1)
            self.assertEqual(entries["linked-log"]["symlinks"], 1)
            self.assertEqual(entries["linked-history"]["files"], 0)
            with self.assertRaises(ValueError):
                mod.audit(root / "linked-history")

    def test_cli_read_only_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "state"
            root.mkdir()
            (root / "operation.lock").touch()
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--state-root", str(root), "--json"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["audit"], "READ_ONLY")
            self.assertFalse(report["delete_authorized"])
            self.assertEqual(report["entries"][0]["name"], "operation.lock")


if __name__ == "__main__":
    unittest.main()
