from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
INSTALLER = ROOT / "install.sh"


class InstallerOptionParityTests(unittest.TestCase):
    maxDiff = None

    EXPECTED_CLI_FLAGS = {
        "--api-access",
        "--api-docker-port",
        "--api-lan-address",
        "--api-lan-port",
        "--config-override",
        "--dry-run",
        "--help",
        "--lang",
        "--list-backends",
        "--list-models",
        "--migrate-manifest",
        "--model",
        "--model-root",
        "--monitor",
        "--monitor-consecutive",
        "--monitor-free-gate-gib",
        "--monitor-heartbeat",
        "--monitor-min-available-gib",
        "--monitor-min-free-gib",
        "--monitor-min-swap-free-gib",
        "--no-monitor",
        "--no-service",
        "--no-start",
        "--protect",
        "--refresh-profile-defaults",
        "--service",
        "--yes",
    }

    # Explicitly classified command/control flags do not represent a persisted
    # installer setting and therefore do not need a Wizard field.
    CONTROL_OR_INFORMATIONAL_FLAGS = {
        "--help",
        "--list-backends",
        "--list-models",
        "--migrate-manifest",
        "--yes",
    }

    # Known product debt is kept explicit so CI prevents the gap from growing.
    # These are user-facing execution/settings choices that still need a Wizard
    # control in a later phase of the profile-manager work.
    KNOWN_WIZARD_PARITY_DEBT = {
        "--dry-run",
        "--no-start",
        "--refresh-profile-defaults",
    }

    WIZARD_MARKERS = {
        "--lang": "wizard_step 1 6 '언어 선택 / Language'",
        "--model": "wizard_choose_model_profile",
        "--model-root": "wizard_input MODEL_ROOT",
        "--config-override": "wizard_input CONFIG_OVERRIDE",
        "--monitor": "Enable the runtime memory monitor?",
        "--no-monitor": "Enable the runtime memory monitor?",
        "--protect": "Stop the container safely after sustained low memory?",
        "--monitor-min-available-gib": "wizard_input MONITOR_MIN_AVAILABLE_GIB",
        "--monitor-min-free-gib": "wizard_input MONITOR_MIN_FREE_GIB",
        "--monitor-free-gate-gib": "wizard_input MONITOR_FREE_GATE_GIB",
        "--monitor-min-swap-free-gib": "wizard_input MONITOR_MIN_SWAP_FREE_GIB",
        "--monitor-consecutive": "wizard_input MONITOR_CONSECUTIVE",
        "--monitor-heartbeat": "wizard_input MONITOR_HEARTBEAT",
        "--api-access": "wizard_step 5 6 'API and service'",
        "--api-docker-port": "wizard_input API_DOCKER_PORT",
        "--api-lan-address": "wizard_input API_LAN_ADDRESS",
        "--api-lan-port": "wizard_input API_LAN_PORT",
        "--service": "Install a systemd service that starts at boot?",
        "--no-service": "Install a systemd service that starts at boot?",
    }

    def setUp(self) -> None:
        self.installer = INSTALLER.read_text(encoding="utf-8")

    def parser_flags(self) -> set[str]:
        parser = self.installer.split('while [[ $# -gt 0 ]]; do', 1)[1].split("\ndone", 1)[0]
        return set(re.findall(r"--[a-z][a-z0-9-]*(?=[)|])", parser))

    def test_cli_flag_inventory_is_explicit(self) -> None:
        self.assertEqual(self.parser_flags(), self.EXPECTED_CLI_FLAGS)

    def test_help_mentions_every_supported_long_flag(self) -> None:
        usage = self.installer.split("usage() {", 1)[1].split("\n}", 1)[0]
        for flag in sorted(self.EXPECTED_CLI_FLAGS - {"--help"}):
            with self.subTest(flag=flag):
                self.assertIn(flag, usage)

    def test_wizard_parity_debt_is_bounded_and_every_other_setting_has_a_field(self) -> None:
        user_setting_flags = self.EXPECTED_CLI_FLAGS - self.CONTROL_OR_INFORMATIONAL_FLAGS
        covered = set(self.WIZARD_MARKERS)
        self.assertEqual(user_setting_flags - covered, self.KNOWN_WIZARD_PARITY_DEBT)
        self.assertEqual(covered & self.KNOWN_WIZARD_PARITY_DEBT, set())

        for flag, marker in sorted(self.WIZARD_MARKERS.items()):
            with self.subTest(flag=flag):
                self.assertIn(marker, self.installer)


if __name__ == "__main__":
    unittest.main()
