from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
MONITOR = ROOT / "scripts" / "runtime" / "monitor-runtime.sh"


class RuntimeMonitorTests(unittest.TestCase):
    def test_cma_dominated_free_memory_triggers_host_protection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            state_home = root / "state"
            bin_dir.mkdir()

            docker_log = root / "docker.log"
            stop_marker = root / "docker-stopped"
            fake_docker = bin_dir / "docker"
            fake_docker.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "$FAKE_DOCKER_LOG"
case "${1:-}" in
  inspect)
    if [[ "${2:-}" == "-f" ]]; then
      printf 'true\\n'
    elif [[ "${2:-}" == "--format" ]]; then
      printf '%064d\\n' 0
    fi
    ;;
  logs)
    ;;
  stop)
    : > "$FAKE_DOCKER_STOP_MARKER"
    ;;
  *)
    ;;
esac
""",
                encoding="utf-8",
            )
            fake_docker.chmod(fake_docker.stat().st_mode | stat.S_IXUSR)

            # Reproduce the failure signature: raw MemFree still looks large,
            # but almost all of it is CMA-reserved and therefore not a safe
            # margin for NVIDIA system-page allocation.
            meminfo = root / "meminfo"
            meminfo.write_text(
                "\n".join(
                    [
                        "MemTotal:       127506432 kB",
                        "MemFree:          9437184 kB",   # 9.0 GiB
                        "MemAvailable:     9437184 kB",   # 9.0 GiB
                        "CmaFree:           8912896 kB",   # 8.5 GiB
                        "SwapFree:        104857600 kB",   # 100 GiB
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    str(MONITOR),
                    "--container",
                    "qwen38-flash-next",
                    "--protect",
                    "--consecutive",
                    "1",
                    "--interval",
                    "1",
                    "--heartbeat",
                    "0",
                ],
                cwd=ROOT,
                env={
                    **os.environ,
                    "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
                    "XDG_STATE_HOME": str(state_home),
                    "QWEN38_MEMINFO_PATH": str(meminfo),
                    "FAKE_DOCKER_LOG": str(docker_log),
                    "FAKE_DOCKER_STOP_MARKER": str(stop_marker),
                },
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            output = result.stdout + result.stderr
            self.assertIn("noncma_available=512MiB", output)
            self.assertIn("noncmafree=512MiB", output)
            self.assertIn("PROTECT stopping qwen38-flash-next", output)
            self.assertTrue(stop_marker.exists(), docker_log.read_text(encoding="utf-8"))
            stop_reason = state_home / "qwen38-spark" / "runtime-stop.env"
            self.assertTrue(stop_reason.is_file())
            self.assertIn("STOP_REASON=memory-protection", stop_reason.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
