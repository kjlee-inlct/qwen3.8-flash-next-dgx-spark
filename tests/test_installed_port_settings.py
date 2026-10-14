"""Installed API/port configuration must remain reachable from modular Wizard.

No Docker/GPU/systemd effects: synthetic HOME manifests and --dry-run.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install.sh"
MENU = ROOT / "scripts/wizard/runtime-menu.sh"
UI = ROOT / "scripts/lib/wizard-ui.sh"


def manifest_for(home: Path, phase: str = "complete") -> Path:
    state = home / "state/qwen38-spark"
    state.mkdir(parents=True)
    path = state / "install.env"
    rows = {
        "SCHEMA_VERSION": "4",
        "PHASE": phase,
        "INSTALL_ROOT": str(ROOT),
        "MODEL_PROFILE": "orcarouter",
        "MODEL_REPO": "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
        "MODEL_REVISION": "c1209bda15a6bbc4c68b585e93d40c0d85f50306",
        "MODEL_DIR": str(home / "models/qwen3.8-flash-next-orcarouter"),
        "MODEL_OWNED": "0",
        "SWAP_FILE": "/swap-ple.img",
        "SWAP_OWNED": "0",
        "VLLM_IMAGE": "vllm-skinny-tp1:v1",
        "IMAGE_OWNED": "0",
        "SERVED_NAME": "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
        "CONTAINER_NAME": "qwen38-flash-next",
        "CONFIG_OVERRIDE": "",
        "CONFIG_OWNED": "0",
        "MONITOR_PROTECT": "1",
        "MONITOR_ENABLED": "1",
        "MONITOR_MIN_AVAILABLE_GIB": "7",
        "MONITOR_MIN_FREE_GIB": "3",
        "MONITOR_FREE_GATE_GIB": "11",
        "MONITOR_MIN_SWAP_FREE_GIB": "9",
        "MONITOR_CONSECUTIVE": "6",
        "MONITOR_HEARTBEAT": "30",
        "API_ACCESS_MODE": "lan",
        "API_DOCKER_PORT": "8000",
        "API_LAN_ADDRESS": "192.0.2.10",
        "API_LAN_PORT": "8001",
        "PROXY_ENABLED": "1",
        "PROXY_OWNED": "1",
        "PROXY_PORT": "8000",
        "SERVICE_ENABLED": "1",
        "SERVICE_OWNED": "1",
        "SERVICE_UNIT": "qwen38-flash-next.service",
        "UI_LANG": "en",
    }
    path.write_text("".join(f"{k}={v}\n" for k, v in rows.items()), encoding="utf-8")
    return path


class InstalledPortSettingsTests(unittest.TestCase):
    def installer(self, home: Path, args: list[str], answers: str = ""):
        env = {**os.environ, "HOME": str(home), "XDG_STATE_HOME": str(home / "state")}
        return subprocess.run(["/bin/bash", str(INSTALL), *args], cwd=ROOT, env=env,
                              input=answers, capture_output=True, text=True,
                              check=False, timeout=30)

    def test_manage_settings_dry_run_requires_completed_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            r = self.installer(home, ["--manage-settings", "--lang", "en", "--dry-run"])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("requires an existing managed installation", r.stderr)
            self.assertFalse((home / "state").exists())
            manifest = manifest_for(home, phase="weights_ready")
            original = manifest.read_bytes()
            r = self.installer(home, ["--manage-settings", "--lang", "en", "--dry-run"])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("requires PHASE=complete", r.stderr)
            self.assertEqual(manifest.read_bytes(), original)

    def test_manage_settings_refuses_model_switch_yes_or_cli_port_bypass(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            manifest = manifest_for(home)
            original = manifest.read_bytes()
            for extra in (["--yes"], ["--model", "nvidia"],
                          ["--api-lan-port", "9000"], ["--config-override", "/tmp/x"]):
                with self.subTest(extra=extra):
                    r = self.installer(home, ["--manage-settings", "--dry-run",
                                              "--lang", "en", *extra])
                    self.assertNotEqual(r.returncode, 0)
                    self.assertIn("cannot combine", r.stderr)
                    self.assertEqual(manifest.read_bytes(), original)

    def test_port_settings_are_reviewed_without_download_or_host_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            manifest = manifest_for(home)
            original = manifest.read_bytes()
            # config=keep, monitor=yes, protect=yes, customize=no;
            # LAN=existing, Docker port=8000, IP=192.0.2.10,
            # NEW LAN port=8007, boot service=yes, final continue=yes.
            answers = "1\n\n\nn\n\n\n8007\n\ny\n"
            r = self.installer(home, ["--manage-settings", "--lang", "en",
                                      "--dry-run"], answers)
            self.assertEqual(r.returncode, 0, r.stderr + "\n" + r.stdout[-1800:])
            self.assertIn("LAN: 192.0.2.10:8007", r.stdout)
            self.assertIn("Docker apps: 8000", r.stdout)
            self.assertIn("profile     : orcarouter", r.stdout)
            self.assertIn("DRY-RUN complete", r.stdout)
            self.assertEqual(manifest.read_bytes(), original)
            self.assertFalse((home / "models").exists())
            self.assertFalse((home / "state/qwen38-spark/operation.lock").exists())

    def test_modular_runtime_menu_routes_to_existing_installer_only_for_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            stub = home / "install.sh"
            stub.write_text("#!/bin/bash\nprintf 'INSTALLED_SETTINGS_INVOKED=%s\\n' \"$*\"\n")
            for state, phase, expected in (
                ("valid", "complete", True),
                ("valid", "weights_ready", False),
                ("missing", "", False),
                ("invalid", "", False),
            ):
                with self.subTest(state=state, phase=phase):
                    code = "\n".join([
                        "set -Eeuo pipefail",
                        f"ROOT_DIR={str(home)!r}",
                        "UI_LANG=en",
                        f"source {str(UI)!r}",
                        f"source {str(MENU)!r}",
                        f"wizard_read_manifest() {{ WIZARD_MANIFEST_STATE={state}; WIZARD_PHASE={phase}; }}",
                        "wizard_runtime_menu",
                    ])
                    result = subprocess.run(["/bin/bash", "-c", code], input="4\n0\n",
                                            cwd=ROOT, capture_output=True, text=True,
                                            timeout=10, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual("INSTALLED_SETTINGS_INVOKED=--lang en --manage-settings"
                                     in result.stdout, expected)
                    self.assertIn("API access / Docker & LAN ports", result.stdout)


if __name__ == "__main__":
    unittest.main()
