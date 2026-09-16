from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "runtime-transition.sh"


FAKE_DOCKER = r'''#!/usr/bin/env python3
import os
import pathlib
import sys

root = pathlib.Path(os.environ["FAKE_DOCKER_STATE"])
root.mkdir(parents=True, exist_ok=True)


def path(name: str) -> pathlib.Path:
    return root / name.replace("/", "_")


def exists(name: str) -> bool:
    return path(name).exists()


def status(name: str) -> str:
    return path(name).read_text(encoding="utf-8").strip()


def write(name: str, value: str) -> None:
    path(name).write_text(value, encoding="utf-8")

args = sys.argv[1:]
if not args:
    sys.exit(2)
cmd = args[0]

if cmd == "inspect":
    if len(args) >= 4 and args[1] in ("-f", "--format"):
        name = args[3]
        if not exists(name):
            sys.exit(1)
        template = args[2]
        if "State.Running" in template:
            print("true" if status(name) == "running" else "false")
        elif "State.Status" in template:
            print(status(name))
        else:
            print("")
        sys.exit(0)
    name = args[-1]
    sys.exit(0 if exists(name) else 1)

if cmd == "stop":
    name = args[-1]
    if not exists(name):
        sys.exit(1)
    write(name, "stopped")
    sys.exit(0)

if cmd == "start":
    name = args[-1]
    if not exists(name):
        sys.exit(1)
    write(name, "running")
    print(name)
    sys.exit(0)

if cmd == "rename":
    old, new = args[1], args[2]
    if not exists(old) or exists(new):
        sys.exit(1)
    path(old).rename(path(new))
    sys.exit(0)

if cmd == "rm":
    name = args[-1]
    if exists(name):
        path(name).unlink()
        sys.exit(0)
    sys.exit(1)

print(f"unsupported fake docker command: {args}", file=sys.stderr)
sys.exit(2)
'''


class RuntimeTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        docker = self.bin_dir / "docker"
        docker.write_text(FAKE_DOCKER, encoding="utf-8")
        docker.chmod(0o755)
        self.docker_state = self.root / "docker-state"
        self.docker_state.mkdir()
        self.xdg_state = self.root / "state"
        self.env = os.environ.copy()
        self.env.update(
            {
                "PATH": f"{self.bin_dir}:{self.env['PATH']}",
                "FAKE_DOCKER_STATE": str(self.docker_state),
                "XDG_STATE_HOME": str(self.xdg_state),
                "HOME": str(self.root / "home"),
                "CONTAINER_NAME": "qwen38-flash-next",
            }
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def container_path(self, name: str) -> Path:
        return self.docker_state / name

    @property
    def transition_file(self) -> Path:
        return self.xdg_state / "qwen38-spark" / "runtime-transition.env"

    def set_container(self, name: str, state: str) -> None:
        self.container_path(name).write_text(state, encoding="utf-8")

    def write_transition_state(self, state: str, had_previous: int) -> None:
        self.transition_file.parent.mkdir(parents=True, exist_ok=True)
        self.transition_file.write_text(
            textwrap.dedent(
                f"""\
                RUNTIME_SCHEMA_VERSION=1
                TRANSACTION_STATE={state}
                CURRENT_CONTAINER=qwen38-flash-next
                ROLLBACK_CONTAINER=qwen38-flash-next.rollback
                HAD_PREVIOUS={had_previous}
                UPDATED_AT=2026-09-16T00:00:00Z
                """
            ),
            encoding="utf-8",
        )

    def run_transition(self, action: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT), action],
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )

    def test_status_is_idle_without_state_file(self) -> None:
        result = self.run_transition("status")
        self.assertEqual(result.stdout.strip(), "TRANSACTION_STATE=idle")

    def test_prepare_then_rollback_restores_previous_container(self) -> None:
        self.set_container("qwen38-flash-next", "running")
        self.run_transition("prepare")
        self.assertFalse(self.container_path("qwen38-flash-next").exists())
        self.assertEqual(self.container_path("qwen38-flash-next.rollback").read_text(), "stopped")

        self.set_container("qwen38-flash-next", "running")
        self.run_transition("candidate-started")
        self.run_transition("validating")
        self.run_transition("rollback")

        self.assertEqual(self.container_path("qwen38-flash-next").read_text(), "running")
        self.assertFalse(self.container_path("qwen38-flash-next.rollback").exists())
        self.assertFalse(self.transition_file.exists())

    def test_recover_after_previous_was_preserved(self) -> None:
        self.set_container("qwen38-flash-next", "running")
        self.run_transition("prepare")

        result = self.run_transition("recover")

        self.assertIn("recovery complete", result.stdout)
        self.assertEqual(self.container_path("qwen38-flash-next").read_text(), "running")
        self.assertFalse(self.container_path("qwen38-flash-next.rollback").exists())
        self.assertFalse(self.transition_file.exists())

    def test_recover_preparing_state_before_rename(self) -> None:
        self.set_container("qwen38-flash-next", "stopped")
        self.write_transition_state("preparing", 1)

        self.run_transition("recover")

        self.assertEqual(self.container_path("qwen38-flash-next").read_text(), "running")
        self.assertFalse(self.transition_file.exists())

    def test_commit_removes_preserved_container(self) -> None:
        self.set_container("qwen38-flash-next", "running")
        self.run_transition("prepare")
        self.set_container("qwen38-flash-next", "running")
        self.run_transition("candidate-started")
        self.run_transition("validating")
        self.run_transition("commit")

        self.assertEqual(self.container_path("qwen38-flash-next").read_text(), "running")
        self.assertFalse(self.container_path("qwen38-flash-next.rollback").exists())
        self.assertFalse(self.transition_file.exists())

    def test_recover_committing_before_rollback_delete_restores_previous(self) -> None:
        self.set_container("qwen38-flash-next", "running")
        self.set_container("qwen38-flash-next.rollback", "stopped")
        self.write_transition_state("committing", 1)

        result = self.run_transition("recover")

        self.assertIn("recovery complete", result.stdout)
        self.assertEqual(self.container_path("qwen38-flash-next").read_text(), "running")
        self.assertFalse(self.container_path("qwen38-flash-next.rollback").exists())
        self.assertFalse(self.transition_file.exists())

    def test_recover_committing_after_rollback_delete_accepts_candidate(self) -> None:
        self.set_container("qwen38-flash-next", "running")
        self.write_transition_state("committing", 1)

        result = self.run_transition("recover")

        self.assertIn("accepted committed candidate", result.stdout)
        self.assertEqual(self.container_path("qwen38-flash-next").read_text(), "running")
        self.assertFalse(self.transition_file.exists())

    def test_recover_committing_after_delete_restarts_stopped_candidate(self) -> None:
        self.set_container("qwen38-flash-next", "stopped")
        self.write_transition_state("committing", 1)

        self.run_transition("recover")

        self.assertEqual(self.container_path("qwen38-flash-next").read_text(), "running")
        self.assertFalse(self.transition_file.exists())

    def test_recover_committing_without_previous_accepts_candidate(self) -> None:
        self.set_container("qwen38-flash-next", "running")
        self.write_transition_state("committing", 0)

        self.run_transition("recover")

        self.assertEqual(self.container_path("qwen38-flash-next").read_text(), "running")
        self.assertFalse(self.transition_file.exists())

    def test_recover_refuses_ambiguous_containers_without_state(self) -> None:
        self.set_container("qwen38-flash-next", "running")
        self.set_container("qwen38-flash-next.rollback", "stopped")

        result = self.run_transition("recover", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing ambiguous recovery", result.stderr)
        self.assertTrue(self.container_path("qwen38-flash-next").exists())
        self.assertTrue(self.container_path("qwen38-flash-next.rollback").exists())

    def test_recover_rejects_rollback_container_mismatch(self) -> None:
        self.set_container("qwen38-flash-next", "stopped")
        self.set_container("unexpected.rollback", "stopped")
        self.transition_file.parent.mkdir(parents=True)
        self.transition_file.write_text(
            textwrap.dedent(
                """\
                RUNTIME_SCHEMA_VERSION=1
                TRANSACTION_STATE=previous_preserved
                CURRENT_CONTAINER=qwen38-flash-next
                ROLLBACK_CONTAINER=unexpected.rollback
                HAD_PREVIOUS=1
                UPDATED_AT=2026-09-15T00:00:00Z
                """
            ),
            encoding="utf-8",
        )

        result = self.run_transition("recover", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rollback-container mismatch", result.stderr)
        self.assertTrue(self.container_path("qwen38-flash-next").exists())
        self.assertTrue(self.container_path("unexpected.rollback").exists())


if __name__ == "__main__":
    unittest.main()
