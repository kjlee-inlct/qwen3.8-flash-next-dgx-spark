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
            value = "maybe\n" if argv[0] == "loginctl" else "Version=255\\n"
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
