from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
TRANSITION = ROOT / "scripts" / "lifecycle" / "settings-transition.sh"
OPERATION_LOCK = ROOT / "scripts" / "lib" / "operation-lock.sh"


class SettingsTransitionTests(unittest.TestCase):
    def manifest_text(self, home: Path, *, heartbeat: int = 60, profile: str = "orcarouter") -> str:
        model_dir = home / "models" / "qwen3.8-flash-next-orcarouter"
        return "\n".join(
            [
                "SCHEMA_VERSION=4",
                "PHASE=complete",
                f"INSTALL_ROOT={ROOT}",
                f"MODEL_PROFILE={profile}",
                "MODEL_REPO=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                "MODEL_REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306",
                f"MODEL_DIR={model_dir}",
                "MODEL_OWNED=0",
                "SWAP_FILE=/swap-ple.img",
                "SWAP_OWNED=0",
                "VLLM_IMAGE=vllm-skinny-tp1:v1",
                "IMAGE_OWNED=0",
                "SERVED_NAME=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                "CONTAINER_NAME=qwen38-flash-next",
                "CONFIG_OVERRIDE=",
                "CONFIG_OWNED=0",
                "MONITOR_PROTECT=0",
                "MONITOR_ENABLED=1",
                "MONITOR_MIN_AVAILABLE_GIB=6",
                "MONITOR_MIN_FREE_GIB=2",
                "MONITOR_FREE_GATE_GIB=10",
                "MONITOR_MIN_SWAP_FREE_GIB=8",
                "MONITOR_CONSECUTIVE=5",
                f"MONITOR_HEARTBEAT={heartbeat}",
                "API_ACCESS_MODE=local",
                "API_DOCKER_PORT=8000",
                "API_LAN_ADDRESS=",
                "API_LAN_PORT=8001",
                "PROXY_ENABLED=0",
                "PROXY_OWNED=0",
                "PROXY_PORT=8000",
                "SERVICE_ENABLED=0",
                "SERVICE_OWNED=0",
                "SERVICE_UNIT=qwen38-flash-next.service",
                "UI_LANG=en",
                "",
            ]
        )

    def setup_state(self, home: Path) -> tuple[Path, Path, dict[str, str]]:
        state = home / "state" / "qwen38-spark"
        state.mkdir(parents=True)
        manifest = state / "install.env"
        candidate = home / "candidate.env"
        manifest.write_text(self.manifest_text(home, heartbeat=60), encoding="utf-8")
        candidate.write_text(self.manifest_text(home, heartbeat=30), encoding="utf-8")
        env = {
            **os.environ,
            "HOME": str(home),
            "XDG_STATE_HOME": str(home / "state"),
            "XDG_DATA_HOME": str(home / "data"),
        }
        return manifest, candidate, env

    def run_transition(
        self, env: dict[str, str], *args: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(TRANSITION), *args],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_prepare_apply_commit_changes_only_settings_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            manifest, candidate, env = self.setup_state(home)
            before = manifest.read_text(encoding="utf-8")

            prepared = self.run_transition(env, "prepare", str(candidate), "0")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            self.assertEqual(manifest.read_text(encoding="utf-8"), before)
            phase = home / "state/qwen38-spark/settings-transition.phase"
            self.assertEqual(phase.read_text(encoding="utf-8"), "preparing\n")
            self.assertFalse(candidate.exists())

            applied = self.run_transition(env, "apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertIn("MONITOR_HEARTBEAT=30", manifest.read_text(encoding="utf-8"))
            self.assertEqual(phase.read_text(encoding="utf-8"), "resources-applied\n")

            committed = self.run_transition(env, "commit")
            self.assertEqual(committed.returncode, 0, committed.stderr)
            self.assertFalse(phase.exists())
            self.assertIn("MONITOR_HEARTBEAT=30", manifest.read_text(encoding="utf-8"))
            self.assertFalse(Path(str(manifest) + ".settings-backup").exists())
            self.assertFalse(Path(str(manifest) + ".settings-candidate").exists())

    def test_rollback_restores_previous_complete_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            manifest, candidate, env = self.setup_state(home)
            before = manifest.read_bytes()

            self.assertEqual(self.run_transition(env, "prepare", str(candidate), "0").returncode, 0)
            applied = self.run_transition(env, "apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            rolled_back = self.run_transition(env, "rollback")
            self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr)
            self.assertEqual(manifest.read_bytes(), before)
            self.assertFalse((home / "state/qwen38-spark/settings-transition.phase").exists())

    def test_recover_rolls_back_activation_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            manifest, candidate, env = self.setup_state(home)
            before = manifest.read_bytes()
            self.assertEqual(self.run_transition(env, "prepare", str(candidate), "0").returncode, 0)

            state = home / "state/qwen38-spark"
            target = Path(str(manifest) + ".settings-candidate")
            shutil.copy2(target, manifest)
            (state / "settings-transition.phase").write_text("activated\n", encoding="utf-8")

            recovered = self.run_transition(env, "recover")
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            self.assertEqual(manifest.read_bytes(), before)
            self.assertFalse((state / "settings-transition.phase").exists())

    def test_operation_lock_blocks_other_mutators_during_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            _, candidate, env = self.setup_state(home)
            prepared = self.run_transition(env, "prepare", str(candidate), "0")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)

            state = home / "state/qwen38-spark"
            probe = subprocess.run(
                [
                    "bash",
                    "-lc",
                    f'source "{OPERATION_LOCK}"; acquire_operation_lock "{state}" probe',
                ],
                cwd=ROOT,
                env={
                    k: v
                    for k, v in env.items()
                    if not k.startswith("QWEN38_OPERATION_LOCK_")
                    and k != "QWEN38_SETTINGS_TRANSACTION_CONTEXT"
                },
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(probe.returncode, 0)
            self.assertIn("interrupted settings transaction is active", probe.stderr)

            recovered = self.run_transition(env, "recover")
            self.assertEqual(recovered.returncode, 0, recovered.stderr)

    def test_prepare_rejects_model_identity_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            _, candidate, env = self.setup_state(home)
            candidate.write_text(
                self.manifest_text(home, heartbeat=30, profile="nvidia"),
                encoding="utf-8",
            )
            result = self.run_transition(env, "prepare", str(candidate), "0")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("MODEL_PROFILE", result.stderr)


if __name__ == "__main__":
    unittest.main()
