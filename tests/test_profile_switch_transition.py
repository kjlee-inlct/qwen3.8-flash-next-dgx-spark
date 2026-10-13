from __future__ import annotations

import fcntl
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
HELPER = ROOT / "scripts" / "lifecycle" / "profile-switch-transition.sh"


class ProfileSwitchTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.state_dir = self.home / "state" / "qwen38-spark"
        self.data_dir = self.home / "data" / "qwen38-spark"
        self.release = self.data_dir / "releases" / ("1" * 40)
        self.bin_dir = self.home / "bin"
        self.state_dir.mkdir(parents=True)
        self.release.mkdir(parents=True)
        self.bin_dir.mkdir()
        (self.data_dir / "current").symlink_to(self.release)
        self.install = self.state_dir / "install.env"
        self.candidate = self.state_dir / "install.env.profile-switch-candidate"
        self.backup = self.state_dir / "install.env.profile-switch-backup"
        self.transition = self.state_dir / "profile-switch-transition.env"
        self.runtime_commit = self.state_dir / "runtime-commit.env"
        self.old_model = self.home / "models" / "old"
        self.target_model = self.home / "models" / "target"
        self.fake_docker = self.bin_dir / "docker"
        self.fake_docker.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
[[ "${1:-}" == inspect ]] || exit 0
if [[ "${2:-}" != --format ]]; then
  exit 0
fi
format="${3:-}"
case "${format}" in
  '{{.Id}}') printf '%s\\n' "${FAKE_DOCKER_ID}" ;;
  '{{.Config.Image}}') printf '%s\\n' "${FAKE_DOCKER_IMAGE}" ;;
  '{{range .Mounts}}{{if eq .Destination "/model"}}{{.Source}}{{end}}{{end}}')
    printf '%s\\n' "${FAKE_DOCKER_MODEL}"
    ;;
  '{{json .Config.Cmd}}') printf '%s\\n' "${FAKE_DOCKER_CMD}" ;;
  *) exit 2 ;;
