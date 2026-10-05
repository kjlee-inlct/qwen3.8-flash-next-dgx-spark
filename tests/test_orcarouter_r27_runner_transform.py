import pathlib
import re
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
RUNNER = REPO / "scripts/benchmark/run-orcarouter-r27-linear-boundary.sh"
R24 = REPO / "scripts/benchmark/run-orcarouter-hybrid-r24-kv16-rm-mitigation.sh"


class R27RunnerTransformTest(unittest.TestCase):
    def test_embedded_transform_rewrites_all_rm_probe_definitions(self) -> None:
        runner = RUNNER.read_text(encoding="utf-8")
        matches = re.findall(
            r"python3 - \"\$\{R24_HARNESS\}\" \"\$\{TMP_HARNESS\}\" "
            r"\"\$\{EXPERIMENT_CONTAINER\}\" <<'PY'\n(.*?)\nPY\n",
            runner,
            flags=re.DOTALL,
        )
        self.assertEqual(len(matches), 1, "R27 embedded harness transform not found exactly once")

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            transform = root / "transform.py"
            rendered = root / "r27-rendered.sh"
            transform.write_text(matches[0] + "\n", encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    str(transform),
                    str(R24),
                    str(rendered),
                    "qwen38-hybrid-r27-linear-marker",
                ],
                check=True,
                text=True,
                capture_output=True,
            )

            text = rendered.read_text(encoding="utf-8")
            self.assertIn(
                'SCRIPT_ROOT="${ORCA_R27_SCRIPT_ROOT:?ORCA_R27_SCRIPT_ROOT required}"',
                text,
            )
            self.assertIn(
                'EXPERIMENT_CONTAINER="qwen38-hybrid-r27-linear-marker"',
                text,
            )
            self.assertIn('GROUP="r27_rm"', text)
            self.assertEqual(text.count("r27_rm/"), 4)
            self.assertNotIn("r24_rm/", text)
            self.assertNotIn('GROUP="r24_rm"', text)


if __name__ == "__main__":
    unittest.main()
