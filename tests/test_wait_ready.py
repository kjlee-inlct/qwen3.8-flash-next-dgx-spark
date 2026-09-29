from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "runtime" / "wait-ready.sh"


class WaitReadyDiagnosticsTests(unittest.TestCase):
    def test_failure_path_prints_root_cause_and_large_log_tail(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('FAILURE_LOG_TAIL="${FAILURE_LOG_TAIL:-300}"', script)
        self.assertIn("print_failure_diagnostics()", script)
        self.assertIn("ROOT CAUSE CANDIDATES", script)
        self.assertIn("LAST %s LOG LINES", script)
        self.assertIn("ValueError", script)
        self.assertIn("RuntimeError", script)
        self.assertIn("weight_scale", script)
        self.assertIn("scale_inv", script)

    def test_stopped_and_timeout_paths_use_failure_diagnostics(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertGreaterEqual(script.count('print_failure_diagnostics "${CONTAINER}"'), 2)


    def test_wait_ready_reports_container_disappearance_events(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("seen_container=1", script)
        self.assertIn("CONTAINER DISAPPEARED", script)
        self.assertIn("print_container_events", script)
        self.assertIn("docker events", script)
        self.assertIn('--filter "container=${CONTAINER}"', script)



    def test_managed_restart_waits_through_stopped_container(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            counter = root / "inspect-count"

            (bin_dir / "docker").write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    set -e
                    if [[ "$1" == inspect && "$2" != --format ]]; then
                      exit 0
                    fi
                    if [[ "$1" == inspect && "$2" == --format ]]; then
                      count=0
                      [[ -r "{counter}" ]] && count="$(cat "{counter}")"
                      count=$((count + 1))
                      printf '%s' "$count" >"{counter}"
                      if (( count == 1 )); then
                        printf 'exited\\n'
                      else
                        printf 'running\\n'
                      fi
                      exit 0
                    fi
                    if [[ "$1" == logs || "$1" == events ]]; then
                      exit 0
                    fi
                    exit 0
                    """
                ),
                encoding="utf-8",
            )
            (bin_dir / "systemctl").write_text(
                "#!/usr/bin/env bash\nprintf 'active\\n'\n",
                encoding="utf-8",
            )
            (bin_dir / "curl").write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    case "$*" in
                      *"/v1/models"*) printf '{"object":"list","data":[{"id":"test/model"}]}\\n' ;;
                      *) exit 0 ;;
                    esac
                    """
                ),
                encoding="utf-8",
            )
            for path in bin_dir.iterdir():
                path.chmod(0o755)

            result = subprocess.run(
                [
                    "bash",
                    str(SCRIPT),
                    "--container",
                    "qwen38-flash-next",
                    "--model",
                    "test/model",
                    "--timeout",
                    "5",
                    "--interval",
                    "1",
                ],
                env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("managed-service=replacing", result.stdout)
            self.assertIn("READY after", result.stdout)

    def test_wait_ready_rejects_missing_initial_container(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("container not found before readiness wait", script)
        self.assertIn('docker inspect "${CONTAINER}"', script)
        self.assertIn("seen_container=1", script)


if __name__ == "__main__":
    unittest.main()
