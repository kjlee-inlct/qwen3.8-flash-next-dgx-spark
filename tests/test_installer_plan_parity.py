from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
PLAN_HELPER = ROOT / "scripts" / "lib" / "install-plan.sh"


class InstallerPlanParityTests(unittest.TestCase):
    PLAN_KEYS = {
        "model",
        "profile",
        "switch",
        "storage root",
        "directory",
        "revision",
        "image",
        "config",
        "PLE swap",
        "protection",
        "monitor",
        "API access",
        "service",
    }

    def run_installer(
        self,
        home: Path,
        args: list[str],
        answers: str = "",
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(ROOT / "install.sh"), *args],
            cwd=ROOT,
            env={
                **os.environ,
                "HOME": str(home),
                "XDG_STATE_HOME": str(home / "state"),
            },
            input=answers,
            text=True,
            capture_output=True,
            check=False,
        )

    def extract_plan(self, output: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for raw_line in output.splitlines():
            if ":" not in raw_line:
                continue
            key, value = raw_line.strip().split(":", 1)
            key = key.strip()
            if key in self.PLAN_KEYS:
                result[key] = value.strip()
        return result

    def write_complete_manifest(self, home: Path) -> Path:
        state = home / "state" / "qwen38-spark"
        state.mkdir(parents=True)
        manifest = state / "install.env"
        manifest.write_text(
            "\n".join(
                [
                    "SCHEMA_VERSION=4",
                    "PHASE=complete",
                    f"INSTALL_ROOT={ROOT}",
                    "MODEL_PROFILE=orcarouter",
                    "MODEL_REPO=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "MODEL_REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306",
                    f"MODEL_DIR={home / 'models/qwen3.8-flash-next-orcarouter'}",
                    "MODEL_OWNED=0",
                    "SWAP_FILE=/swap-ple.img",
                    "SWAP_OWNED=0",
                    "VLLM_IMAGE=vllm-skinny-tp1:v1",
                    "IMAGE_OWNED=0",
                    "SERVED_NAME=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "CONTAINER_NAME=qwen38-flash-next",
                    "CONFIG_OVERRIDE=",
                    "CONFIG_OWNED=0",
                    "MONITOR_PROTECT=1",
                    "MONITOR_ENABLED=1",
                    "MONITOR_MIN_AVAILABLE_GIB=7",
                    "MONITOR_MIN_FREE_GIB=3",
                    "MONITOR_FREE_GATE_GIB=11",
                    "MONITOR_MIN_SWAP_FREE_GIB=9",
                    "MONITOR_CONSECUTIVE=6",
                    "MONITOR_HEARTBEAT=30",
                    "API_ACCESS_MODE=lan",
                    "API_DOCKER_PORT=8000",
                    "API_LAN_ADDRESS=192.0.2.10",
                    "API_LAN_PORT=8001",
                    "PROXY_ENABLED=1",
                    "PROXY_OWNED=1",
                    "PROXY_PORT=8000",
                    "SERVICE_ENABLED=1",
                    "SERVICE_OWNED=1",
                    "SERVICE_UNIT=qwen38-flash-next.service",
                    "UI_LANG=en",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return manifest

    def test_plan_helper_normalizes_and_reapplies_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            script = f'''
set -euo pipefail
validate_monitor_settings() {{ :; }}
validate_api_access_settings() {{ PROXY_ENABLED=1; PROXY_PORT="${{API_DOCKER_PORT}}"; }}
MODEL_PROFILE=orcarouter
REPO=repo/example
REVISION=rev1
MODEL_ROOT_SOURCE=custom
MODEL_ROOT='~/models/../models'
MODEL_DIR='~/models/model-a/../model-a'
IMAGE=image:test
SERVED_NAME=served/example
CONFIG_OVERRIDE='~/cfg/../config.json'
PROFILE_CONFIG_OVERRIDE=0
SWAP_FILE=/swap-ple.img
MONITOR_ENABLED=1
MONITOR_PROTECT=0
MONITOR_MIN_AVAILABLE_GIB=7
MONITOR_MIN_FREE_GIB=3
MONITOR_FREE_GATE_GIB=11
MONITOR_MIN_SWAP_FREE_GIB=9
MONITOR_CONSECUTIVE=6
MONITOR_HEARTBEAT=30
API_ACCESS_MODE=lan
API_DOCKER_PORT=8000
API_LAN_ADDRESS=192.0.2.10
API_LAN_PORT=8001
PROXY_ENABLED=0
PROXY_PORT=9999
SERVICE_ENABLED=1
PROFILE_SWITCH=0
SWITCH_FROM_PROFILE=''
START=0
DRY_RUN=1
REFRESH_PROFILE_DEFAULTS=0
PROFILE_LOCAL_BUILD=0
UI_LANG=en
source "{PLAN_HELPER}"
install_plan_finalize
printf '%s\n' \
  "$PLAN_SCHEMA_VERSION" \
  "$PLAN_MODEL_ROOT" \
  "$PLAN_MODEL_DIR" \
  "$PLAN_CONFIG_OVERRIDE" \
  "$PLAN_API_ACCESS_MODE" \
  "$PLAN_PROXY_ENABLED" \
  "$PLAN_PROXY_PORT" \
  "$MODEL_ROOT" \
  "$MODEL_DIR" \
  "$CONFIG_OVERRIDE"
'''
            result = subprocess.run(
                ["bash", "-lc", script],
                cwd=ROOT,
                env={**os.environ, "HOME": str(home)},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            lines = result.stdout.splitlines()
            self.assertEqual(lines[0], "1")
            self.assertEqual(lines[1], str(home / "models"))
            self.assertEqual(lines[2], str(home / "models/model-a"))
            self.assertEqual(lines[3], str(home / "config.json"))
            self.assertEqual(lines[4:7], ["lan", "1", "8000"])
            self.assertEqual(lines[7], lines[1])
            self.assertEqual(lines[8], lines[2])
            self.assertEqual(lines[9], lines[3])

    def test_fresh_cli_and_wizard_build_same_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            model_root = ROOT / "models"

            cli = self.run_installer(
                home,
                [
                    "--lang",
                    "en",
                    "--yes",
                    "--no-start",
                    "--dry-run",
                    "--model",
                    "orcarouter",
                    "--model-root",
                    str(model_root),
                    "--monitor",
                    "--api-access",
                    "docker",
                    "--api-docker-port",
                    "8000",
                    "--service",
                ],
            )
            wizard = self.run_installer(
                home,
                ["--lang", "en", "--no-start", "--dry-run"],
                answers="\n" * 10,
            )

            self.assertEqual(cli.returncode, 0, cli.stderr)
            self.assertEqual(wizard.returncode, 0, wizard.stderr)
            cli_plan = self.extract_plan(cli.stdout)
            wizard_plan = self.extract_plan(wizard.stdout)
            self.assertEqual(cli_plan, wizard_plan)
            self.assertEqual(cli_plan["profile"], "orcarouter")
            self.assertIn("Docker apps: 8000", cli_plan["API access"])

    def test_completed_switch_cli_and_wizard_build_same_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            manifest = self.write_complete_manifest(home)
            before = manifest.read_bytes()

            cli = self.run_installer(
                home,
                [
                    "--lang",
                    "en",
                    "--yes",
                    "--model",
                    "nvidia",
                    "--no-start",
                    "--dry-run",
                ],
            )
            wizard = self.run_installer(
                home,
                ["--lang", "en", "--no-start", "--dry-run"],
                answers="1\n2\ny\n",
            )

            self.assertEqual(cli.returncode, 0, cli.stderr)
            self.assertEqual(wizard.returncode, 0, wizard.stderr)
            cli_plan = self.extract_plan(cli.stdout)
            wizard_plan = self.extract_plan(wizard.stdout)
            self.assertEqual(cli_plan, wizard_plan)
            self.assertEqual(cli_plan["profile"], "nvidia")
            self.assertEqual(cli_plan["switch"], "orcarouter -> nvidia")
            self.assertIn("LAN: 192.0.2.10:8001", cli_plan["API access"])
            self.assertEqual(manifest.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()