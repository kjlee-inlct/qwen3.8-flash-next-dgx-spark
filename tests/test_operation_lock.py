from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
LOCK_LIB = ROOT / "scripts" / "lib" / "operation-lock.sh"
UPDATE_TRANSITION = ROOT / "scripts" / "update-transition.sh"


class OperationLockTests(unittest.TestCase):
    def test_second_mutator_is_rejected_while_lock_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state" / "qwen38-spark"
            holder = subprocess.Popen(
                [
                    "bash",
                    "-c",
                    f'source "{LOCK_LIB}"; acquire_operation_lock "$1" holder; echo READY; sleep 30',
                    "bash",
                    str(state),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                assert holder.stdout is not None
                self.assertEqual(holder.stdout.readline().strip(), "READY")
                contender = subprocess.run(
                    [
                        "bash",
                        "-c",
                        f'source "{LOCK_LIB}"; acquire_operation_lock "$1" contender',
                        "bash",
                        str(state),
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(contender.returncode, 0)
                self.assertIn("another Qwen3.8 lifecycle operation is active", contender.stderr)
            finally:
                holder.terminate()
                holder.wait(timeout=5)

    def test_update_transition_entry_point_rejects_concurrent_recover(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            xdg_state = Path(directory) / "state"
            state = xdg_state / "qwen38-spark"
            holder = subprocess.Popen(
                [
                    "bash",
                    "-c",
                    f'source "{LOCK_LIB}"; acquire_operation_lock "$1" holder; echo READY; sleep 30',
                    "bash",
                    str(state),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                assert holder.stdout is not None
                self.assertEqual(holder.stdout.readline().strip(), "READY")
                result = subprocess.run(
                    ["bash", str(UPDATE_TRANSITION), "recover"],
                    env={**os.environ, "XDG_STATE_HOME": str(xdg_state)},
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("another Qwen3.8 lifecycle operation is active", result.stderr)
            finally:
                holder.terminate()
                holder.wait(timeout=5)

    def test_descendant_can_reuse_real_outer_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state" / "qwen38-spark"
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        f'source "{LOCK_LIB}"; '
                        'acquire_operation_lock "$1" outer; '
                        f'bash -c \'source "{LOCK_LIB}"; acquire_operation_lock "$1" nested; echo NESTED_OK\' bash "$1"'
                    ),
                    "bash",
                    str(state),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("NESTED_OK", result.stdout)

    def test_inherited_marker_without_owner_chain_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state" / "qwen38-spark"
            state.mkdir(parents=True)
            lock_file = state / "operation.lock"
            lock_file.touch(mode=0o600)
            env = os.environ.copy()
            env.update(
                {
                    "QWEN38_OPERATION_LOCK_HELD": "1",
                    "QWEN38_OPERATION_LOCK_FILE": str(lock_file),
                    "QWEN38_OPERATION_LOCK_OWNER_PID": "99999999",
                }
            )
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    f'source "{LOCK_LIB}"; acquire_operation_lock "$1" spoofed',
                    "bash",
                    str(state),
                ],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("owner is not an ancestor", result.stderr)

    def test_release_and_update_mutators_use_shared_lock(self) -> None:
        release_manager = (ROOT / "scripts" / "release-manager.sh").read_text(encoding="utf-8")
        update_transition = (ROOT / "scripts" / "lifecycle" / "update-transition.sh").read_text(encoding="utf-8")
        update_release = (ROOT / "scripts" / "update-release.sh").read_text(encoding="utf-8")
        bootstrap = (ROOT / "scripts" / "lifecycle" / "bootstrap-release.sh").read_text(encoding="utf-8")

        for action in ("stage", "activate", "discard", "rollback"):
            self.assertIn(f'acquire_release_lock "release {action}"', release_manager)
        for action in ("prepare", "commit", "rollback", "recover"):
            self.assertIn(f'acquire_transition_lock "update transition {action}"', update_transition)
        self.assertIn('acquire_operation_lock "${STATE_HOME}" "release update to ${target}"', update_release)
        self.assertIn('if [[ "${DRY_RUN}" != 1 ]]', update_release)
        self.assertIn('acquire_operation_lock "${STATE_HOME}" "release bootstrap"', bootstrap)

    def test_read_only_actions_remain_unlocked(self) -> None:
        release_manager = (ROOT / "scripts" / "release-manager.sh").read_text(encoding="utf-8")
        update_transition = (ROOT / "scripts" / "lifecycle" / "update-transition.sh").read_text(encoding="utf-8")
        self.assertIn('status)\n    [[ $# -eq 0 ]]', release_manager)
        self.assertIn('status)\n    [[ $# -eq 0 ]]', update_transition)
        self.assertNotIn('status)\n    acquire_', release_manager)
        self.assertNotIn('status)\n    acquire_', update_transition)


if __name__ == "__main__":
    unittest.main()
