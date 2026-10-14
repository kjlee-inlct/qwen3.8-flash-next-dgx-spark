"""Pure synthetic tests for M1 background-host read-only capability inspection."""
from __future__ import annotations

import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/runtime/m1-background-probe.py"
SPEC = importlib.util.spec_from_file_location("m1_background_probe_test_target", TARGET)
assert SPEC and SPEC.loader
PROBE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROBE
SPEC.loader.exec_module(PROBE)


class M1BackgroundHostProbeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.runtime = Path(temp.name) / "run"
        self.runtime.mkdir(mode=0o700)
        self.env_patch = mock.patch.dict(os.environ, {
            "XDG_RUNTIME_DIR": str(self.runtime),
        })
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def invoke(self):
        output = io.StringIO()
        with redirect_stdout(output):
            rc = PROBE.probe()
        return rc, output.getvalue()

    def invoke_unit_status(self):
        output = io.StringIO()
        with redirect_stdout(output):
            rc = PROBE.unit_status()
        return rc, output.getvalue()

    @staticmethod
    def mock_unit(load="not-found", active="inactive", sub="dead", pid="0"):
        body = (f"LoadState={load}\\nActiveState={active}\\n"
                f"SubState={sub}\\nMainPID={pid}\\n")
        return subprocess.CompletedProcess(["systemctl"], 0,
                                           stdout=body.replace("\\\\n", "\\n"), stderr="")

    def test_missing_reserved_unit_is_not_claimed_as_supervisor(self):
        calls = []
        def query(*argv):
            calls.append(argv)
            return self.mock_unit()
        with mock.patch.object(PROBE.shutil, "which", return_value="/usr/bin/systemctl"), \
                mock.patch.object(PROBE, "command", side_effect=query):
            rc, out = self.invoke_unit_status()
        self.assertEqual(rc, 0, out)
        self.assertIn("M1_BG_UNIT_STATUS=NOT_FOUND", out)
        self.assertIn("M1_BG_WORKER_IMPLEMENTED=NO", out)
        self.assertIn("M1_BG_WORKER_IDENTITY_VERIFIED=NO", out)
        self.assertEqual(calls, [(
            "systemctl", "--user", "show", PROBE.BG_UNIT,
            "--property=" + ",".join(PROBE.BG_UNIT_FIELDS), "--no-pager")])

    def test_loaded_unit_with_pid_is_untrusted(self):
        with mock.patch.object(PROBE.shutil, "which", return_value="/usr/bin/systemctl"), \
                mock.patch.object(PROBE, "command",
                                  return_value=self.mock_unit("loaded", "active", "running", "1234")):
            rc, out = self.invoke_unit_status()
        self.assertEqual(rc, 2)
        self.assertIn("M1_BG_UNIT_STATUS=BLOCKED_UNTRUSTED_PRESENT", out)
        self.assertIn("UNIT_PROVENANCE_NOT_IMPLEMENTED", out)
        self.assertNotIn("M1_BG_UNIT_STATUS=NOT_FOUND", out)

    def test_malformed_or_duplicate_unit_properties_fail_closed(self):
        invalid = "LoadState=not-found\\nActiveState=inactive\\nMainPID=0\\nMainPID=0\\nSubState=dead\\n"
        response = subprocess.CompletedProcess(["systemctl"], 0,
                                                stdout=invalid, stderr="")
        with mock.patch.object(PROBE.shutil, "which", return_value="/usr/bin/systemctl"), \
                mock.patch.object(PROBE, "command", return_value=response):
            rc, out = self.invoke_unit_status()
        self.assertEqual(rc, 2)
        self.assertIn("MALFORMED_UNIT_PROPERTIES", out)

    def test_unit_manager_error_or_absent_property_blocks(self):
        response = subprocess.CompletedProcess(["systemctl"], 1,
                                                stdout="LoadState=not-found\\n", stderr="no bus")
        with mock.patch.object(PROBE.shutil, "which", return_value="/usr/bin/systemctl"), \
                mock.patch.object(PROBE, "command", return_value=response):
            rc, out = self.invoke_unit_status()
        self.assertEqual(rc, 2)
        self.assertIn("UNIT_QUERY_FAILED", out)

    def test_unsafe_runtime_dir_never_queries_user_manager(self):
        with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": ""}), \
                mock.patch.object(PROBE, "command", side_effect=AssertionError("unexpected query")):
            rc, out = self.invoke_unit_status()
        self.assertEqual(rc, 2)
        self.assertIn("XDG_RUNTIME_DIR_MISSING", out)

    def test_plan_is_pure_and_never_offers_mutating_action(self):
        with mock.patch.object(PROBE, "command", side_effect=AssertionError("must not execute")):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(PROBE.plan(), 0)
        self.assertIn("M1_BG_START=NOT_IMPLEMENTED", out.getvalue())
        self.assertIn("M1_BG_AUTO_START=DISABLED", out.getvalue())

    def test_supported_capability_remains_only_read_only_probe(self):
        seen = []

        def command(*argv):
            seen.append(argv)
            if argv[0] == "loginctl":
                return subprocess.CompletedProcess(argv, 0, stdout="yes\n", stderr="")
            if argv[0] == "systemctl":
                return subprocess.CompletedProcess(argv, 0, stdout="Version=255\n", stderr="")
            self.fail(f"unexpected command: {argv}")

        with mock.patch.object(PROBE.shutil, "which", side_effect=lambda x: "/usr/bin/" + x), \
                mock.patch.object(PROBE, "command", side_effect=command):
            code, output = self.invoke()
        self.assertEqual(code, 0)
        self.assertIn("PASS_CAPABILITY_ONLY", output)
        self.assertIn("M1_BG_DOCKER_ACTION=NONE", output)
        self.assertIn("M1_BG_SUPERVISOR_IMPLEMENTED=NO", output)
        self.assertEqual(len(seen), 2)
        self.assertEqual({x[0] for x in seen}, {"systemctl", "loginctl"})
        self.assertFalse(any(token in {"start", "stop", "enable", "run"} for a in seen for token in a))

    def test_user_linger_no_blocks_even_with_healthy_manager(self):
        def command(*argv):
            value = "no\n" if argv[0] == "loginctl" else "Version=255\n"
            return subprocess.CompletedProcess(argv, 0, stdout=value, stderr="")
        with mock.patch.object(PROBE.shutil, "which", return_value="/usr/bin/tool"), \
                mock.patch.object(PROBE, "command", side_effect=command):
            code, output = self.invoke()
        self.assertEqual(code, 2)
        self.assertIn("USER_LINGER_DISABLED", output)
        self.assertIn("M1_BG_USER_LINGER=DISABLED", output)
        self.assertIn("M1_BG_USER_MANAGER=AVAILABLE", output)
        self.assertIn("M1_BG_LINGER_POLICY_CHANGE=NOT_PERFORMED", output)

    def test_unrecognized_linger_is_distinct_from_disabled(self):
        def command(*argv):
            value = "maybe\n" if argv[0] == "loginctl" else "Version=255\n"
            return subprocess.CompletedProcess(argv, 0, stdout=value, stderr="")
        with mock.patch.object(PROBE.shutil, "which", return_value="/usr/bin/tool"), \
                mock.patch.object(PROBE, "command", side_effect=command):
            code, output = self.invoke()
        self.assertEqual(code, 2)
        self.assertIn("M1_BG_USER_LINGER=UNKNOWN", output)
        self.assertIn("USER_LINGER_RESPONSE_UNRECOGNIZED", output)
        self.assertNotIn("USER_LINGER_DISABLED", output)

    def test_failed_linger_query_is_not_misreported_as_disabled(self):
        def command(*argv):
            if argv[0] == "loginctl":
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unavailable")
            return subprocess.CompletedProcess(argv, 0, stdout="Version=255\n", stderr="")
        with mock.patch.object(PROBE.shutil, "which", return_value="/usr/bin/tool"), \
                mock.patch.object(PROBE, "command", side_effect=command):
            code, output = self.invoke()
        self.assertEqual(code, 2)
        self.assertIn("M1_BG_USER_LINGER=UNKNOWN", output)
        self.assertIn("USER_LINGER_QUERY_FAILED", output)
        self.assertNotIn("USER_LINGER_DISABLED", output)

    def test_dead_user_manager_blocks(self):
        def command(*argv):
            if argv[0] == "loginctl":
                return subprocess.CompletedProcess(argv, 0, stdout="yes\n", stderr="")
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="can't connect")
        with mock.patch.object(PROBE.shutil, "which", return_value="/usr/bin/tool"), \
                mock.patch.object(PROBE, "command", side_effect=command):
            code, output = self.invoke()
        self.assertEqual(code, 2)
        self.assertIn("USER_SERVICE_MANAGER_UNAVAILABLE", output)

    def test_symlink_runtime_dir_blocks_before_any_command(self):
        real = self.runtime
        link = real.parent / "runtime-link"
        link.symlink_to(real, target_is_directory=True)
        with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(link)}), \
                mock.patch.object(PROBE, "command", side_effect=AssertionError("must not execute")):
            rc, out = self.invoke()
        self.assertEqual(rc, 2)
        self.assertIn("XDG_RUNTIME_DIR_UNSAFE_PATH", out)

    def test_world_accessible_runtime_dir_blocks(self):
        self.runtime.chmod(0o755)
        with mock.patch.object(PROBE, "command", side_effect=AssertionError("must not execute")):
            rc, out = self.invoke()
        self.assertEqual(rc, 2)
        self.assertIn("XDG_RUNTIME_DIR_UNSAFE_PERMISSIONS", out)

    def test_missing_tools_block_before_any_inspection(self):
        with mock.patch.object(PROBE.shutil, "which", return_value=None), \
                mock.patch.object(PROBE, "command", side_effect=AssertionError("must not execute")):
            rc, out = self.invoke()
        self.assertEqual(rc, 2)
        self.assertIn("MISSING_SYSTEMD_TOOLS", out)

    def test_command_timeout_blocks_without_mutation(self):
        with mock.patch.object(PROBE.shutil, "which", return_value="/usr/bin/tool"), \
                mock.patch.object(PROBE, "command",
                                  side_effect=subprocess.TimeoutExpired(["loginctl"], 5)):
            rc, out = self.invoke()
        self.assertEqual(rc, 2)
        self.assertIn("USER_SERVICE_INSPECTION_FAILED", out)


if __name__ == "__main__":
    unittest.main()
