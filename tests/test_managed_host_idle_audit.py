"""Synthetic-only full host-idle audit for the post-benchmark Wizard."""
from __future__ import annotations

import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/diagnostics/verify-managed-idle.py"
SPEC = importlib.util.spec_from_file_location("managed_host_idle", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class HostIdleTests(unittest.TestCase):
    def fake_shell(self, *argv: str) -> str:
        if argv[:2] == ("systemctl", "show"):
            return "LoadState=not-found\nActiveState=inactive\nUnitFileState=\n"
        if argv[:3] == ("ss", "-H", "-ltn"):
            return "LISTEN 0 100 127.0.0.1:22 0.0.0.0:*\n"
        if argv[:2] == ("docker", "ps"):
            return "other-service\n"
        raise AssertionError(f"Unexpected command: {argv}")

    def test_idle_systemd_and_configured_ports_and_no_project_docker(self):
        with mock.patch.object(AUDIT, "run", side_effect=self.fake_shell):
            output = io.StringIO()
            with redirect_stdout(output):
                AUDIT.systemd()
                AUDIT.listeners({8000, 8001, 8888, 18888, 18889})
                AUDIT.docker()
        self.assertIn("MANAGED_IDLE_SYSTEMD=NO_RUNNING_OR_BOOT_ENABLED_UNITS", output.getvalue())
        self.assertIn("MANAGED_IDLE_MANAGED_PORTS=NO_LISTENERS", output.getvalue())

    def test_active_or_boot_enabled_proxy_is_not_idle(self):
        for active, boot in (("active", "enabled"), ("inactive", "enabled"),
                             ("active", "disabled"), ("failed", "enabled")):
            with self.subTest(active=active, boot=boot):
                def fake(*argv: str) -> str:
                    return f"LoadState=loaded\nActiveState={active}\nUnitFileState={boot}\n"
                with mock.patch.object(AUDIT, "run", side_effect=fake):
                    with self.assertRaises(AUDIT.NotIdle):
                        AUDIT.systemd()

    def test_still_listening_docker_or_lan_api_blocks(self):
        for ipport in ("172.17.0.1:8000", "10.221.50.65:8000",
                       "127.0.0.1:8888", "127.0.0.1:18889"):
            with self.subTest(ipport=ipport):
                with mock.patch.object(AUDIT, "run", return_value=
                                       f"LISTEN 0 4096 {ipport} 0.0.0.0:*\n"):
                    with self.assertRaisesRegex(AUDIT.NotIdle, "PORT_STILL_LISTENING"):
                        AUDIT.listeners({8000, 8888, 18889})

    def test_any_running_qwen38_project_container_blocks(self):
        with mock.patch.object(AUDIT, "run",
                               return_value="other-service\nqwen38-flash-next\n"):
            with self.assertRaisesRegex(AUDIT.NotIdle, "PROJECT_DOCKER_RUNNING"):
                AUDIT.docker()

    def test_manifest_policy_precedes_probing_host_services(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            state = home / "state"
            state.mkdir()
            (state / "install.env").write_text("synthetic")
            with mock.patch.object(AUDIT, "parse_install", return_value={
                    "PHASE": "complete", "MODEL_PROFILE": "orcarouter",
                    "API_ACCESS_MODE": "lan", "SERVICE_ENABLED": "1",
                    "API_DOCKER_PORT": "8000", "API_LAN_PORT": "8001"}), \
                 mock.patch.object(AUDIT, "systemd") as systemd:
                with self.assertRaisesRegex(AUDIT.NotIdle, "MANIFEST_STILL_EXPOSES"):
                    AUDIT.verify(home, state)
                systemd.assert_not_called()

    def test_idle_check_keeps_all_model_and_evidence_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            state = home / "state"
            state.mkdir()
            manifest = state / "install.env"
            manifest.write_text("synthetic")
            before = manifest.read_bytes()
            with mock.patch.object(AUDIT, "parse_install", return_value={
                    "PHASE": "complete", "MODEL_PROFILE": "orcarouter",
                    "API_ACCESS_MODE": "local", "SERVICE_ENABLED": "0",
                    "API_DOCKER_PORT": "8000", "API_LAN_PORT": "8001",
                    "PROXY_PORT": "8000"}), \
                 mock.patch.object(AUDIT, "run", side_effect=self.fake_shell):
                output = io.StringIO()
                with redirect_stdout(output):
                    AUDIT.verify(home, state)
                self.assertIn("MANAGED_IDLE_AUDIT=PASS", output.getvalue())
                self.assertEqual(manifest.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
