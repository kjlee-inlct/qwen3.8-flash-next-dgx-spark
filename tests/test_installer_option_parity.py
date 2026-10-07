from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
INSTALLER = ROOT / "install.sh"
COMPLETED_MANAGER = ROOT / "scripts" / "lib" / "install-completed-manager.sh"
OPTION_REGISTRY = ROOT / "scripts" / "lib" / "install-options.sh"


class InstallerOptionParityTests(unittest.TestCase):
    maxDiff = None

    # The registry owns option identity/classification. This map intentionally
    # owns only the UI evidence for each logical user-facing setting.
    WIZARD_MARKERS = {
        "language": "wizard_step 1 6 '언어 선택 / Language'",
        "profile": "wizard_choose_model_profile",
        "model_root": "wizard_input MODEL_ROOT",
        "config_override": "wizard_input CONFIG_OVERRIDE",
        "monitor_mode": "Enable the runtime memory monitor?",
        "monitor_min_available": "wizard_input MONITOR_MIN_AVAILABLE_GIB",
        "monitor_min_free": "wizard_input MONITOR_MIN_FREE_GIB",
        "monitor_free_gate": "wizard_input MONITOR_FREE_GATE_GIB",
        "monitor_min_swap_free": "wizard_input MONITOR_MIN_SWAP_FREE_GIB",
        "monitor_consecutive": "wizard_input MONITOR_CONSECUTIVE",
        "monitor_heartbeat": "wizard_input MONITOR_HEARTBEAT",
        "api_access": "wizard_step 5 6 'API and service'",
        "api_docker_port": "wizard_input API_DOCKER_PORT",
        "api_lan_address": "wizard_input API_LAN_ADDRESS",
        "api_lan_port": "wizard_input API_LAN_PORT",
        "service_mode": "Install a systemd service that starts at boot?",
        "dry_run": "Apply these settings after the final plan review?",
        "start_policy": "Restart the runtime now to apply runtime settings?",
        "refresh_profile_defaults": "REFRESH_PROFILE_DEFAULTS=1",
    }

    def setUp(self) -> None:
        self.installer = INSTALLER.read_text(encoding="utf-8")
        self.wizard_surface = (
            self.installer
            + "\n"
            + COMPLETED_MANAGER.read_text(encoding="utf-8")
        )
        self.registry = self.load_registry()

    def load_registry(self) -> list[dict[str, str]]:
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; install_option_registry',
                "bash",
                str(OPTION_REGISTRY),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        rows: list[dict[str, str]] = []
        for line in result.stdout.splitlines():
            fields = line.split("\t")
            self.assertEqual(len(fields), 5, line)
            option_id, option_class, wizard, usage, flags = fields
            rows.append(
                {
                    "id": option_id,
                    "class": option_class,
                    "wizard": wizard,
                    "usage": usage,
                    "flags": flags,
                }
            )
        return rows

    def parser_flags(self) -> set[str]:
        parser = self.installer.split(
            'while [[ $# -gt 0 ]]; do',
            1,
        )[1].split("\ndone", 1)[0]
        return set(re.findall(r"--[a-z][a-z0-9-]*(?=[)|])", parser))

    def registry_flags(self) -> set[str]:
        result: set[str] = set()
        for row in self.registry:
            result.update(flag for flag in row["flags"].split(",") if flag)
        return result

    def test_option_registry_is_well_formed_and_unique(self) -> None:
        ids = [row["id"] for row in self.registry]
        self.assertEqual(len(ids), len(set(ids)))

        all_flags: list[str] = []
        for row in self.registry:
            self.assertIn(
                row["class"],
                {"setting", "informational", "maintenance", "control"},
            )
            self.assertIn(row["wizard"], {"yes", "no"})
            self.assertTrue(row["usage"].startswith("["))
            self.assertTrue(row["usage"].endswith("]"))
            flags = [flag for flag in row["flags"].split(",") if flag]
            self.assertTrue(flags)
            self.assertTrue(all(flag.startswith("--") for flag in flags))
            all_flags.extend(flags)

        self.assertEqual(len(all_flags), len(set(all_flags)))

    def test_parser_flags_match_canonical_registry(self) -> None:
        self.assertEqual(self.parser_flags(), self.registry_flags())

    def test_help_is_rendered_from_registry_and_mentions_every_option(self) -> None:
        self.assertIn("install_option_usage", self.installer)
        result = subprocess.run(
            [str(INSTALLER), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        for row in self.registry:
            with self.subTest(option=row["id"]):
                self.assertIn(row["usage"], result.stdout)

    def test_wizard_setting_contract_has_no_parity_debt(self) -> None:
        setting_rows = {
            row["id"]: row
            for row in self.registry
            if row["class"] == "setting"
        }
        nonsetting_rows = {
            row["id"]: row
            for row in self.registry
            if row["class"] != "setting"
        }

        self.assertEqual(set(self.WIZARD_MARKERS), set(setting_rows))
        self.assertTrue(all(row["wizard"] == "yes" for row in setting_rows.values()))
        self.assertTrue(all(row["wizard"] == "no" for row in nonsetting_rows.values()))

        for option_id, marker in sorted(self.WIZARD_MARKERS.items()):
            with self.subTest(option=option_id):
                self.assertIn(marker, self.wizard_surface)


if __name__ == "__main__":
    unittest.main()
