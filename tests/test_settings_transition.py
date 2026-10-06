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
    def manifest_text(
        self,
        home: Path,
        *,
        heartbeat: int = 60,
        profile: str = "orcarouter",
        config_override: str = "",
        config_owned: int = 0,
        api_mode: str = "local",
        service_enabled: int = 0,
    ) -> str:
        model_dir = home / "models" / "qwen3.8-flash-next-orcarouter"
        proxy_enabled = 0 if api_mode == "local" else 1
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
                f"CONFIG_OVERRIDE={config_override}",
                f"CONFIG_OWNED={config_owned}",
                "MONITOR_PROTECT=0",
                "MONITOR_ENABLED=1",
                "MONITOR_MIN_AVAILABLE_GIB=6",
                "MONITOR_MIN_FREE_GIB=2",
                "MONITOR_FREE_GATE_GIB=10",
                "MONITOR_MIN_SWAP_FREE_GIB=8",
                "MONITOR_CONSECUTIVE=5",
                f"MONITOR_HEARTBEAT={heartbeat}",
                f"API_ACCESS_MODE={api_mode}",
                "API_DOCKER_PORT=8000",
                "API_LAN_ADDRESS=",
                "API_LAN_PORT=8001",
                f"PROXY_ENABLED={proxy_enabled}",
                f"PROXY_OWNED={proxy_enabled}",
                "PROXY_PORT=8000",
                f"SERVICE_ENABLED={service_enabled}",
                f"SERVICE_OWNED={service_enabled}",
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

    def write_executable(self, path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)

    def setup_fake_resources(self, home: Path, env: dict[str, str]) -> tuple[dict[str, str], Path]:
        fake_bin = home / "fake-bin"
        resources = home / "fake-resources"
        release = home / "release"
        current = home / "data/qwen38-spark/current"
        fake_bin.mkdir()
        resources.mkdir()
        release.mkdir()
        current.parent.mkdir(parents=True, exist_ok=True)
        current.symlink_to(release, target_is_directory=True)

        self.write_executable(fake_bin / "sudo", "#!/usr/bin/env bash\nexec \"$@\"\n")
        self.write_executable(
            fake_bin / "docker",
            "#!/usr/bin/env bash\n"
            "case \"${1:-}\" in\n"
            "  inspect) printf 'false\\n'; exit 0 ;;\n"
            "  rm) exit 0 ;;\n"
            "  *) exit 0 ;;\n"
            "esac\n",
        )
        self.write_executable(
            fake_bin / "systemctl",
            "#!/usr/bin/env bash\n"
            "set -e\n"
            'root="${TEST_FAKE_RESOURCES:?}"\n'
            "case \"${1:-}\" in\n"
            "  is-active) exit 1 ;;\n"
            "  enable) : >\"${root}/service-enabled\" ;;\n"
            "  disable) rm -f -- \"${root}/service-enabled\" ;;\n"
            "  stop|reset-failed) ;;\n"
            "  *) ;;\n"
            "esac\n",
        )
        proxy = fake_bin / "manage-proxy"
        self.write_executable(
            proxy,
            "#!/usr/bin/env bash\n"
            "set -e\n"
            'root="${TEST_FAKE_RESOURCES:?}"\n'
            "case \"${1:-}\" in\n"
            "  status)\n"
            "    [[ -f \"${root}/proxy-port\" ]] || exit 1\n"
            "    port=\"$(cat \"${root}/proxy-port\")\"\n"
            "    printf '  listener  : 172.17.0.1:%s\\n' \"${port}\"\n"
            "    ;;\n"
            "  create)\n"
            "    shift; port=8000\n"
            "    while [[ $# -gt 0 ]]; do\n"
            "      if [[ \"$1\" == --docker-port ]]; then port=\"$2\"; shift; fi\n"
            "      shift\n"
            "    done\n"
            "    printf '%s\\n' \"${port}\" >\"${root}/proxy-port\"\n"
            "    ;;\n"
            "  remove) rm -f -- \"${root}/proxy-port\" ;;\n"
            "  *) exit 2 ;;\n"
            "esac\n",
        )
        service = fake_bin / "manage-service"
        self.write_executable(
            service,
            "#!/usr/bin/env bash\n"
            "set -e\n"
            'root="${TEST_FAKE_RESOURCES:?}"\n'
            "case \"${1:-}\" in\n"
            "  status)\n"
            "    if [[ -f \"${root}/service-installed\" ]]; then installed=yes; else installed=no; fi\n"
            "    if [[ -f \"${root}/service-enabled\" ]]; then enabled=yes; else enabled=no; fi\n"
            "    printf 'Qwen runtime service status\\n  installed : %s\\n  enabled   : %s\\n  active    : no\\n' \"${installed}\" \"${enabled}\"\n"
            "    [[ \"${installed}\" == yes ]]\n"
            "    ;;\n"
            "  create)\n"
            "    : >\"${root}/service-installed\"\n"
            "    : >\"${root}/service-created\"\n"
            "    enable=1\n"
            "    for arg in \"$@\"; do [[ \"${arg}\" != --no-enable ]] || enable=0; done\n"
            "    if [[ \"${enable}\" == 1 ]]; then : >\"${root}/service-enabled\"; else rm -f -- \"${root}/service-enabled\"; fi\n"
            "    ;;\n"
            "  remove) rm -f -- \"${root}/service-installed\" \"${root}/service-enabled\" ;;\n"
            "  *) exit 2 ;;\n"
            "esac\n",
        )
        runtime_transition = fake_bin / "runtime-transition"
        runtime_transition.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        wait_ready = fake_bin / "wait-ready"
        self.write_executable(wait_ready, "#!/usr/bin/env bash\nexit 0\n")

        fake_env = {
            **env,
            "PATH": f"{fake_bin}:{env['PATH']}",
            "TEST_FAKE_RESOURCES": str(resources),
            "QWEN38_MANAGE_PROXY_HELPER": str(proxy),
            "QWEN38_MANAGE_SERVICE_HELPER": str(service),
            "QWEN38_RUNTIME_TRANSITION_HELPER": str(runtime_transition),
            "QWEN38_WAIT_READY_HELPER": str(wait_ready),
            "QWEN38_SYSTEMCTL": str(fake_bin / "systemctl"),
            "QWEN38_CURRENT_RELEASE_LINK": str(current),
        }
        return fake_env, resources

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

    def test_resource_create_defers_service_enable_until_commit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            manifest, candidate, env = self.setup_state(home)
            candidate.write_text(
                self.manifest_text(
                    home,
                    heartbeat=30,
                    api_mode="docker",
                    service_enabled=1,
                ),
                encoding="utf-8",
            )
            env, resources = self.setup_fake_resources(home, env)

            prepared = self.run_transition(env, "prepare", str(candidate), "0")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            applied = self.run_transition(env, "apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertTrue((resources / "proxy-port").exists())
            self.assertTrue((resources / "service-installed").exists())
            self.assertFalse((resources / "service-enabled").exists())
            self.assertEqual(
                (home / "state/qwen38-spark/settings-transition.phase").read_text(encoding="utf-8"),
                "resources-applied\n",
            )

            committed = self.run_transition(env, "commit")
            self.assertEqual(committed.returncode, 0, committed.stderr)
            self.assertTrue((resources / "proxy-port").exists())
            self.assertTrue((resources / "service-installed").exists())
            self.assertTrue((resources / "service-enabled").exists())
            self.assertIn("API_ACCESS_MODE=docker", manifest.read_text(encoding="utf-8"))
            self.assertIn("SERVICE_ENABLED=1", manifest.read_text(encoding="utf-8"))
            self.assertFalse((home / "state/qwen38-spark/settings-transition.phase").exists())

    def test_enabled_service_no_start_preserves_existing_unit_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "state/qwen38-spark"
            state.mkdir(parents=True)
            manifest = state / "install.env"
            candidate = home / "candidate.env"
            manifest.write_text(
                self.manifest_text(home, api_mode="docker", service_enabled=1),
                encoding="utf-8",
            )
            candidate.write_text(
                self.manifest_text(
                    home,
                    heartbeat=30,
                    api_mode="docker",
                    service_enabled=1,
                ),
                encoding="utf-8",
            )
            env = {
                **os.environ,
                "HOME": str(home),
                "XDG_STATE_HOME": str(home / "state"),
                "XDG_DATA_HOME": str(home / "data"),
            }
            env, resources = self.setup_fake_resources(home, env)
            (resources / "proxy-port").write_text("8000\n", encoding="utf-8")
            (resources / "service-installed").touch()
            (resources / "service-enabled").touch()

            prepared = self.run_transition(env, "prepare", str(candidate), "0")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            applied = self.run_transition(env, "apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)

            # Activation may temporarily disable boot start, but a retained
            # managed service with deferred runtime restart must not be
            # recreated or rewritten.
            self.assertTrue((resources / "service-installed").exists())
            self.assertFalse((resources / "service-enabled").exists())
            self.assertFalse((resources / "service-created").exists())

            committed = self.run_transition(env, "commit")
            self.assertEqual(committed.returncode, 0, committed.stderr)
            self.assertTrue((resources / "service-installed").exists())
            self.assertTrue((resources / "service-enabled").exists())
            self.assertFalse((resources / "service-created").exists())

    def test_destructive_resource_change_rolls_back_symmetrically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "state/qwen38-spark"
            state.mkdir(parents=True)
            manifest = state / "install.env"
            candidate = home / "candidate.env"
            manifest.write_text(
                self.manifest_text(home, api_mode="docker", service_enabled=1),
                encoding="utf-8",
            )
            before = manifest.read_bytes()
            candidate.write_text(self.manifest_text(home, heartbeat=30), encoding="utf-8")
            env = {
                **os.environ,
                "HOME": str(home),
                "XDG_STATE_HOME": str(home / "state"),
                "XDG_DATA_HOME": str(home / "data"),
            }
            env, resources = self.setup_fake_resources(home, env)
            (resources / "proxy-port").write_text("8000\n", encoding="utf-8")
            (resources / "service-installed").touch()
            (resources / "service-enabled").touch()

            prepared = self.run_transition(env, "prepare", str(candidate), "0")
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            applied = self.run_transition(env, "apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertFalse((resources / "proxy-port").exists())
            self.assertFalse((resources / "service-installed").exists())

            rolled_back = self.run_transition(env, "rollback")
            self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr)
            self.assertEqual(manifest.read_bytes(), before)
            self.assertTrue((resources / "proxy-port").exists())
            self.assertTrue((resources / "service-installed").exists())
            self.assertTrue((resources / "service-enabled").exists())
            self.assertFalse((state / "settings-transition.phase").exists())

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

    def test_recover_activation_guard_restores_backup_before_target_activation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            manifest, candidate, env = self.setup_state(home)
            before = manifest.read_bytes()
            self.assertEqual(self.run_transition(env, "prepare", str(candidate), "0").returncode, 0)

            state = home / "state/qwen38-spark"
            (state / "settings-transition.phase").write_text(
                "activation-guarded\n", encoding="utf-8"
            )
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

    def test_prepare_rejects_new_config_ownership_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            _, candidate, env = self.setup_state(home)
            managed_config = home / "state/qwen38-spark/config.vllm.json"
            managed_config.write_text("{}\n", encoding="utf-8")
            candidate.write_text(
                self.manifest_text(
                    home,
                    heartbeat=30,
                    config_override=str(managed_config),
                    config_owned=1,
                ),
                encoding="utf-8",
            )

            result = self.run_transition(env, "prepare", str(candidate), "0")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot claim new config ownership", result.stderr)

    def test_commit_removes_released_installer_owned_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "state/qwen38-spark"
            state.mkdir(parents=True)
            managed_config = state / "config.vllm.json"
            managed_config.write_text("{}\n", encoding="utf-8")
            manifest = state / "install.env"
            candidate = home / "candidate.env"
            manifest.write_text(
                self.manifest_text(
                    home,
                    config_override=str(managed_config),
                    config_owned=1,
                ),
                encoding="utf-8",
            )
            candidate.write_text(self.manifest_text(home, heartbeat=30), encoding="utf-8")
            env = {
                **os.environ,
                "HOME": str(home),
                "XDG_STATE_HOME": str(home / "state"),
                "XDG_DATA_HOME": str(home / "data"),
            }

            self.assertEqual(self.run_transition(env, "prepare", str(candidate), "0").returncode, 0)
            applied = self.run_transition(env, "apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertTrue(managed_config.exists())

            committed = self.run_transition(env, "commit")
            self.assertEqual(committed.returncode, 0, committed.stderr)
            self.assertFalse(managed_config.exists())
            self.assertIn("CONFIG_OWNED=0", manifest.read_text(encoding="utf-8"))

    def test_rollback_preserves_installer_owned_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "state/qwen38-spark"
            state.mkdir(parents=True)
            managed_config = state / "config.vllm.json"
            managed_config.write_text("{}\n", encoding="utf-8")
            manifest = state / "install.env"
            candidate = home / "candidate.env"
            manifest.write_text(
                self.manifest_text(
                    home,
                    config_override=str(managed_config),
                    config_owned=1,
                ),
                encoding="utf-8",
            )
            before = manifest.read_bytes()
            candidate.write_text(self.manifest_text(home, heartbeat=30), encoding="utf-8")
            env = {
                **os.environ,
                "HOME": str(home),
                "XDG_STATE_HOME": str(home / "state"),
                "XDG_DATA_HOME": str(home / "data"),
            }

            self.assertEqual(self.run_transition(env, "prepare", str(candidate), "0").returncode, 0)
            applied = self.run_transition(env, "apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            rolled_back = self.run_transition(env, "rollback")

            self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr)
            self.assertTrue(managed_config.exists())
            self.assertEqual(manifest.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
