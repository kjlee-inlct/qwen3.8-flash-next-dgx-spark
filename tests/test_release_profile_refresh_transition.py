from __future__ import annotations

import fcntl
import hashlib
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
TRANSITION = ROOT / "scripts" / "lifecycle" / "release-profile-refresh-transition.sh"
STATE_PARSER = ROOT / "scripts" / "lib" / "state_file.py"


class ReleaseProfileRefreshTransitionTests(unittest.TestCase):
    def test_operator_entrypoint_is_executable(self) -> None:
        entrypoint = ROOT / "scripts" / "release-profile-refresh-transition.sh"
        self.assertTrue(
            entrypoint.stat().st_mode & stat.S_IXUSR,
            "release-profile refresh entrypoint must keep its Git executable bit for immutable releases",
        )

    def test_shell_syntax(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(TRANSITION)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_status_is_read_only_when_idle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = subprocess.run(
                ["bash", str(TRANSITION), "status"],
                cwd=ROOT,
                env={
                    **os.environ,
                    "HOME": str(home),
                    "XDG_STATE_HOME": str(home / "state"),
                    "XDG_DATA_HOME": str(home / "data"),
                },
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "RELEASE_PROFILE_REFRESH_STATE=idle")
            self.assertFalse((home / "state").exists())
            self.assertFalse((home / "data").exists())

    def test_strict_parser_accepts_refresh_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "refresh.env"
            state.write_text(
                "\n".join(
                    [
                        "RELEASE_PROFILE_REFRESH_SCHEMA_VERSION=1",
                        "RELEASE_PROFILE_REFRESH_STATE=candidate_prepared",
                        "TARGET_RELEASE=" + "a" * 40,
                        "OLD_CURRENT_RELEASE=" + "b" * 40,
                        "OLD_PREVIOUS_RELEASE=" + "c" * 40,
                        "RELEASE_MANIFEST_SHA256=" + "d" * 64,
                        f"BACKUP_MANIFEST={root / 'install.env.backup'}",
                        "BACKUP_SHA256=" + "e" * 64,
                        f"TARGET_MANIFEST={root / 'install.env.candidate'}",
                        "TARGET_MANIFEST_SHA256=" + "f" * 64,
                        "PROFILE=orcarouter",
                        "OLD_IMAGE=vllm-skinny-tp1:v1",
                        "TARGET_IMAGE=vllm-orcarouter-v029-h38-decoder-scope:v1",
                        "SERVED_NAME=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                        "UPDATED_AT=2026-10-07T00:00:00Z",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                ["python3", str(STATE_PARSER), "release-profile-refresh", str(state)],
                cwd=ROOT,
                text=False,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_transaction_is_single_recovery_owner(self) -> None:
        text = TRANSITION.read_text(encoding="utf-8")
        self.assertNotIn('UPDATE_TRANSITION="', text)
        self.assertNotIn('PROFILE_SWITCH_TRANSITION="', text)
        self.assertIn("restore_previous_pair()", text)
        self.assertIn('restore_pointer "${CURRENT_LINK}" "${OLD_CURRENT_RELEASE}"', text)
        self.assertIn('restore_pointer "${PREVIOUS_LINK}" "${OLD_PREVIOUS_RELEASE:-}"', text)
        self.assertIn('atomic_copy "${BACKUP_MANIFEST}" "${INSTALL_STATE_FILE}"', text)
        self.assertIn("refusing ambiguous recovery", text)

    def test_no_legacy_runtime_is_started_between_pair_activation(self) -> None:
        text = TRANSITION.read_text(encoding="utf-8")
        activate_start = text.index("activate_pair()")
        activate_end = text.index("restore_pointer()", activate_start)
        activate_block = text[activate_start:activate_end]
        self.assertIn('atomic_link "${RELEASES_DIR}/${TARGET_RELEASE}" "${CURRENT_LINK}"', activate_block)
        self.assertIn('atomic_copy "${TARGET_MANIFEST}" "${INSTALL_STATE_FILE}"', activate_block)
        self.assertNotIn("manage-service.sh", activate_block)

        apply_activation = text.index("    activate_pair\n")
        service_start = text.index(
            'sudo_with_operation_lock bash "${target_root}/scripts/manage-service.sh"',
            apply_activation,
        )
        self.assertLess(apply_activation, service_start)
        self.assertIn('write_state runtime_validating', text[apply_activation:service_start])

    def test_h38_identity_and_safety_proof_are_fail_closed(self) -> None:
        text = TRANSITION.read_text(encoding="utf-8")
        self.assertIn('TARGET_H38_IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"', text)
        self.assertIn('TARGET_H38_SCOPE="decoder-v1"', text)
        self.assertIn('prepare-h38-image.sh" verify', text)
        self.assertIn("same-profile refresh cannot change MODEL_REPO", text)
        self.assertIn("same-profile refresh cannot change MODEL_REVISION", text)
        self.assertIn("same-profile refresh cannot change MODEL_DIR", text)
        self.assertIn("same-profile refresh cannot change served model identity", text)
        self.assertIn("{{.State.OOMKilled}}", text)
        self.assertIn('[[ "${scope}" == "${TARGET_H38_SCOPE}" ]]', text)
        self.assertIn("runtime-commit", text)

    def test_asset_ownership_preserves_operator_owned_images(self) -> None:
        text = TRANSITION.read_text(encoding="utf-8")
        self.assertIn("owns-image", text)
        self.assertIn('elif docker image inspect "${image}"', text)
        self.assertIn("owned=0", text)
        self.assertIn("owned=1", text)
        self.assertIn("H38_OWNERSHIP", text)
        self.assertIn("--depends", text)

    def test_operation_lock_blocks_other_lifecycle_mutations(self) -> None:
        lock = (ROOT / "scripts" / "lib" / "operation-lock.sh").read_text(encoding="utf-8")
        self.assertIn("operation_lock_release_profile_refresh_guard", lock)
        self.assertIn("release-profile-refresh-transition.env", lock)
        self.assertIn("QWEN38_RELEASE_PROFILE_REFRESH_CONTEXT", lock)
        self.assertIn("recover it before another lifecycle mutation", lock)

    def test_service_runner_recovers_refresh_before_other_state(self) -> None:
        runner = (ROOT / "scripts" / "runtime" / "service-runner.sh").read_text(encoding="utf-8")
        refresh = 'bash "${RELEASE_PROFILE_REFRESH_TRANSITION}" service-recover'
        profile = 'bash "${PROFILE_SWITCH_TRANSITION}" service-recover'
        manifest = 'parse_state_into_vars install-service-runtime "${STATE_FILE}"'
        self.assertIn(refresh, runner)
        self.assertLess(runner.index(refresh), runner.index(profile))
        self.assertLess(runner.index(refresh), runner.index(manifest))

    def test_doctor_requires_refresh_transaction_idle(self) -> None:
        doctor = (ROOT / "scripts" / "doctor.sh").read_text(encoding="utf-8")
        self.assertIn("release-profile-refresh-transition.env", doctor)
        self.assertIn("release-profile-refresh-backup", doctor)
        self.assertIn("release-profile-refresh-candidate", doctor)
        self.assertIn("no incomplete release-profile refresh exists", doctor)

    def test_update_release_has_explicit_atomic_refresh_route(self) -> None:
        update = (ROOT / "scripts" / "update-release.sh").read_text(encoding="utf-8")
        self.assertIn("--refresh-profile-defaults", update)
        self.assertIn("release-profile-refresh-transition.sh", update)
        dispatch = update.index('if [[ "${REFRESH_PROFILE_DEFAULTS}" == 1 ]]')
        legacy_prepare = update.index('bash "${UPDATE_TRANSITION}" prepare "${target}"')
        self.assertLess(dispatch, legacy_prepare)
        self.assertIn('exec bash "${RELEASE_PROFILE_REFRESH}"', update[dispatch:legacy_prepare])

    def test_dry_run_exits_before_asset_or_pair_mutation(self) -> None:
        text = TRANSITION.read_text(encoding="utf-8")
        dry = text.index('if [[ "${DRY_RUN}" == 1 ]]')
        end = text.index("    fi\n\n    command -v docker", dry)
        dry_block = text[dry:end]
        self.assertIn("no release pointer, manifest, Docker image, service, or transaction state mutated", dry_block)
        self.assertIn("exit 0", dry_block)
        self.assertNotIn("track_h38_assets", dry_block)
        self.assertNotIn("activate_pair", dry_block)



class ReleaseProfileRefreshRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.data_home = self.root / "data"
        self.state_home = self.root / "state"
        self.home = self.root / "home"
        self.bin_dir = self.root / "bin"
        self.source.mkdir()
        self.bin_dir.mkdir()
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.name", "Refresh Test"], check=True)
        scripts = self.source / "scripts"
        scripts.mkdir()
        manager = scripts / "manage-service.sh"
        manager.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        manager.chmod(manager.stat().st_mode | stat.S_IXUSR)
        (self.source / "payload.txt").write_text("old\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.source), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.source), "commit", "-q", "-m", "old"], check=True)
        self.old_release = self.rev("HEAD")
        (self.source / "payload.txt").write_text("target\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.source), "commit", "-qam", "target"], check=True)
        self.target_release = self.rev("HEAD")

        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "XDG_DATA_HOME": str(self.data_home),
            "XDG_STATE_HOME": str(self.state_home),
            "QWEN38_SOURCE_ROOT": str(self.source),
            "PATH": f"{self.bin_dir}:{os.environ.get('PATH', '')}",
        }
        self.app_data = self.data_home / "qwen38-spark"
        self.state_dir = self.state_home / "qwen38-spark"
        self.releases = self.app_data / "releases"
        self.current = self.app_data / "current"
        self.previous = self.app_data / "previous"
        self.install = self.state_dir / "install.env"
        self.backup = self.state_dir / "install.env.release-profile-refresh-backup"
        self.candidate = self.state_dir / "install.env.release-profile-refresh-candidate"
        self.transition = self.state_dir / "release-profile-refresh-transition.env"
        self.runtime_commit = self.state_dir / "runtime-commit.env"

        self.run_release_manager("stage", self.old_release)
        self.run_release_manager("stage", self.target_release)
        self.current.symlink_to(self.releases / self.target_release)
        self.previous.symlink_to(self.releases / self.old_release)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        fake_sudo = self.bin_dir / "sudo"
        fake_sudo.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        fake_sudo.chmod(fake_sudo.stat().st_mode | stat.S_IXUSR)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def rev(self, ref: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(self.source), "rev-parse", ref],
            text=True,
        ).strip()

    def run_release_manager(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(ROOT / "scripts" / "release-manager.sh"), *args],
            cwd=ROOT,
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_helper(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(TRANSITION), *args],
            cwd=ROOT,
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_manifest(
        self,
        path: Path,
        *,
        install_root: Path,
        phase: str,
        image: str,
    ) -> None:
        path.write_text(
            "\n".join(
                [
                    "SCHEMA_VERSION=4",
                    f"PHASE={phase}",
                    f"INSTALL_ROOT={install_root}",
                    "MODEL_PROFILE=orcarouter",
                    "MODEL_REPO=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "MODEL_REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306",
                    f"MODEL_DIR={self.root / 'models' / 'qwen3.8-flash-next-orcarouter'}",
                    "MODEL_OWNED=0",
                    "SWAP_FILE=/swap-ple.img",
                    "SWAP_OWNED=0",
                    f"VLLM_IMAGE={image}",
                    "IMAGE_OWNED=0",
                    "SERVED_NAME=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "CONTAINER_NAME=qwen38-flash-next",
                    "CONFIG_OVERRIDE=",
                    "CONFIG_OWNED=0",
                    "MONITOR_PROTECT=1",
                    "MONITOR_ENABLED=1",
                    "MONITOR_MIN_AVAILABLE_GIB=6",
                    "MONITOR_MIN_FREE_GIB=2",
                    "MONITOR_FREE_GATE_GIB=10",
                    "MONITOR_MIN_SWAP_FREE_GIB=8",
                    "MONITOR_CONSECUTIVE=5",
                    "MONITOR_HEARTBEAT=60",
                    "API_ACCESS_MODE=local",
                    "API_DOCKER_PORT=8000",
                    "API_LAN_ADDRESS=",
                    "API_LAN_PORT=8001",
                    "PROXY_ENABLED=0",
                    "PROXY_OWNED=0",
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

    def write_state(self, phase: str, backup_sha: str | None = None) -> None:
        if backup_sha is None:
            backup_sha = hashlib.sha256(self.backup.read_bytes()).hexdigest()
        target_sha = hashlib.sha256(self.candidate.read_bytes()).hexdigest() if self.candidate.exists() else ""
        self.transition.write_text(
            "\n".join(
                [
                    "RELEASE_PROFILE_REFRESH_SCHEMA_VERSION=1",
                    f"RELEASE_PROFILE_REFRESH_STATE={phase}",
                    f"TARGET_RELEASE={self.target_release}",
                    f"OLD_CURRENT_RELEASE={self.old_release}",
                    "OLD_PREVIOUS_RELEASE=",
                    "RELEASE_MANIFEST_SHA256=" + "d" * 64,
                    f"BACKUP_MANIFEST={self.backup}",
                    f"BACKUP_SHA256={backup_sha}",
                    f"TARGET_MANIFEST={self.candidate}",
                    f"TARGET_MANIFEST_SHA256={target_sha}",
                    "PROFILE=orcarouter",
                    "OLD_IMAGE=vllm-skinny-tp1:v1",
                    "TARGET_IMAGE=vllm-orcarouter-v029-h38-decoder-scope:v1",
                    "SERVED_NAME=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "UPDATED_AT=2026-10-07T00:00:00Z",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def prepare_activated_state(self) -> None:
        self.write_manifest(
            self.backup,
            install_root=self.releases / self.old_release,
            phase="complete",
            image="vllm-skinny-tp1:v1",
        )
        self.write_manifest(
            self.candidate,
            install_root=self.releases / self.target_release,
            phase="service_ready",
            image="vllm-orcarouter-v029-h38-decoder-scope:v1",
        )
        self.install.write_bytes(self.candidate.read_bytes())
        self.write_state("activated")

    def test_recover_activated_restores_exact_previous_pair_and_manifest(self) -> None:
        self.prepare_activated_state()

        result = self.run_helper("recover")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.current.resolve(), self.releases / self.old_release)
        self.assertFalse(self.previous.exists())
        self.assertEqual(self.install.read_bytes(), self.backup.read_bytes() if self.backup.exists() else self.install.read_bytes())
        self.assertFalse(self.transition.exists())
        self.assertFalse(self.candidate.exists())

    def test_recover_digest_mismatch_fails_closed_with_state_preserved(self) -> None:
        self.prepare_activated_state()
        self.write_state("activated", backup_sha="0" * 64)

        result = self.run_helper("recover")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("backup manifest digest mismatch", result.stderr)
        self.assertTrue(self.transition.exists())
        self.assertIn(
            "RELEASE_PROFILE_REFRESH_STATE=rolling_back",
            self.transition.read_text(encoding="utf-8"),
        )
        self.assertEqual(self.current.resolve(), self.releases / self.target_release)

    def test_recover_rejects_orphan_candidate_without_state(self) -> None:
        self.candidate.write_text("orphan\n", encoding="utf-8")

        result = self.run_helper("recover")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("artifacts exist without transaction state", result.stderr)
        self.assertTrue(self.candidate.exists())

    def test_recover_runtime_committed_finishes_proven_target(self) -> None:
        self.prepare_activated_state()
        self.write_state("runtime_committed")
        container_id = "a" * 64
        self.runtime_commit.write_text(
            "\n".join(
                [
                    "RUNTIME_COMMIT_SCHEMA_VERSION=1",
                    f"RUNTIME_ROOT={self.releases / self.target_release}",
                    "RUNTIME_CONTAINER_NAME=qwen38-flash-next",
                    f"RUNTIME_CONTAINER_ID={container_id}",
                    "COMMITTED_AT=2026-10-07T00:00:00Z",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        fake_docker = self.bin_dir / "docker"
        fake_docker.write_text(
            f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == inspect && "$2" == --format ]]; then
  case "$3" in
    '{{{{.Id}}}}') printf '%s\\n' '{container_id}' ;;
    '{{{{.Config.Image}}}}') printf '%s\\n' 'vllm-orcarouter-v029-h38-decoder-scope:v1' ;;
    '{{{{.State.Running}}}}') printf '%s\\n' true ;;
    '{{{{.State.OOMKilled}}}}') printf '%s\\n' false ;;
    *) exit 2 ;;
  esac
elif [[ "$1" == image && "$2" == inspect ]]; then
  printf '%s\\n' decoder-v1
else
  exit 2
fi
""",
            encoding="utf-8",
        )
        fake_docker.chmod(fake_docker.stat().st_mode | stat.S_IXUSR)

        result = self.run_helper("recover")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.transition.exists())
        self.assertEqual(self.current.resolve(), self.releases / self.target_release)
        text = self.install.read_text(encoding="utf-8")
        self.assertIn("PHASE=complete", text)
        self.assertIn("VLLM_IMAGE=vllm-orcarouter-v029-h38-decoder-scope:v1", text)

    def test_service_recovery_defers_while_outer_lock_is_held(self) -> None:
        self.prepare_activated_state()
        lock_path = self.state_dir / "operation.lock"
        lock_path.touch(mode=0o600, exist_ok=True)
        with lock_path.open("r+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_helper("service-recover")
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("deferred", result.stdout)
        self.assertTrue(self.transition.exists())


if __name__ == "__main__":
    unittest.main()
