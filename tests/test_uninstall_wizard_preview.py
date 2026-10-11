"""Non-destructive real CLI regression for the bilingual uninstall wizard.

Every test uses only a synthetic disposable HOME/XDG tree. Never uninstall
a live managed runtime, remove a model, or invoke Docker/systemd/sudo.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
UNINSTALL = REPO / "uninstall.sh"


class UninstallWizardPreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.state = self.home / "state" / "qwen38-spark"
        self.data = self.home / "data" / "qwen38-spark"
        self.model = self.home / "models" / "test-orcarouter"
        self.state.mkdir(parents=True)
        self.data.mkdir(parents=True)
        self.model.mkdir(parents=True)
        (self.model / "keep-model.bin").write_bytes(b"KEEP MODEL")
        (self.data / "keep-release").write_text("KEEP RELEASE\n", encoding="utf-8")
        self.manifest = self.state / "install.env"
        self.manifest.write_text(
            "\n".join(
                [
                    "SCHEMA_VERSION=4",
                    "PHASE=complete",
                    f"INSTALL_ROOT={REPO}",
                    "MODEL_PROFILE=orcarouter",
                    "MODEL_REPO=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "MODEL_REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306",
                    f"MODEL_DIR={self.model}",
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
                    "SERVICE_OWNED=0",
                    "SERVICE_UNIT=qwen38-flash-next.service",
                    "UI_LANG=en",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self.initial_files = self.snapshot()

    def snapshot(self) -> dict[str, bytes]:
        return {
            str(file.relative_to(self.home)): file.read_bytes()
            for file in self.home.rglob("*")
            if file.is_file()
        }

    def run_preview(self, *args: str, input_text: str = "") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(UNINSTALL), *args, "--dry-run"],
            cwd=REPO,
            env={
                **os.environ,
                "HOME": str(self.home),
                "XDG_STATE_HOME": str(self.home / "state"),
                "XDG_DATA_HOME": str(self.home / "data"),
            },
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )

    def assert_readonly(self) -> None:
        self.assertEqual(self.snapshot(), self.initial_files)
        self.assertTrue((self.model / "keep-model.bin").is_file())
        self.assertTrue((self.data / "keep-release").is_file())

    def test_default_english_preview_preserves_model_and_release(self) -> None:
        result = self.run_preview("--lang", "en", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Qwen3.8 Flash Next uninstaller wizard", result.stdout)
        self.assertIn("model    :", result.stdout)
        self.assertIn("(keep)", result.stdout)
        self.assertIn("DRY-RUN complete", result.stdout)
        self.assert_readonly()

    def test_korean_preview_uses_korean_labels(self) -> None:
        result = self.run_preview("--lang", "ko", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Qwen3.8 Flash Next 제거 마법사", result.stdout)
        self.assertIn("(유지)", result.stdout)
        self.assertIn("DRY-RUN 완료", result.stdout)
        self.assert_readonly()

    def test_selected_destructive_flags_are_preview_only(self) -> None:
        result = self.run_preview(
            "--lang", "en", "--yes",
            "--purge-model", "--purge-image", "--purge-swap",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("model    :", result.stdout)
        self.assertIn("(remove)", result.stdout)
        self.assertIn("DRY-RUN complete", result.stdout)
        self.assert_readonly()

    def test_full_purge_preview_preserves_everything(self) -> None:
        result = self.run_preview("--lang", "en", "--yes", "--purge-all")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No cumulative ownership registry exists yet", result.stdout)
        self.assertIn("releases : purge", result.stdout)
        self.assertIn("DRY-RUN complete", result.stdout)
        self.assert_readonly()

    def test_readonly_preview_does_not_require_docker_or_sudo(self) -> None:
        # A dry-run must exit before any daemon mutator. An isolated
        # nonexistent command cannot be invoked accidentally.
        result = self.run_preview("--lang", "en", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("sudo:", result.stderr)
        self.assertNotIn("docker:", result.stderr)
        self.assert_readonly()


    def test_unowned_swap_purge_fails_before_host_or_fixture_mutation(self) -> None:
        """Both selected and full purge must fail closed before teardown.

        A disposable HOME/XDG fixture and rejecting daemon-command stubs
        ensure this test cannot touch a live Docker/systemd/swap resource.
        """
        fake_bin = self.home / "fake-bin"
        fake_bin.mkdir()
        daemon_calls = self.home / "unexpected-daemon-calls.txt"
        for command in ("docker", "sudo", "systemctl", "swapoff"):
            stub = fake_bin / command
            stub.write_text(
                '#!/bin/sh\nprintf "%s\n" "$0" >> "'
                + str(daemon_calls)
                + '"\nexit 99\n',
                encoding="utf-8",
            )
            stub.chmod(0o700)
        before = self.snapshot()

        for purge_flag in ("--purge-swap", "--purge-all"):
            with self.subTest(purge_flag=purge_flag):
                result = subprocess.run(
                    [
                        "bash", str(UNINSTALL),
                        "--lang", "en", "--yes", purge_flag,
                    ],
                    cwd=REPO,
                    env={
                        **os.environ,
                        "HOME": str(self.home),
                        "XDG_STATE_HOME": str(self.home / "state"),
                        "XDG_DATA_HOME": str(self.home / "data"),
                        "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", ""),
                    },
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=15,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "refusing swap deletion: swap was not created by this installer",
                    result.stderr,
                )
                self.assertFalse(daemon_calls.exists(), result.stderr)
                self.assertEqual(self.snapshot(), before)


    def test_cancel_or_eof_preserves_ownership_and_install_state(self) -> None:
        """Non-dry-run consent refusal leaves every fixture file intact.

        Use disposable HOME/XDG and shadow host commands. --purge-all uses
        synthetic SWAP_OWNED=1 solely to exercise its confirmation path.
        """
        manifest_text = self.manifest.read_text(encoding="utf-8")
        self.assertIn("SWAP_OWNED=0", manifest_text)
        self.manifest.write_text(
            manifest_text.replace("SWAP_OWNED=0", "SWAP_OWNED=1"),
            encoding="utf-8",
        )
        self.assertFalse((self.state / "asset-ownership.json").exists())
        self.assertFalse((self.state / "operation.lock").exists())

        fake_bin = self.home / "fake-bin"
        fake_bin.mkdir()
        daemon_calls = self.home / "unexpected-host-commands.txt"
        for command in ("docker", "sudo", "systemctl", "swapoff"):
            stub = fake_bin / command
            stub.write_text(
                f'#!/bin/sh\nprintf "%s\\n" "{command}" >> "{daemon_calls}"\nexit 99\n',
                encoding="utf-8",
            )
            stub.chmod(0o700)

        expected = self.snapshot()
        cases = (
            ("default_english", "en", (), "n\nn\nn\nNO\n"),
            ("selected_korean", "ko", ("--purge-model",), "취소\n"),
            ("full_purge_rejected", "en", ("--purge-all",), "NO\n"),
            ("full_purge_eof", "en", ("--purge-all",), ""),
        )
        for name, language, flags, answers in cases:
            with self.subTest(case=name):
                result = subprocess.run(
                    ["bash", str(UNINSTALL), "--lang", language, *flags],
                    cwd=REPO,
                    env={
                        **os.environ,
                        "HOME": str(self.home),
                        "XDG_STATE_HOME": str(self.home / "state"),
                        "XDG_DATA_HOME": str(self.home / "data"),
                        "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", ""),
                    },
                    input=answers,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=15,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("취소됨" if language == "ko" else "cancelled", result.stderr)
                self.assertEqual(self.snapshot(), expected)
                self.assertFalse(daemon_calls.exists())
                self.assertFalse((self.state / "asset-ownership.json").exists())
                self.assertFalse((self.state / "operation.lock").exists())


if __name__ == "__main__":
    unittest.main()
