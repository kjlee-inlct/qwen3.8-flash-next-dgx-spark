from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "manage-proxy.sh"


class ProxyUnitParsingTests(unittest.TestCase):
    def test_extracts_ports_from_multiple_listen_streams(self) -> None:
        unit = (
            "[Socket]\n"
            "ListenStream=172.17.0.1:8000\n"
            "ListenStream=192.168.0.57:8001\n"
            "NoDelay=true\n"
        )
        command = [
            "awk",
            "-F[=:]",
            '$1=="ListenStream" {print $NF}',
        ]
        result = subprocess.run(command, input=unit, text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.splitlines(), ["8000", "8001"])

    def test_script_keeps_legacy_listen_port_alias(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("--docker-port|--listen-port", script)
        self.assertIn("--lan-address", script)
        self.assertIn("--lan-port", script)

    def test_script_uses_specific_lan_address_not_wildcard(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('LAN address must be a specific non-loopback IPv4 address', script)
        self.assertIn('LAN address is not assigned to this host', script)
        self.assertNotIn("ListenStream=0.0.0.0", script)

    def test_status_uses_user_facing_api_access_wording(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("Qwen API access status", script)
        self.assertIn("Docker-app API ready", script)
        self.assertIn("LAN API ready", script)


if __name__ == "__main__":
    unittest.main()