esac
""",
            encoding="utf-8",
        )
        self.fake_docker.chmod(self.fake_docker.stat().st_mode | stat.S_IXUSR)
        self.write_manifest(
            self.install,
            profile="orcarouter",
            phase="complete",
            model_dir=self.old_model,
            image="old-image",
            served="old/model",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_manifest(
        self,
        path: Path,
        *,
        profile: str,
        phase: str,
        model_dir: Path,
        image: str,
        served: str,
    ) -> None:
        repo = {
            "orcarouter": "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
            "nvidia": "nvidia/Qwen3.8-Flash-Next-NVFP4",
            "mazinb": "mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4",
            "orcarouter-hybrid": "local/orcarouter-mazinb-h6-w4a16",
        }[profile]
        revision = "a" * 40
        path.write_text(
            "\n".join(
                [
                    "SCHEMA_VERSION=4",
                    f"PHASE={phase}",
                    f"INSTALL_ROOT={ROOT}",
                    f"MODEL_PROFILE={profile}",
                    f"MODEL_REPO={repo}",
                    f"MODEL_REVISION={revision}",
                    f"MODEL_DIR={model_dir}",
                    "MODEL_OWNED=0",
                    "SWAP_FILE=/swap-ple.img",
                    "SWAP_OWNED=1",
                    f"VLLM_IMAGE={image}",
                    "IMAGE_OWNED=0",
                    f"SERVED_NAME={served}",
                    "CONTAINER_NAME=qwen38-flash-next",
                    "CONFIG_OVERRIDE=",
                    "CONFIG_OWNED=0",
                    "MONITOR_PROTECT=0",
                    "MONITOR_ENABLED=0",
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

    def write_target_candidate(self, profile: str = "nvidia") -> None:
        self.write_manifest(
            self.candidate,
            profile=profile,
            phase="service_ready",
            model_dir=self.target_model,
            image="target-image",
            served="target/model",
        )

    def docker_env(self, profile: str) -> dict[str, str]:
        if profile == "old":
            image = "old-image"
            model = self.old_model
            served = "old/model"
            container_id = "b" * 64
        else:
            image = "target-image"
            model = self.target_model
            served = "target/model"
            container_id = "a" * 64
        return {
            "FAKE_DOCKER_ID": container_id,
            "FAKE_DOCKER_IMAGE": image,
            "FAKE_DOCKER_MODEL": str(model),
            "FAKE_DOCKER_CMD": f'["python","--served-model-name","{served}"]',
        }

    def env(self, profile: str = "old") -> dict[str, str]:
        return {
            **os.environ,
            "HOME": str(self.home),
            "XDG_STATE_HOME": str(self.home / "state"),
            "XDG_DATA_HOME": str(self.home / "data"),
            "PATH": f"{self.bin_dir}:{os.environ.get('PATH', '')}",
            **self.docker_env(profile),
        }

    def run_helper(self, *args: str, profile: str = "old") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(HELPER), *args],
            cwd=ROOT,
            env=self.env(profile),
            text=True,
            capture_output=True,
            check=False,
        )

    def prepare_and_activate(self) -> None:
        result = self.run_helper("prepare", "orcarouter", "nvidia")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.write_target_candidate()
        result = self.run_helper("activate")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def write_target_attestation(self) -> None:
        self.runtime_commit.write_text(
            "\n".join(
                [
                    "RUNTIME_COMMIT_SCHEMA_VERSION=1",
                    f"RUNTIME_ROOT={self.release}",
                    "RUNTIME_CONTAINER_NAME=qwen38-flash-next",
                    f"RUNTIME_CONTAINER_ID={'a' * 64}",
                    "COMMITTED_AT=2026-09-29T12:00:00Z",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def test_prepare_persists_transaction_before_candidate(self) -> None:
        result = self.run_helper("prepare", "orcarouter", "nvidia")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.transition.is_file())
        text = self.transition.read_text(encoding="utf-8")
        self.assertIn("PROFILE_SWITCH_STATE=preparing", text)
        self.assertIn("FROM_PROFILE=orcarouter", text)
        self.assertIn("TO_PROFILE=nvidia", text)
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.candidate.exists())

    def test_recover_power_loss_after_live_activation_before_state_update(self) -> None:
        result = self.run_helper("prepare", "orcarouter", "nvidia")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.write_target_candidate()
        self.backup.write_bytes(self.install.read_bytes())
        self.install.write_bytes(self.candidate.read_bytes())

        result = self.run_helper("recover", profile="target")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        live = self.install.read_text(encoding="utf-8")
        self.assertIn("MODEL_PROFILE=orcarouter", live)
        self.assertIn("PHASE=complete", live)
        self.assertFalse(self.transition.exists())
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.candidate.exists())

    def test_recover_activated_switch_rolls_back_when_previous_runtime_is_provable(self) -> None:
        self.prepare_and_activate()

        result = self.run_helper("recover", profile="old")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MODEL_PROFILE=orcarouter", self.install.read_text(encoding="utf-8"))
        self.assertFalse(self.transition.exists())

    def test_recover_runtime_committed_switch_finishes_target_manifest(self) -> None:
        self.prepare_and_activate()
        self.write_target_attestation()

        result = self.run_helper("runtime-committed", profile="target")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PROFILE_SWITCH_STATE=runtime_committed", self.transition.read_text(encoding="utf-8"))

        result = self.run_helper("recover", profile="target")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        live = self.install.read_text(encoding="utf-8")
        self.assertIn("MODEL_PROFILE=nvidia", live)
        self.assertIn("PHASE=complete", live)
        self.assertFalse(self.transition.exists())
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.candidate.exists())

    def test_recover_fails_closed_after_runtime_commit_without_attestation(self) -> None:
        self.prepare_and_activate()

        result = self.run_helper("recover", profile="target")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing ambiguous rollback", result.stderr)
        self.assertTrue(self.transition.is_file())
        self.assertIn("MODEL_PROFILE=nvidia", self.install.read_text(encoding="utf-8"))
        self.assertTrue(self.backup.is_file())

    def test_service_recovery_defers_while_installer_lock_is_held(self) -> None:
        result = self.run_helper("prepare", "orcarouter", "nvidia")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lock_path = self.state_dir / "operation.lock"
        with lock_path.open("r+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_helper("service-recover")
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("deferred", result.stdout)
        self.assertTrue(self.transition.is_file())


    PROFILES = ("orcarouter", "nvidia", "mazinb", "orcarouter-hybrid")

    def _reset_pair_fixture(self, source: str) -> None:
        """Reset only this test's disposable state between ordered-pair cases."""
        for path in (self.transition, self.candidate, self.backup, self.runtime_commit):
            path.unlink(missing_ok=True)
        self.write_manifest(
            self.install,
            profile=source,
            phase="complete",
            model_dir=self.old_model,
            image="old-image",
            served="old/model",
        )

    def test_all_twelve_ordered_pairs_recover_uncommitted_to_previous(self) -> None:
        """No target attestation: activated pair must recover only the provable old runtime."""
        for source in self.PROFILES:
            for target in self.PROFILES:
                if source == target:
                    continue
                with self.subTest(source=source, target=target):
                    self._reset_pair_fixture(source)
                    original = self.install.read_bytes()
                    prepared = self.run_helper("prepare", source, target)
                    self.assertEqual(prepared.returncode, 0, prepared.stderr)
                    self.write_target_candidate(target)
                    activated = self.run_helper("activate")
                    self.assertEqual(activated.returncode, 0, activated.stderr)
                    self.assertIn(
                        f"MODEL_PROFILE={target}", self.install.read_text(encoding="utf-8")
                    )

                    # The read-only Docker stub proves the predecessor's
                    # image/mount/served identity. No host commands run.
                    recovered = self.run_helper("recover", profile="old")
                    self.assertEqual(recovered.returncode, 0, recovered.stderr)
                    self.assertEqual(self.install.read_bytes(), original)
                    self.assertFalse(self.transition.exists())
                    self.assertFalse(self.backup.exists())
                    self.assertFalse(self.candidate.exists())

    def test_all_twelve_ordered_pairs_commit_only_attested_target(self) -> None:
        """A valid target identity/commit can finalize each ordered profile pair."""
        for source in self.PROFILES:
            for target in self.PROFILES:
                if source == target:
                    continue
                with self.subTest(source=source, target=target):
                    self._reset_pair_fixture(source)
                    prepared = self.run_helper("prepare", source, target)
                    self.assertEqual(prepared.returncode, 0, prepared.stderr)
                    self.write_target_candidate(target)
                    activated = self.run_helper("activate")
                    self.assertEqual(activated.returncode, 0, activated.stderr)
                    self.write_target_attestation()

                    committed = self.run_helper("runtime-committed", profile="target")
                    self.assertEqual(committed.returncode, 0, committed.stderr)
                    self.assertIn(
                        "PROFILE_SWITCH_STATE=runtime_committed",
                        self.transition.read_text(encoding="utf-8"),
                    )
                    recovered = self.run_helper("recover", profile="target")
                    self.assertEqual(recovered.returncode, 0, recovered.stderr)
                    live = self.install.read_text(encoding="utf-8")
                    self.assertIn(f"MODEL_PROFILE={target}", live)
                    self.assertIn("PHASE=complete", live)
                    self.assertFalse(self.transition.exists())
                    self.assertFalse(self.backup.exists())
                    self.assertFalse(self.candidate.exists())

    def test_all_twelve_pairs_reject_wrong_runtime_identity_and_recover(self) -> None:
        """No target commit may be recorded with a mismatched container ID."""
        for source in self.PROFILES:
            for target in self.PROFILES:
                if source == target:
                    continue
                with self.subTest(source=source, target=target):
                    self._reset_pair_fixture(source)
                    original = self.install.read_bytes()
                    prepared = self.run_helper("prepare", source, target)
                    self.assertEqual(prepared.returncode, 0, prepared.stderr)
                    self.write_target_candidate(target)
                    activated = self.run_helper("activate")
                    self.assertEqual(activated.returncode, 0, activated.stderr)
                    self.write_target_attestation()

                    # The attestation is well formed, but it belongs to
                    # another Docker container ID. Never finalize target.
                    self.runtime_commit.write_text(
                        self.runtime_commit.read_text(encoding="utf-8").replace(
                            "RUNTIME_CONTAINER_ID=" + "a" * 64,
                            "RUNTIME_CONTAINER_ID=" + "c" * 64,
                        ),
                        encoding="utf-8",
                    )
                    bad = self.run_helper("runtime-committed", profile="target")
                    self.assertNotEqual(bad.returncode, 0)
                    self.assertIn("runtime commit attestation", bad.stderr)
                    self.assertIn(
                        "PROFILE_SWITCH_STATE=activated",
                        self.transition.read_text(encoding="utf-8"),
                    )
                    self.assertIn(
                        f"MODEL_PROFILE={target}",
                        self.install.read_text(encoding="utf-8"),
                    )

                    # Once a provable previous runtime is supplied, recovery
                    # restores exact original manifest bytes and clears tx.
                    restored = self.run_helper("recover", profile="old")
                    self.assertEqual(restored.returncode, 0, restored.stderr)
                    self.assertEqual(self.install.read_bytes(), original)
                    self.assertFalse(self.transition.exists())
                    self.assertFalse(self.backup.exists())
                    self.assertFalse(self.candidate.exists())


    def test_modified_backup_manifest_refuses_rollback_and_preserves_transaction(self) -> None:
        """Even a valid but changed backup must never overwrite the live manifest."""
        self.prepare_and_activate()
        live_before = self.install.read_bytes()
        state_before = self.transition.read_bytes()
        candidate_before = self.candidate.read_bytes()

        original_backup = self.backup.read_bytes()
        # UI language is not used by the fake Docker identity check, so
        # this isolates the recorded backup SHA256 guard.
        self.backup.write_bytes(original_backup.replace(b"UI_LANG=en", b"UI_LANG=ko"))
        self.assertNotEqual(original_backup, self.backup.read_bytes())

        result = self.run_helper("recover", profile="old")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("backup digest mismatch", result.stderr)
        self.assertEqual(self.install.read_bytes(), live_before)
        self.assertEqual(self.transition.read_bytes(), state_before)
        self.assertEqual(self.candidate.read_bytes(), candidate_before)
        self.assertTrue(self.backup.exists())

    def test_candidate_drift_blocks_commit_before_rollback_recovery(self) -> None:
        """After activation, target manifest drift must not qualify a target commit."""
        self.prepare_and_activate()
        self.write_target_attestation()
        original_candidate = self.candidate.read_bytes()
        self.candidate.write_bytes(
            original_candidate.replace(b"UI_LANG=en", b"UI_LANG=ko")
        )
        self.assertNotEqual(original_candidate, self.candidate.read_bytes())

        result = self.run_helper("runtime-committed", profile="target")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime commit attestation", result.stderr)
        self.assertIn(
            "PROFILE_SWITCH_STATE=activated",
            self.transition.read_text(encoding="utf-8"),
        )
        self.assertIn("MODEL_PROFILE=nvidia", self.install.read_text(encoding="utf-8"))

        # A provable predecessor is permitted to restore the exact original
        # manifest, without treating the damaged target as committed.
        recovered = self.run_helper("recover", profile="old")
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertIn(
            "MODEL_PROFILE=orcarouter", self.install.read_text(encoding="utf-8")
        )
        self.assertFalse(self.transition.exists())
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.candidate.exists())

    def test_missing_attestation_after_runtime_committed_blocks_finalization(self) -> None:
        """Do not accept an earlier state marker as substitute for live proof."""
        self.prepare_and_activate()
        self.write_target_attestation()
        marked = self.run_helper("runtime-committed", profile="target")
        self.assertEqual(marked.returncode, 0, marked.stderr)
        committed_state = self.transition.read_bytes()
        live_before = self.install.read_bytes()
        self.runtime_commit.unlink()

        failed = self.run_helper("recover", profile="target")
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("target runtime commit cannot be proven", failed.stderr)
        self.assertEqual(self.transition.read_bytes(), committed_state)
        self.assertEqual(self.install.read_bytes(), live_before)
        self.assertTrue(self.backup.is_file())
        self.assertTrue(self.candidate.is_file())

        self.write_target_attestation()
        recovered = self.run_helper("recover", profile="target")
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertIn("MODEL_PROFILE=nvidia", self.install.read_text(encoding="utf-8"))
        self.assertIn("PHASE=complete", self.install.read_text(encoding="utf-8"))
        self.assertFalse(self.transition.exists())
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.candidate.exists())


    def test_prepare_refuses_orphans_before_new_transaction(self) -> None:
        """Do not overwrite leftover staging during a fresh profile switch."""
        original = self.install.read_bytes()
        artifacts = (
            self.backup,
            self.candidate,
            Path(str(self.transition) + ".tmp"),
            Path(str(self.backup) + ".tmp"),
            Path(str(self.candidate) + ".tmp"),
            Path(str(self.install) + ".profile-switch-complete.tmp"),
        )
        for artifact in artifacts:
            with self.subTest(artifact=artifact.name):
                artifact.write_bytes(b"preserve interrupted transaction evidence\n")
                try:
                    result = self.run_helper("prepare", "orcarouter", "nvidia")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(
                        "artifacts exist without transaction state", result.stderr
                    )
                    self.assertFalse(self.transition.exists())
                    self.assertEqual(
                        artifact.read_bytes(),
                        b"preserve interrupted transaction evidence\n",
                    )
                    self.assertEqual(self.install.read_bytes(), original)
                finally:
                    artifact.unlink(missing_ok=True)

        staged = Path(str(self.transition) + ".tmp")
        staged.symlink_to(self.home / "missing-stage-target")
        try:
            rejected = self.run_helper("prepare", "orcarouter", "nvidia")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("artifacts exist without transaction state", rejected.stderr)
            self.assertTrue(staged.is_symlink())
            self.assertFalse(self.transition.exists())
            self.assertEqual(self.install.read_bytes(), original)
        finally:
            staged.unlink(missing_ok=True)

    def test_idle_without_transaction_or_orphans_remains_successful(self) -> None:
        """Pristine idle paths preserve their previous benign behavior."""
        for action in ("rollback", "recover", "service-recover", "status"):
            with self.subTest(action=action):
                result = self.run_helper(action)
                self.assertEqual(result.returncode, 0, result.stderr)
                if action in ("recover", "status"):
                    self.assertIn("PROFILE_SWITCH_STATE=idle", result.stdout)
        self.assertFalse(self.transition.exists())

    def test_orphan_profile_switch_files_refuse_all_idle_actions(self) -> None:
        """Missing state plus leftover backup/candidate/temporary is never idle."""
        artifacts = (
            self.backup,
            self.candidate,
            Path(str(self.transition) + ".tmp"),
            Path(str(self.backup) + ".tmp"),
            Path(str(self.candidate) + ".tmp"),
            Path(str(self.install) + ".profile-switch-complete.tmp"),
        )
        original = self.install.read_bytes()
        for artifact in artifacts:
            for action in ("rollback", "recover", "service-recover", "status"):
                with self.subTest(artifact=artifact.name, action=action):
                    artifact.write_text("orphan fixture", encoding="utf-8")
                    try:
                        result = self.run_helper(action)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(
                            "artifacts exist without transaction state",
                            result.stderr,
                        )
                        self.assertNotIn("PROFILE_SWITCH_STATE=idle", result.stdout)
                        self.assertTrue(artifact.exists())
                        self.assertEqual(self.install.read_bytes(), original)
                    finally:
                        artifact.unlink(missing_ok=True)

    def test_dangling_symlink_state_and_orphans_never_claim_idle(self) -> None:
        """Bash -e misses dangling links: all idle-like actions must reject them."""
        original = self.install.read_bytes()
        missing = self.home / "nonexistent-transaction-state"
        self.transition.symlink_to(missing)
        try:
            for action in ("rollback", "recover", "service-recover", "status"):
                with self.subTest(action=action):
                    result = self.run_helper(action)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn("PROFILE_SWITCH_STATE=idle", result.stdout)
                    self.assertEqual(self.install.read_bytes(), original)
                    self.assertTrue(self.transition.is_symlink())
        finally:
            self.transition.unlink(missing_ok=True)

        # A dangling candidate is also a retained artifact, not absence.
        self.candidate.symlink_to(missing)
        try:
            for action in ("rollback", "recover", "service-recover", "status"):
                with self.subTest(artifact="candidate_symlink", action=action):
                    result = self.run_helper(action)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(
                        "artifacts exist without transaction state",
                        result.stderr,
                    )
                    self.assertTrue(self.candidate.is_symlink())
                    self.assertEqual(self.install.read_bytes(), original)
        finally:
            self.candidate.unlink(missing_ok=True)

    def test_same_profile_and_wrong_source_refuse_before_transaction_creation(self) -> None:
        """Every registered profile rejects no-op and incorrect-source transitions."""
        for source in self.PROFILES:
            with self.subTest(source=source):
                self._reset_pair_fixture(source)
                original = self.install.read_bytes()
                same = self.run_helper("prepare", source, source)
                self.assertNotEqual(same.returncode, 0)
                self.assertIn("must differ", same.stderr)
                self.assertFalse(self.transition.exists())
                self.assertEqual(self.install.read_bytes(), original)

                wrong_source = next(x for x in self.PROFILES if x != source)
                wrong = self.run_helper("prepare", wrong_source, source)
                self.assertNotEqual(wrong.returncode, 0)
                self.assertIn("FROM_PROFILE does not match", wrong.stderr)
                self.assertFalse(self.transition.exists())
                self.assertEqual(self.install.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
