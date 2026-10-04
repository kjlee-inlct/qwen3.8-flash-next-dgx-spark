from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "runtime" / "wait-runtime-age.sh"
WRAPPER = ROOT / "scripts" / "wait-runtime-age.sh"
DOC = ROOT / "scripts" / "WAITERS.md"


class WaitRuntimeAgeTests(unittest.TestCase):
    def test_operator_wrapper_targets_canonical_runtime_helper(self) -> None:
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(WRAPPER.is_file())
        wrapper = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("runtime/wait-runtime-age.sh", wrapper)

    def test_waiter_pins_container_identity_and_start_time(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("initial_id", script)
        self.assertIn("initial_started", script)
        self.assertIn("container replaced while waiting", script)
        self.assertIn("container StartedAt changed while waiting", script)
        self.assertIn("container stopped while waiting", script)

    def test_waiter_returns_immediately_for_old_enough_container(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            (bin_dir / "docker").write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    if [[ "$1" == inspect ]]; then
                      printf 'aaaaaaaa running 2020-01-01T00:00:00Z\\n'
                      exit 0
                    fi
                    exit 1
                    """
                ),
                encoding="utf-8",
            )
            (bin_dir / "docker").chmod(0o755)

            result = subprocess.run(
                ["bash", str(SCRIPT), "--min-age", "1"],
                env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("WAIT_RUNTIME_AGE_READY", result.stdout)

    def test_waiter_rejects_container_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            counter = root / "inspect-count"

            (bin_dir / "docker").write_text(
                textwrap.dedent(
                    f"""\
                    #!/usr/bin/env bash
                    if [[ "$1" == inspect ]]; then
                      count=0
                      [[ -r "{counter}" ]] && count="$(cat "{counter}")"
                      count=$((count + 1))
                      printf '%s' "$count" >"{counter}"
                      if (( count <= 2 )); then
                        printf 'aaaaaaaa running 1970-01-01T00:01:40Z\\n'
                      else
                        printf 'bbbbbbbb running 1970-01-01T00:01:40Z\\n'
                      fi
                      exit 0
                    fi
                    exit 1
                    """
                ),
                encoding="utf-8",
            )
            (bin_dir / "date").write_text(
                "#!/usr/bin/env bash\nprintf '100\\n'\n",
                encoding="utf-8",
            )
            (bin_dir / "sleep").write_text(
                "#!/usr/bin/env bash\nexit 0\n",
                encoding="utf-8",
            )
            for path in bin_dir.iterdir():
                path.chmod(0o755)

            result = subprocess.run(
                [
                    "bash",
                    str(SCRIPT),
                    "--min-age",
                    "10",
                    "--interval",
                    "1",
                    "--report-interval",
                    "1",
                ],
                env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("container replaced while waiting", result.stderr)

    def test_waiter_definitions_are_documented(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        self.assertIn("wait-ready.sh", text)
        self.assertIn("wait-runtime-age.sh", text)
        self.assertIn("--min-age 2700", text)
        self.assertIn("container replacement", text)


if __name__ == "__main__":
    unittest.main()
