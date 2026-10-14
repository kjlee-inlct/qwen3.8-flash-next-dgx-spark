"""Synthetic M1 journal reconciliation, no actual Docker side effects."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("m1_reconcile_target", ROOT / "scripts/runtime/mazinb-m1.py")
assert spec and spec.loader
M1 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M1
spec.loader.exec_module(M1)


class ReconcileSafety(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.state, self.data = base / "state", base / "data"
        self.m1 = self.state / "mazinb-m1"
        self.name = "qwen38-mazinb-m1-20261014013811-16ced779"
        self.trial = self.m1 / self.name
        self.monitor = self.trial / "monitor"
        self.old = "b"*64
        self.id = "a"*64
        self.image = "sha256:" + "c"*64
        self.old_image = "sha256:" + "d"*64
        self.monitor.mkdir(parents=True)
        (self.trial / "home").mkdir()
        (self.state / "operation.lock").touch()
        (self.m1 / "benchmark.lock").touch(mode=0o600)
        (self.m1 / "benchmark.lock").chmod(0o600)
        (self.monitor / "armed").write_text(self.id)
        (self.monitor / "heartbeat").write_text("1")
        (self.trial / "monitor.log").write_text(
            "HEARTBEAT healthy\ncontainer is no longer running; monitor exiting\n")
        (self.state / "install.env").write_text("sample")
        release = self.data / "releases" / "test"
        release.mkdir(parents=True)
        (self.data / "current").symlink_to(release)
        self.record = {
            "schema": 1, "name": self.name, "id": self.id, "old_id": self.old,
            "old_image_id": self.old_image, "image_id": self.image,
            "release": str(release),
            "manifest_sha256": hashlib.sha256(b"sample").hexdigest(),
            "model": M1.MODEL, "port": M1.PORT, "kv_bytes": M1.KV_BYTES,
            "monitor_dir": str(self.monitor), "trial_home": str(self.trial/"home"),
            "started_at": "2026-10-14T01:38:11+00:00",
            "kernel_since": "2026-10-14 01:38:11",
            "phase": "stopping", "detail": "operator end or protective error",
        }
        self.save()
        self.candidate = {"State": {"Status": "exited", "Running": False,
                                    "ExitCode": 0, "OOMKilled": False,
                                    "FinishedAt": "2026-10-14T02:41:14Z"}}
        old = {"Image": self.old_image}
        for p in (
            mock.patch.object(M1, "state_paths", return_value=(self.state, self.data, self.m1)),
            mock.patch.object(M1, "read_manifest", return_value=({}, self.record["manifest_sha256"])),
            mock.patch.object(M1, "snapshot_old", return_value=old),
            mock.patch.object(M1, "check_trial_history"),
            mock.patch.object(M1, "pinned_candidate", side_effect=lambda _: self.candidate),
            mock.patch.object(M1, "call", side_effect=self.commands),
        ):
            p.start()
            self.addCleanup(p.stop)

    def save(self):
        for path in (self.m1 / "active.json", self.m1 / (self.name + ".json")):
            path.write_text(json.dumps(self.record))
            path.chmod(0o600)

    def commands(self, *args, **_):
        if args[0] == "systemctl":
            return subprocess.CompletedProcess(args, 0, "inactive\n", "")
        if args[0] == "ps":
            return subprocess.CompletedProcess(args, 0, "python3 unrelated.py\n", "")
        raise AssertionError("unexpected external command " + repr(args))

    def test_exact_exited_unknown_stop_and_repeat(self):
        M1.reconcile()
        a = M1.read_json(self.m1 / "active.json")
        self.assertEqual(a, M1.read_json(self.m1 / (self.name + ".json")))
        self.assertEqual((a["phase"], a["exit_code"]), ("stopped", 0))
        self.assertEqual(a["recovery_shutdown_cause"], "UNDETERMINED")
        self.assertEqual(a["recovery_host_stability"], "INCONCLUSIVE")
        self.assertEqual(len(list(self.m1.glob("*.bak"))), 2)
        M1.reconcile()
        self.assertEqual(len(list(self.m1.glob("*.bak"))), 2)

    def test_running_blocks_without_backup(self):
        self.candidate["State"].update({"Status": "running", "Running": True})
        with self.assertRaisesRegex(M1.M1Error, "not proved exited"):
            M1.reconcile()
        self.assertFalse(list(self.m1.glob("*.bak")))

    def test_missing_watchdog_end_blocks(self):
        (self.trial / "monitor.log").write_text("HEARTBEAT healthy\n")
        with self.assertRaisesRegex(M1.M1Error, "termination evidence"):
            M1.reconcile()

    def test_divergent_trial_id_blocks(self):
        path = self.m1 / (self.name + ".json")
        row = json.loads(path.read_text())
        row["id"] = "f"*64
        path.write_text(json.dumps(row))
        with self.assertRaisesRegex(M1.M1Error, "provenance diverged"):
            M1.reconcile()

    def test_protection_marker_classifies_failure(self):
        p = self.monitor / "runtime-stop.env"
        p.write_text("RUNTIME_STOP_SCHEMA_VERSION=1\nSTOP_REASON=memory-protection\n"
                     "STOP_CONTAINER_NAME=" + self.name + "\nSTOP_CONTAINER_ID=" + self.id + "\n")
        p.chmod(0o600)
        M1.reconcile()
        self.assertEqual(M1.read_json(self.m1 / "active.json")["phase"], "failed_stopped")

    def test_bad_stop_marker_rejected(self):
        p = self.monitor / "runtime-stop.env"
        p.write_text("STOP_CONTAINER_ID=" + "f"*64)
        p.chmod(0o600)
        with self.assertRaisesRegex(M1.M1Error, "not pinned"):
            M1.reconcile()

    def test_live_supervisor_blocks(self):
        def busy(*args, **kwargs):
            if args[0] == "ps":
                return subprocess.CompletedProcess(
                    args, 0, "python3 scripts/runtime/mazinb-m1.py run --expected-old-id " + self.old, "")
            return self.commands(*args, **kwargs)
        with mock.patch.object(M1, "call", side_effect=busy):
            with self.assertRaisesRegex(M1.M1Error, "supervisor process"):
                M1.reconcile()


if __name__ == "__main__":
    unittest.main()
