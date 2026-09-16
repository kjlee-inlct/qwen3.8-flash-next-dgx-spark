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
        self.assertIn('bash "${ROOT_DIR}/scripts/bootstrap-release.sh" "${baseline_revision}"', installer)
        self.assertIn('bash "${ROOT_DIR}/scripts/release-manager.sh" verify "${current_release}"', installer)
        self.assertIn('service_args=(create --runtime-root "${CURRENT_RELEASE_LINK}" --yes)', installer)
        self.assertIn('"${RUNTIME_ROOT}/scripts/serve.sh"', installer)
        self.assertLess(
            installer.index('scripts/bootstrap-release.sh'),
            installer.index('service_args=(create --runtime-root'),
        )

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
                        f"INSTALL_ROOT={ROOT}",
                        "CONTAINER_NAME=qwen38-flash-next",
                        f"MODEL_DIR={home / 'model'}",
                        "MODEL_OWNED=0",
                        "SWAP_FILE=/swap-ple.img",
                        "SWAP_OWNED=0",
                        "VLLM_IMAGE=test-image",
                        "IMAGE_OWNED=0",
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

    def test_uninstall_full_purge_covers_release_and_transient_state(self) -> None:
        uninstaller = (ROOT / "uninstall.sh").read_text(encoding="utf-8")

        self.assertIn('PURGE_ALL=1', uninstaller)
        self.assertIn('rm -rf --one-file-system -- "${DATA_HOME}"', uninstaller)
        self.assertIn('"${STATE_DIR}/runtime-stop.env"', uninstaller)
        self.assertIn('"${STATE_DIR}/runtime-transition.env"', uninstaller)
        self.assertIn('"${STATE_DIR}/update-transition.env"', uninstaller)
        self.assertIn("Immutable release history and manifest were retained", uninstaller)

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
