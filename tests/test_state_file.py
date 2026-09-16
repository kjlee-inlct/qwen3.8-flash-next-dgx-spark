from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
PARSER = ROOT / "scripts" / "state_file.py"


class StateFileParserTests(unittest.TestCase):
    def run_parser(self, schema: str, text: str) -> subprocess.CompletedProcess[bytes]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.env"
            path.write_text(text, encoding="utf-8")
            return subprocess.run(
                ["python3", str(PARSER), schema, str(path)],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def test_update_state_emits_nul_delimited_values(self) -> None:
        result = self.run_parser(
            "update",
            "\n".join(
                [
                    "UPDATE_SCHEMA_VERSION=1",
                    "UPDATE_STATE=staged",
                    "TARGET_RELEASE=" + "2" * 40,
                    "OLD_CURRENT_RELEASE=" + "1" * 40,
                    "OLD_PREVIOUS_RELEASE='',",
                    "UPDATED_AT=2026-09-16T01:00:00Z",
                    "",
                ]
            ).replace("OLD_PREVIOUS_RELEASE='',", "OLD_PREVIOUS_RELEASE=''"),
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        fields = result.stdout.split(b"\0")
        self.assertIn(b"UPDATE_STATE", fields)
        self.assertIn(b"staged", fields)
        self.assertIn(b"OLD_PREVIOUS_RELEASE", fields)

    def test_shell_command_substitution_is_rejected_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "executed"
            state = root / "state.env"
            state.write_text(
                "\n".join(
                    [
                        "UPDATE_SCHEMA_VERSION=1",
                        "UPDATE_STATE=staged",
                        "TARGET_RELEASE=$(touch " + str(marker) + ")",
                        "OLD_CURRENT_RELEASE=",
                        "OLD_PREVIOUS_RELEASE=",
                        "UPDATED_AT=2026-09-16T01:00:00Z",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                ["python3", str(PARSER), "update", str(state)],
                cwd=ROOT,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())

    def test_duplicate_and_unknown_keys_are_rejected(self) -> None:
        base = [
            "UPDATE_SCHEMA_VERSION=1",
            "UPDATE_STATE=staged",
            "TARGET_RELEASE=" + "2" * 40,
            "OLD_CURRENT_RELEASE=",
            "OLD_PREVIOUS_RELEASE=",
            "UPDATED_AT=2026-09-16T01:00:00Z",
        ]
        duplicate = self.run_parser("update", "\n".join(base + ["UPDATE_STATE=staged", ""]))
        unknown = self.run_parser("update", "\n".join(base + ["EVIL=value", ""]))
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertNotEqual(unknown.returncode, 0)

    def test_qualification_and_runtime_stop_schemas_are_strict(self) -> None:
        qualification = self.run_parser(
            "qualification",
            "\n".join(
                [
                    "QUALIFICATION_SCHEMA_VERSION=1",
                    "QUALIFIED_RELEASE=" + "a" * 40,
                    "QUALIFIED_AT=2026-09-16T01:00:00Z",
                    "",
                ]
            ),
        )
        stop = self.run_parser(
            "runtime-stop",
            "\n".join(
                [
                    "RUNTIME_STOP_SCHEMA_VERSION=1",
                    "STOP_REASON=memory-protection",
                    "STOP_CONTAINER_NAME=qwen38-flash-next",
                    "STOP_CONTAINER_ID=" + "b" * 64,
                    "UPDATED_AT=2026-09-16T01:00:00Z",
                    "",
                ]
            ),
        )
        self.assertEqual(qualification.returncode, 0, qualification.stderr.decode())
        self.assertEqual(stop.returncode, 0, stop.stderr.decode())

    def test_runtime_commit_attestation_binds_root_and_container(self) -> None:
        valid = self.run_parser(
            "runtime-commit",
            "\n".join(
                [
                    "RUNTIME_COMMIT_SCHEMA_VERSION=1",
                    "RUNTIME_ROOT=/home/inlc/.local/share/qwen38-spark/releases/" + "a" * 40,
                    "RUNTIME_CONTAINER_NAME=qwen38-flash-next",
                    "RUNTIME_CONTAINER_ID=" + "b" * 64,
                    "COMMITTED_AT=2026-09-16T01:00:00Z",
                    "",
                ]
            ),
        )
        unsafe_root = self.run_parser(
            "runtime-commit",
            "\n".join(
                [
                    "RUNTIME_COMMIT_SCHEMA_VERSION=1",
                    "RUNTIME_ROOT=/tmp/runtime $(touch /tmp/should-not-run)",
                    "RUNTIME_CONTAINER_NAME=qwen38-flash-next",
                    "RUNTIME_CONTAINER_ID=" + "b" * 64,
                    "COMMITTED_AT=2026-09-16T01:00:00Z",
                    "",
                ]
            ),
        )
        self.assertEqual(valid.returncode, 0, valid.stderr.decode())
        fields = valid.stdout.split(b"\0")
        self.assertIn(b"RUNTIME_ROOT", fields)
        self.assertIn(b"RUNTIME_CONTAINER_ID", fields)
        self.assertNotEqual(unsafe_root.returncode, 0)


if __name__ == "__main__":
    unittest.main()
