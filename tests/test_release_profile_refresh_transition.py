from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
TRANSITION = ROOT / "scripts" / "lifecycle" / "release-profile-refresh-transition.sh"
STATE_PARSER = ROOT / "scripts" / "lib" / "state_file.py"


class ReleaseProfileRefreshTransitionTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
