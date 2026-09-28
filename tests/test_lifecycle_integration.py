from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class LifecycleIntegrationTests(unittest.TestCase):
    def test_install_prepares_release_before_managed_service(self) -> None:
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertIn('DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"', installer)
        self.assertIn('baseline_revision="$(git -C "${ROOT_DIR}" rev-parse HEAD)"', installer)
        self.assertIn('bash "${ROOT_DIR}/scripts/bootstrap-release.sh" "${baseline_revision}"', installer)
        self.assertIn('bash "${ROOT_DIR}/scripts/release-manager.sh" verify "${current_release}"', installer)
        self.assertIn('bash "${ROOT_DIR}/scripts/release-manager.sh" stage "${baseline_revision}"', installer)
        self.assertIn('bash "${ROOT_DIR}/scripts/lifecycle/qualify-release.sh" "${baseline_revision}"', installer)
        self.assertIn('bash "${ROOT_DIR}/scripts/release-manager.sh" activate "${baseline_revision}"', installer)
        self.assertIn('elif [[ "${RESUME}" == 0 ]]', installer)
        self.assertIn("Immutable runtime release advanced for fresh install", installer)
        self.assertIn("differs from installer revision", installer)
        self.assertIn('service_args=(create --runtime-root "${CURRENT_RELEASE_LINK}" --yes)', installer)
        self.assertIn('"${RUNTIME_ROOT}/scripts/serve.sh"', installer)
        self.assertLess(
            installer.index('scripts/bootstrap-release.sh'),
            installer.index('service_args=(create --runtime-root'),
        )

    def test_installer_strictly_parses_resume_and_migration_manifest(self) -> None:
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertIn('install-maintenance "${STATE_FILE}"', installer)
        self.assertIn("installation manifest failed strict maintenance parsing", installer)
        self.assertIn("STATE_PARSER", installer)
        self.assertNotIn('source "${STATE_FILE}"', installer)
        self.assertNotIn("shellcheck disable=SC1090", installer)
        self.assertIn("would be migrated to schema 4", installer)

    def test_install_records_api_access_modes_and_legacy_fields(self) -> None:
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertIn("API_ACCESS_MODE", installer)
        self.assertIn("API_DOCKER_PORT", installer)
        self.assertIn("API_LAN_ADDRESS", installer)
        self.assertIn("API_LAN_PORT", installer)
        self.assertIn("PROXY_ENABLED", installer)
        self.assertIn("PROXY_PORT", installer)
        self.assertIn("--api-access", installer)
        self.assertIn("--api-lan-port", installer)
        self.assertIn("8001 recommended for new installs", installer)
        self.assertIn("use 8000 for legacy URL compatibility", installer)

    def test_install_dry_run_mentions_release_without_mutating_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = subprocess.run(
                [
                    str(ROOT / "install.sh"),
                    "--lang",
                    "en",
                    "--yes",
                    "--no-start",
                    "--dry-run",
                ],
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
            self.assertIn("release", result.stdout)
            self.assertFalse((home / "state").exists())
            self.assertFalse((home / "data").exists())

    def test_uninstall_refuses_active_update_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state_dir = home / "state" / "qwen38-spark"
            state_dir.mkdir(parents=True)
            (state_dir / "install.env").write_text(
                "\n".join(
                    [
                        "SCHEMA_VERSION=3",
                        f"INSTALL_ROOT={ROOT}",
                        "CONTAINER_NAME=qwen38-flash-next",
                        f"MODEL_DIR={home / 'model'}",
                        "MODEL_OWNED=0",
                        "SWAP_FILE=/swap-ple.img",
                        "SWAP_OWNED=0",
                        "VLLM_IMAGE=test-image",
                        "IMAGE_OWNED=0",
                        "CONFIG_OVERRIDE=''",
                        "CONFIG_OWNED=0",
                        "PROXY_OWNED=0",
                        "SERVICE_OWNED=0",
                        "UI_LANG=en",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (state_dir / "update-transition.env").write_text(
                "UPDATE_STATE=staged\n", encoding="utf-8"
            )

            result = subprocess.run(
                [str(ROOT / "uninstall.sh"), "--lang", "en", "--yes"],
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

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("update transition is active", result.stderr)
            self.assertTrue((state_dir / "install.env").is_file())
            self.assertTrue((state_dir / "update-transition.env").is_file())

    def test_uninstaller_strictly_parses_install_manifest(self) -> None:
        uninstaller = (ROOT / "uninstall.sh").read_text(encoding="utf-8")

        self.assertIn('install-uninstall "${STATE_FILE}"', uninstaller)
        self.assertIn("installation manifest failed strict uninstall parsing", uninstaller)
        self.assertIn("STATE_PARSER", uninstaller)
        self.assertNotIn('source "${STATE_FILE}"', uninstaller)
        self.assertNotIn("shellcheck disable=SC1090", uninstaller)

    def test_uninstall_full_purge_covers_release_and_transient_state(self) -> None:
        uninstaller = (ROOT / "uninstall.sh").read_text(encoding="utf-8")

        self.assertIn('PURGE_ALL=1', uninstaller)
        self.assertIn('rm -rf --one-file-system -- "${DATA_HOME}"', uninstaller)
        self.assertIn('"${STATE_DIR}/runtime-stop.env"', uninstaller)
        self.assertIn('"${STATE_DIR}/runtime-commit.env"', uninstaller)
        self.assertIn('"${STATE_DIR}/runtime-transition.env"', uninstaller)
        self.assertIn('"${STATE_DIR}/update-transition.env"', uninstaller)
        self.assertIn("PHASE=uninstalled", uninstaller)
        self.assertIn("manifest is retained in the uninstalled state", uninstaller)

    def test_retained_uninstall_manifest_allows_fresh_profile_selection(self) -> None:
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        uninstaller = (ROOT / "uninstall.sh").read_text(encoding="utf-8")

        self.assertIn('manifest_phase="$(read_manifest_phase)"', installer)
        self.assertIn('if [[ "${manifest_phase}" == uninstalled ]]', installer)
        self.assertIn('MODEL_PROFILE="${MODEL_CLI:-orcarouter}"', installer)
        self.assertIn('MODEL_REPO=""; MODEL_REVISION=""; MODEL_DIR=""; MODEL_OWNED=0', installer)
        self.assertIn('mark_manifest_uninstalled', uninstaller)
        self.assertIn('lines[matches[0]] = "PHASE=uninstalled"', uninstaller)

    def test_uninstalled_manifest_can_preview_orcarouter_hybrid_as_fresh_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state_dir = home / "state" / "qwen38-spark"
            state_dir.mkdir(parents=True)
            state = state_dir / "install.env"
            state.write_text(
                "\n".join(
                    [
                        "SCHEMA_VERSION=4",
                        "PHASE=uninstalled",
                        f"INSTALL_ROOT={ROOT}",
                        "MODEL_PROFILE=orcarouter",
                        "MODEL_REPO=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                        "MODEL_REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306",
                        f"MODEL_DIR={home / 'old-orcarouter'}",
                        "MODEL_OWNED=1",
                        "SWAP_FILE=/swap-ple.img",
                        "SWAP_OWNED=1",
                        "VLLM_IMAGE=vllm-skinny-tp1:v1",
                        "IMAGE_OWNED=1",
                        "SERVED_NAME=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                        "CONTAINER_NAME=qwen38-flash-next",
                        "CONFIG_OVERRIDE=''",
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
                        "API_LAN_ADDRESS=''",
                        "API_LAN_PORT=8001",
                        "PROXY_ENABLED=0",
                        "PROXY_OWNED=0",
                        "PROXY_PORT=8000",
                        "SERVICE_ENABLED=1",
                        "SERVICE_OWNED=0",
                        "SERVICE_UNIT=qwen38-flash-next.service",
                        "UI_LANG=en",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            before = state.read_bytes()
            result = subprocess.run(
                [
                    str(ROOT / "install.sh"),
                    "--model",
                    "orcarouter-hybrid",
                    "--lang",
                    "en",
                    "--yes",
                    "--no-start",
                    "--dry-run",
                ],
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
            self.assertIn("profile     : orcarouter-hybrid", result.stdout)
            self.assertIn("qwen3.8-h6-modelopt-w4a16", result.stdout)
            self.assertNotIn("Resuming installation", result.stdout)
            self.assertEqual(state.read_bytes(), before)

    def test_uninstaller_accepts_managed_hybrid_manifest_for_owned_model_purge(self) -> None:
        uninstaller = (ROOT / "uninstall.sh").read_text(encoding="utf-8")
        self.assertIn(".qwen38-model-manifest.json", uninstaller)
        self.assertIn(".qwen38-hybrid-manifest.json", uninstaller)
        self.assertIn("managed model/hybrid manifest missing", uninstaller)

    def test_operations_runbook_matches_supported_commands(self) -> None:
        operations = (ROOT / "OPERATIONS.md").read_text(encoding="utf-8")

        for relative_path in (
            "scripts/release-manager.sh",
            "scripts/qualify-release.sh",
            "scripts/update-release.sh",
            "scripts/update-transition.sh",
            "scripts/runtime-transition.sh",
            "scripts/doctor.sh",
            "scripts/manage-proxy.sh",
        ):
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)
            self.assertIn(relative_path, operations)

        self.assertIn("./uninstall.sh --purge-all --yes", operations)
        self.assertIn("UPDATE_STATE=idle", operations)
        self.assertIn("TRANSACTION_STATE=idle", operations)
        self.assertIn("LAN port `8001` is recommended", operations)
        self.assertIn("enter `8000` as the LAN port", operations)


if __name__ == "__main__":
    unittest.main()
