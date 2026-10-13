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
        self.assertIn("MODEL_OWNED=0", manifest_text)
        self.assertIn("SWAP_OWNED=0", manifest_text)
        self.manifest.write_text(
            manifest_text.replace("MODEL_OWNED=0", "MODEL_OWNED=1")
            .replace("SWAP_OWNED=0", "SWAP_OWNED=1"),
            encoding="utf-8",
        )
        # An evidence-backed owned model forces bootstrap-install to create the
        # cumulative registry in the old code *before* DELETE confirmation.
        (self.model / ".qwen38-model-manifest.json").write_text(
            '{"status":"complete","repository":"synthetic/test","revision":"'
            + "a" * 40 + '"}\n',
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


    def test_cancel_preserves_existing_ownership_registry_bytes(self) -> None:
        """Owned model migration must not rewrite a preexisting registry on cancel."""
        content = self.manifest.read_text(encoding="utf-8")
        self.assertIn("MODEL_OWNED=0", content)
        self.manifest.write_text(
            content.replace("MODEL_OWNED=0", "MODEL_OWNED=1"),
            encoding="utf-8",
        )
        (self.model / ".qwen38-model-manifest.json").write_text(
            '{"status":"complete","repository":"synthetic/test","revision":"'
            + "b" * 40 + '"}\n',
            encoding="utf-8",
        )
        registry = self.state / "asset-ownership.json"
        registry.write_text('{"schema_version":1,"assets":[]}\n', encoding="utf-8")
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
        result = subprocess.run(
            ["bash", str(UNINSTALL), "--lang", "en", "--purge-model"],
            cwd=REPO,
            env={
                **os.environ,
                "HOME": str(self.home),
                "XDG_STATE_HOME": str(self.home / "state"),
                "XDG_DATA_HOME": str(self.home / "data"),
                "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", ""),
            },
            input="NO\n",
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cancelled", result.stderr)
        self.assertEqual(self.snapshot(), expected)
        self.assertFalse(daemon_calls.exists())
        self.assertFalse((self.state / "operation.lock").exists())
        self.assertEqual(registry.read_bytes(), expected["state/qwen38-spark/asset-ownership.json"])


    def test_approved_purge_preflight_failure_preserves_cumulative_registry(self) -> None:
        """An owned base with a retained dependent must fail before registry publication.

        This uses the REAL non-dry-run uninstaller, but HOME/XDG are disposable,
        owned paths are synthetic, and host mutators are replaced with rejectors.
        The preexisting unowned entry is promoted only in the *staged* registry.
        """
        import json

        manifest = self.manifest.read_text(encoding="utf-8")
        self.manifest.write_text(
            manifest.replace("MODEL_OWNED=0", "MODEL_OWNED=1")
            .replace("SWAP_OWNED=0", "SWAP_OWNED=1"),
            encoding="utf-8",
        )
        marker = self.model / ".qwen38-model-manifest.json"
        marker.write_text(
            '{"status":"complete","repository":"synthetic/base","revision":"'
            + "c" * 40 + '"}\n',
            encoding="utf-8",
        )
        dependent = self.home / "models" / "retained-dependent"
        dependent.mkdir()
        (dependent / "keep-user.txt").write_text("KEEP DEPENDENT\n", encoding="utf-8")
        registry = self.state / "asset-ownership.json"
        registry.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "assets": [
                        {
                            "kind": "model",
                            "locator": str(self.model),
                            "root": str(self.model.parent),
                            "owned": False,
                            "state": "ready",
                            "fingerprint": "",
                            "depends_on": [],
                        },
                        {
                            "kind": "model",
                            "locator": str(dependent),
                            "root": str(dependent.parent),
                            "owned": False,
                            "state": "claimed",
                            "fingerprint": "",
                            "depends_on": [str(self.model)],
                        },
                    ],
                },
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        stub_bin = self.home / "stub-bin"
        stub_bin.mkdir()
        unexpected_calls = self.home / "unexpected-mutator-calls.txt"
        for command in ("docker", "sudo", "systemctl", "swapoff"):
            stub = stub_bin / command
            stub.write_text(
                f'#!/bin/sh\nprintf "%s\\n" "{command}" >> "{unexpected_calls}"\nexit 97\n',
                encoding="utf-8",
            )
            stub.chmod(0o700)
        expected = self.snapshot()

        for flag in ("--purge-model", "--purge-all"):
            with self.subTest(flag=flag):
                result = subprocess.run(
                    ["bash", str(UNINSTALL), "--lang", "en", "--yes", flag],
                    cwd=REPO,
                    env={
                        **os.environ,
                        "HOME": str(self.home),
                        "XDG_STATE_HOME": str(self.home / "state"),
                        "XDG_DATA_HOME": str(self.home / "data"),
                        "PATH": str(stub_bin) + os.pathsep + os.environ.get("PATH", ""),
                    },
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=20,
                )
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("owned asset is required by a retained dependent", result.stderr)
                self.assertFalse(unexpected_calls.exists(), result.stderr)
                # A permitted operation.lock may be created by the preflight;
                # no installation/asset data may change or remain staged.
                actual = self.snapshot()
                actual.pop("state/qwen38-spark/operation.lock", None)
                self.assertEqual(actual, expected)
                self.assertFalse(list(self.state.glob(".uninstall-preflight.*")))
                self.assertEqual(registry.read_bytes(), expected["state/qwen38-spark/asset-ownership.json"])
                self.assertTrue((dependent / "keep-user.txt").is_file())


    def test_external_container_image_refusal_preserves_registry(self) -> None:
        """An externally referenced image refuses purge before registry publication."""
        manifest = self.manifest.read_text(encoding="utf-8")
        self.manifest.write_text(
            manifest.replace("IMAGE_OWNED=0", "IMAGE_OWNED=1"),
            encoding="utf-8",
        )
        registry = self.state / "asset-ownership.json"
        registry.write_text('{"schema_version":1,"assets":[]}\n', encoding="utf-8")
        stub_bin = self.home / "stub-bin"
        stub_bin.mkdir()
        unexpected = self.home / "unexpected-mutator.txt"
        docker = stub_bin / "docker"
        docker.write_text(
            '#!/usr/bin/env bash\n'
            'if [[ "$1" == image && "$2" == inspect ]]; then\n'
            '  printf "sha256:%s\\n" "'
            + "d" * 64
            + '"\n  exit 0\nfi\n'
            'if [[ "$1" == ps ]]; then\n'
            '  printf "external-owner\\n"\n  exit 0\nfi\n'
            'printf "%s\\n" "$*" >> "'
            + str(unexpected)
            + '"\nexit 99\n',
            encoding="utf-8",
        )
        docker.chmod(0o700)
        for command in ("sudo", "systemctl", "swapoff"):
            stub = stub_bin / command
            stub.write_text(
                f'#!/bin/sh\nprintf "%s\\n" "{command}" >> "{unexpected}"\nexit 99\n',
                encoding="utf-8",
            )
            stub.chmod(0o700)
        expected = self.snapshot()

        result = subprocess.run(
            ["bash", str(UNINSTALL), "--lang", "en", "--yes", "--purge-image"],
            cwd=REPO,
            env={
                **os.environ,
                "HOME": str(self.home),
                "XDG_STATE_HOME": str(self.home / "state"),
                "XDG_DATA_HOME": str(self.home / "data"),
                "PATH": str(stub_bin) + os.pathsep + os.environ.get("PATH", ""),
            },
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("referenced by other containers: external-owner", result.stderr)
        self.assertFalse(unexpected.exists(), result.stderr)
        actual = self.snapshot()
        actual.pop("state/qwen38-spark/operation.lock", None)
        self.assertEqual(actual, expected)
        self.assertFalse(list(self.state.glob(".uninstall-preflight.*")))
        self.assertEqual(registry.read_bytes(), expected["state/qwen38-spark/asset-ownership.json"])



    def test_post_service_failures_preserve_assets_and_can_retry(self) -> None:
        """Real CLI with fake service/Docker commands, disposable owned model."""
        import json

        synthetic_root = self.home / "synthetic-installer"
        (synthetic_root / "scripts").mkdir(parents=True)
        service = synthetic_root / "scripts" / "manage-service.sh"
        service.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        service.chmod(0o700)
        manifest = self.manifest.read_text(encoding="utf-8")
        self.manifest.write_text(
            manifest.replace(f"INSTALL_ROOT={REPO}", f"INSTALL_ROOT={synthetic_root}")
            .replace("MODEL_OWNED=0", "MODEL_OWNED=1")
            .replace("SERVICE_OWNED=0", "SERVICE_OWNED=1"),
            encoding="utf-8",
        )
        (self.model / ".qwen38-model-manifest.json").write_text(
            '{"status":"complete","repository":"synthetic/only","revision":"'
            + "a" * 40 + '"}\n',
            encoding="utf-8",
        )

        fake_bin = self.home / "fake-bin"
        fake_bin.mkdir()
        calls = self.home / "simulated-commands.log"
        service_fault = self.home / "service-fault.flag"
        docker_fault = self.home / "docker-fault.flag"
        service_fault.write_text("fail\n", encoding="utf-8")
        docker_fault.write_text("fail\n", encoding="utf-8")
        sudo = fake_bin / "sudo"
        sudo.write_text(
            "#!/usr/bin/env bash\n"
            f'printf "sudo %s\\n" "$*" >> "{calls}"\n'
            f'if [[ -e "{service_fault}" ]]; then\n'
            '  echo "synthetic service failure" >&2\n  exit 81\nfi\n'
            "exit 0\n",
            encoding="utf-8",
        )
        sudo.chmod(0o700)
        docker = fake_bin / "docker"
        docker.write_text(
            "#!/usr/bin/env bash\n"
            f'printf "docker %s\\n" "$*" >> "{calls}"\n'
            'if [[ "$1" == rm && "$2" == -f ]]; then\n'
            f'  if [[ -e "{docker_fault}" ]]; then\n'
            '    echo "Cannot connect to the Docker daemon" >&2\n    exit 82\n'
            '  fi\n  exit 0\nfi\n'
            "exit 97\n",
            encoding="utf-8",
        )
        docker.chmod(0o700)
        for name in ("systemctl", "swapoff"):
            stub = fake_bin / name
            stub.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
            stub.chmod(0o700)

        def run_remove() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                ["bash", str(UNINSTALL), "--lang", "en", "--yes", "--purge-model"],
                cwd=REPO,
                env={
                    **os.environ,
                    "HOME": str(self.home),
                    "XDG_STATE_HOME": str(self.home / "state"),
                    "XDG_DATA_HOME": str(self.home / "data"),
                    "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", ""),
                },
                capture_output=True,
                text=True,
                check=False,
                timeout=20,
            )

        service_result = run_remove()
        self.assertNotEqual(service_result.returncode, 0)
        self.assertIn("synthetic service failure", service_result.stderr)
        self.assertNotIn("docker rm -f", calls.read_text(encoding="utf-8"))
        self.assertEqual((self.model / "keep-model.bin").read_bytes(), b"KEEP MODEL")
        self.assertIn("PHASE=complete", self.manifest.read_text(encoding="utf-8"))

        service_fault.unlink()
        docker_result = run_remove()
        self.assertNotEqual(docker_result.returncode, 0)
        self.assertIn("managed container removal failed", docker_result.stderr)
        self.assertIn("docker rm -f qwen38-flash-next", calls.read_text(encoding="utf-8"))
        self.assertIn("PHASE=complete", self.manifest.read_text(encoding="utf-8"))
        self.assertEqual((self.model / "keep-model.bin").read_bytes(), b"KEEP MODEL")
        self.assertTrue((self.data / "keep-release").exists())
        registry = json.loads((self.state / "asset-ownership.json").read_text(encoding="utf-8"))
        self.assertTrue(any(
            item["locator"] == str(self.model) and item["owned"]
            for item in registry["assets"]
        ))

        docker_fault.unlink()
        retry_result = run_remove()
        self.assertEqual(retry_result.returncode, 0, retry_result.stderr)
        self.assertIn("PHASE=uninstalled", self.manifest.read_text(encoding="utf-8"))
        self.assertFalse(self.model.exists())
        self.assertEqual(
            (self.data / "keep-release").read_text(encoding="utf-8"), "KEEP RELEASE\n"
        )
        self.assertFalse(list(self.state.glob(".uninstall-preflight.*")))

    def test_docker_explicit_no_such_container_is_idempotent(self) -> None:
        """Known absent container may complete without deleting retained assets."""
        root = self.home / "synthetic-installer"
        (root / "scripts").mkdir(parents=True)
        service = root / "scripts" / "manage-service.sh"
        service.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        service.chmod(0o700)
        self.manifest.write_text(
            self.manifest.read_text(encoding="utf-8").replace(
                f"INSTALL_ROOT={REPO}", f"INSTALL_ROOT={root}"
            ),
            encoding="utf-8",
        )
        fake_bin = self.home / "fake-bin"
        fake_bin.mkdir()
        docker = fake_bin / "docker"
        docker.write_text(
            '#!/usr/bin/env bash\n'
            'if [[ "$1" == rm && "$2" == -f ]]; then\n'
            '  echo "Error response from daemon: No such container: qwen38-flash-next" >&2\n'
            '  exit 1\n'
            'fi\nexit 99\n',
            encoding="utf-8",
        )
        docker.chmod(0o700)
        for name in ("sudo", "systemctl", "swapoff"):
            stub = fake_bin / name
            stub.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
            stub.chmod(0o700)

        result = subprocess.run(
            ["bash", str(UNINSTALL), "--lang", "en", "--yes"],
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
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Container already absent: qwen38-flash-next", result.stdout)
        self.assertIn("PHASE=uninstalled", self.manifest.read_text(encoding="utf-8"))
        self.assertTrue((self.model / "keep-model.bin").exists())
        self.assertTrue((self.data / "keep-release").exists())


    def test_full_purge_swap_failure_after_owned_asset_removal_retries(self) -> None:
        """Full purge partially succeeds, then fails swap, then safely resumes.

        All files, model data and the fake swap are inside disposable HOME.
        PATH intercepts every sudo/Docker/systemctl/swapoff invocation.
        """
        import json

        root = self.home / "synthetic-installer"
        (root / "scripts").mkdir(parents=True)
        model_marker = self.model / ".qwen38-model-manifest.json"
        model_marker.write_text(
            '{"status":"complete","repository":"synthetic/owned","revision":"'
            + "f" * 40 + '"}\n',
            encoding="utf-8",
        )
        swap = self.home / "synthetic-swap.img"
        swap.write_bytes(b"DISPOSABLE FAKE SWAP")
        current = self.manifest.read_text(encoding="utf-8")
        self.manifest.write_text(
            current.replace(f"INSTALL_ROOT={REPO}", f"INSTALL_ROOT={root}")
            .replace("MODEL_OWNED=0", "MODEL_OWNED=1")
            .replace("IMAGE_OWNED=0", "IMAGE_OWNED=1")
            .replace("SWAP_OWNED=0", "SWAP_OWNED=1")
            .replace("SWAP_FILE=/swap-ple.img", f"SWAP_FILE={swap}")
            .replace("SERVICE_OWNED=0", "SERVICE_OWNED=1"),
            encoding="utf-8",
        )

        fake_bin = self.home / "fake-bin"
        fake_bin.mkdir()
        calls = self.home / "simulated-full-purge.log"
        image_exists = self.home / "fake-image-exists"
        swap_fault = self.home / "fail-swap-removal"
        image_exists.write_text("fake\n", encoding="utf-8")
        swap_fault.write_text("fault\n", encoding="utf-8")

        docker = fake_bin / "docker"
        docker.write_text(
            "#!/usr/bin/env bash\n"
            f'printf "docker %s\\n" "$*" >> "{calls}"\n'
            'if [[ "$1" == rm && "$2" == -f ]]; then exit 0; fi\n'
            'if [[ "$1" == ps ]]; then exit 0; fi\n'
            'if [[ "$1" == image && "$2" == inspect ]]; then\n'
            f'  if [[ ! -f "{image_exists}" ]]; then printf "Error: No such image: %s\\n" "${{@: -1}}" >&2; exit 1; fi\n'
            '  if [[ "$3" == --format ]]; then\n'
            '    printf "sha256:%s\\n" "'
            + "a" * 64
            + '"\n  fi\n  exit 0\nfi\n'
            'if [[ "$1" == image && "$2" == rm ]]; then\n'
            f'  rm -f -- "{image_exists}"\n  exit 0\nfi\n'
            "exit 97\n",
            encoding="utf-8",
        )
        docker.chmod(0o700)
        sudo = fake_bin / "sudo"
        sudo.write_text(
            "#!/usr/bin/env bash\n"
            f'printf "sudo %s\\n" "$*" >> "{calls}"\n'
            'if [[ "$*" == *"manage-swap.sh"* ]]; then\n'
            f'  if [[ -f "{swap_fault}" ]]; then\n'
            '    echo "synthetic swap removal failure" >&2\n    exit 88\n'
            '  fi\n'
            f'  rm -f -- "{swap}"\n'
            '  exit 0\n'
            'fi\n'
            'if [[ "$*" == *"manage-service.sh"* ]]; then exit 0; fi\n'
            "exit 97\n",
            encoding="utf-8",
        )
        sudo.chmod(0o700)
        for name in ("systemctl", "swapoff"):
            command = fake_bin / name
            command.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
            command.chmod(0o700)

        def invoke() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                ["bash", str(UNINSTALL), "--lang", "en", "--yes", "--purge-all"],
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
                timeout=30,
            )

        first = invoke()
        self.assertNotEqual(first.returncode, 0, first.stdout)
        self.assertIn("synthetic swap removal failure", first.stderr)
        self.assertFalse(self.model.exists())
        self.assertFalse(image_exists.exists())
        self.assertTrue(swap.exists())
        self.assertTrue((self.data / "keep-release").exists())
        self.assertIn("PHASE=complete", self.manifest.read_text(encoding="utf-8"))
        entries = json.loads(
            (self.state / "asset-ownership.json").read_text(encoding="utf-8")
        )["assets"]
        self.assertEqual(entries, [])
        self.assertFalse(list(self.state.glob(".uninstall-preflight.*")))

        swap_fault.unlink()
        second = invoke()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertFalse(swap.exists())
        self.assertFalse(self.manifest.exists())
        self.assertFalse(self.data.exists())
        self.assertFalse((self.state / "asset-ownership.json").exists())
        self.assertIn("Full uninstall completed", second.stdout)


    def _crash_test_stubs(self) -> Path:
        """Create an isolated fake installer and block all real host commands."""
        root = self.home / "synthetic-installer"
        (root / "scripts").mkdir(parents=True)
        service = root / "scripts" / "manage-service.sh"
        service.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        service.chmod(0o700)
        self.manifest.write_text(
            self.manifest.read_text(encoding="utf-8").replace(
                f"INSTALL_ROOT={REPO}", f"INSTALL_ROOT={root}"
            ),
            encoding="utf-8",
        )
        fake_bin = self.home / "fake-bin"
        fake_bin.mkdir()
        docker = fake_bin / "docker"
        docker.write_text(
            '#!/bin/sh\n'
            'if [ "$1" = rm ] && [ "$2" = -f ]; then exit 0; fi\n'
            'echo "unexpected Docker command" >&2\nexit 98\n',
            encoding="utf-8",
        )
        docker.chmod(0o700)
        for name in ("sudo", "systemctl", "swapoff"):
            stub = fake_bin / name
            stub.write_text(
                '#!/bin/sh\necho "blocked privileged call" >&2\nexit 99\n',
                encoding="utf-8",
            )
            stub.chmod(0o700)
        return fake_bin

    def _run_crash_test(
        self, fake_bin: Path, *args: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(UNINSTALL), "--lang", "en", "--yes", *args],
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
            timeout=20,
        )

    def test_sigkill_during_stage_requires_manual_stale_recovery(self) -> None:
        """SIGKILL preserves the canonical registry and blocks stale-stage retry."""
        import shutil

        fake_bin = self._crash_test_stubs()
        registry = self.state / "asset-ownership.json"
        registry.write_text('{"schema_version":1,"assets":[]}\n', encoding="utf-8")
        original = registry.read_bytes()
        kill_flag = self.home / "kill-during-cp"
        kill_flag.write_text("yes\n", encoding="utf-8")
        cp = fake_bin / "cp"
        cp.write_text(
            "#!/usr/bin/env bash\n"
            '/usr/bin/cp "$@" || exit $?\n'
            f'if [[ -e "{kill_flag}" ]]; then\n'
            '  kill -KILL "$PPID"\n'
            'fi\n',
            encoding="utf-8",
        )
        cp.chmod(0o700)

        killed = self._run_crash_test(fake_bin)
        self.assertEqual(killed.returncode, -9, killed.stderr)
        self.assertEqual(registry.read_bytes(), original)
        self.assertIn("PHASE=complete", self.manifest.read_text(encoding="utf-8"))
        self.assertEqual((self.model / "keep-model.bin").read_bytes(), b"KEEP MODEL")
        stale = list(self.state.glob(".uninstall-preflight.*"))
        self.assertEqual(len(stale), 1)
        self.assertTrue((stale[0] / "asset-ownership.json").is_file())

        kill_flag.unlink()
        refused = self._run_crash_test(fake_bin)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("stale uninstall preflight artifact exists", refused.stderr)
        self.assertEqual(registry.read_bytes(), original)
        self.assertTrue((self.model / "keep-model.bin").is_file())

        # A known temporary directory is inspected and cleared in THIS TEST ONLY.
        self.assertEqual(
            (stale[0] / "asset-ownership.json").read_bytes(), original
        )
        shutil.rmtree(stale[0])
        retried = self._run_crash_test(fake_bin)
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertIn("PHASE=uninstalled", self.manifest.read_text(encoding="utf-8"))
        self.assertTrue((self.model / "keep-model.bin").is_file())

    def test_sigkill_partway_through_model_delete_requires_verified_recovery(self) -> None:
        """Interrupted deletion without an ownership marker must not be retried blindly."""
        import json

        fake_bin = self._crash_test_stubs()
        self.manifest.write_text(
            self.manifest.read_text(encoding="utf-8").replace(
                "MODEL_OWNED=0", "MODEL_OWNED=1"
            ),
            encoding="utf-8",
        )
        marker = self.model / ".qwen38-model-manifest.json"
        marker.write_text(
            '{"status":"complete","repository":"synthetic","revision":"'
            + "b" * 40 + '"}\n',
            encoding="utf-8",
        )
        trusted_copy = marker.read_bytes()
        kill_flag = self.home / "kill-during-rm"
        kill_flag.write_text("yes\n", encoding="utf-8")
        rm = fake_bin / "rm"
        rm.write_text(
            "#!/usr/bin/env bash\n"
            f'if [[ "$1" == -rf && "$2" == --one-file-system && "$4" == "{self.model}" && -e "{kill_flag}" ]]; then\n'
            f'  /usr/bin/rm -f -- "{marker}"\n'
            '  kill -KILL "$PPID"\n'
            '  exit 99\n'
            'fi\n'
            'exec /usr/bin/rm "$@"\n',
            encoding="utf-8",
        )
        rm.chmod(0o700)

        killed = self._run_crash_test(fake_bin, "--purge-model")
        self.assertEqual(killed.returncode, -9, killed.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual((self.model / "keep-model.bin").read_bytes(), b"KEEP MODEL")
        self.assertIn("PHASE=complete", self.manifest.read_text(encoding="utf-8"))
        registry = self.state / "asset-ownership.json"
        entries = json.loads(registry.read_text(encoding="utf-8"))["assets"]
        self.assertTrue(any(
            x["locator"] == str(self.model) and x["owned"] for x in entries
        ))
        original = registry.read_bytes()

        kill_flag.unlink()
        refused = self._run_crash_test(fake_bin, "--purge-model")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("owned model path has no managed manifest", refused.stderr)
        self.assertEqual(registry.read_bytes(), original)
        self.assertTrue((self.model / "keep-model.bin").is_file())

        # Only simulated restoration from verified, byte-identical test fixture.
        marker.write_bytes(trusted_copy)
        resumed = self._run_crash_test(fake_bin, "--purge-model")
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertFalse(self.model.exists())
        self.assertIn("PHASE=uninstalled", self.manifest.read_text(encoding="utf-8"))
        self.assertTrue((self.data / "keep-release").is_file())


    def test_sigkill_at_swap_after_model_purge_can_resume(self) -> None:
        """Completed synthetic model removal and surviving fake swap are retriable."""
        import json

        fake_bin = self._crash_test_stubs()
        swap = self.home / "disposable-swap.img"
        swap.write_bytes(b"NOT AN ACTIVE SWAP")
        original = self.manifest.read_text(encoding="utf-8")
        self.manifest.write_text(
            original.replace("MODEL_OWNED=0", "MODEL_OWNED=1")
            .replace("SWAP_OWNED=0", "SWAP_OWNED=1")
            .replace("SWAP_FILE=/swap-ple.img", f"SWAP_FILE={swap}"),
            encoding="utf-8",
        )
        (self.model / ".qwen38-model-manifest.json").write_text(
            '{"status":"complete","repository":"synthetic","revision":"'
            + "c" * 40 + '"}\n',
            encoding="utf-8",
        )
        kill_flag = self.home / "kill-during-swap"
        kill_flag.write_text("yes\n", encoding="utf-8")
        sudo = fake_bin / "sudo"
        sudo.write_text(
            "#!/usr/bin/env bash\n"
            'if [[ "$*" == *"manage-swap.sh"* ]]; then\n'
            f'  if [[ -e "{kill_flag}" ]]; then kill -KILL "$PPID"; exit 99; fi\n'
            f'  /usr/bin/rm -f -- "{swap}"\n'
            '  exit 0\n'
            'fi\n'
            'echo "blocked unexpected sudo" >&2\nexit 97\n',
            encoding="utf-8",
        )
        sudo.chmod(0o700)

        killed = self._run_crash_test(fake_bin, "--purge-all")
        self.assertEqual(killed.returncode, -9, killed.stderr)
        self.assertFalse(self.model.exists())
        self.assertTrue(swap.is_file())
        self.assertTrue((self.data / "keep-release").is_file())
        self.assertIn("PHASE=complete", self.manifest.read_text(encoding="utf-8"))
        registry = self.state / "asset-ownership.json"
        self.assertEqual(json.loads(registry.read_text(encoding="utf-8"))["assets"], [])

        kill_flag.unlink()
        retried = self._run_crash_test(fake_bin, "--purge-all")
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertFalse(swap.exists())
        self.assertFalse(self.data.exists())
        self.assertFalse(self.manifest.exists())


    def test_full_purge_partial_plan_failure_preserves_registry_and_model(self) -> None:
        """Nonzero plan-purge with partial stdout must stop before any teardown."""
        import sys

        fake_bin = self._crash_test_stubs()
        self.manifest.write_text(
            self.manifest.read_text(encoding="utf-8")
            .replace("MODEL_OWNED=0", "MODEL_OWNED=1")
            .replace("SWAP_OWNED=0", "SWAP_OWNED=1"),
            encoding="utf-8",
        )
        marker = self.model / ".qwen38-model-manifest.json"
        marker.write_text(
            '{"status":"complete","repository":"synthetic/plan",'
            '"revision":"' + "d" * 40 + '"}\n',
            encoding="utf-8",
        )
        registry = self.state / "asset-ownership.json"
        registry.write_text('{"schema_version":1,"assets":[]}\n', encoding="utf-8")
        python_stub = fake_bin / "python3"
        python_stub.write_text(
            "#!/usr/bin/env bash\n"
            'if [[ "${2:-}" == plan-purge ]]; then\n'
            f'  printf "model\\t%s\\n" "{self.model}"\n'
            '  echo "simulated partial plan failure" >&2\n'
            '  exit 86\n'
            'fi\n'
            f'exec "{sys.executable}" "$@"\n',
            encoding="utf-8",
        )
        python_stub.chmod(0o700)
        expected = self.snapshot()

        result = self._run_crash_test(fake_bin, "--purge-all")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("ownership plan generation failed", result.stderr)
        self.assertEqual(registry.read_bytes(), expected["state/qwen38-spark/asset-ownership.json"])
        self.assertIn("PHASE=complete", self.manifest.read_text(encoding="utf-8"))
        self.assertTrue((self.model / "keep-model.bin").is_file())
        self.assertTrue((self.data / "keep-release").is_file())
        self.assertFalse(list(self.state.glob(".uninstall-preflight.*")))
        actual = self.snapshot()
        actual.pop("state/qwen38-spark/operation.lock", None)
        self.assertEqual(actual, expected)

    def test_docker_ps_error_with_partial_output_refuses_all_image_purges(self) -> None:
        """A failed Docker dependency scan is not proof of zero external users."""
        fake_bin = self._crash_test_stubs()
        self.manifest.write_text(
            self.manifest.read_text(encoding="utf-8")
            .replace("IMAGE_OWNED=0", "IMAGE_OWNED=1")
            .replace("SWAP_OWNED=0", "SWAP_OWNED=1"),
            encoding="utf-8",
        )
        registry = self.state / "asset-ownership.json"
        registry.write_text('{"schema_version":1,"assets":[]}\n', encoding="utf-8")
        docker = fake_bin / "docker"
        docker.write_text(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == image && "$2" == inspect ]]; then\n'
            '  if [[ "${3:-}" == --format ]]; then\n'
            '    printf "sha256:%s\\n" "' + "e" * 64 + '"\n'
            '  fi\n'
            '  exit 0\n'
            'fi\n'
            'if [[ "$1" == ps ]]; then\n'
            '  printf "partial-external-user\\n"\n'
            '  echo "simulated Docker daemon disconnect" >&2\n'
            '  exit 78\n'
            'fi\n'
            'echo "unexpected Docker mutation" >&2\n'
            'exit 97\n',
            encoding="utf-8",
        )
        docker.chmod(0o700)
        expected = self.snapshot()
        for flag in ("--purge-image", "--purge-all"):
            with self.subTest(flag=flag):
                result = self._run_crash_test(fake_bin, flag)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("Docker external-container inspection failed", result.stderr)
                self.assertIn("simulated Docker daemon disconnect", result.stderr)
                self.assertIn("PHASE=complete", self.manifest.read_text(encoding="utf-8"))
                self.assertTrue((self.model / "keep-model.bin").is_file())
                self.assertTrue((self.data / "keep-release").is_file())
                self.assertEqual(registry.read_bytes(), expected["state/qwen38-spark/asset-ownership.json"])
                self.assertFalse(list(self.state.glob(".uninstall-preflight.*")))
                observed = self.snapshot()
                observed.pop("state/qwen38-spark/operation.lock", None)
                self.assertEqual(observed, expected)


    def test_docker_image_probe_outage_refuses_before_registry_publication(self) -> None:
        """Do not forget an image when Docker cannot establish its existence."""
        fake_bin = self._crash_test_stubs()
        self.manifest.write_text(
            self.manifest.read_text(encoding="utf-8")
            .replace("IMAGE_OWNED=0", "IMAGE_OWNED=1")
            .replace("SWAP_OWNED=0", "SWAP_OWNED=1"),
            encoding="utf-8",
        )
        registry = self.state / "asset-ownership.json"
        registry.write_text('{"schema_version":1,"assets":[]}\n', encoding="utf-8")
        docker = fake_bin / "docker"
        docker.write_text(
            "#!/usr/bin/env bash\n"
            'if [[ "$1" == image && "$2" == inspect ]]; then\n'
            '  echo "Cannot connect to the Docker daemon" >&2\n'
            '  exit 78\n'
            'fi\n'
            'if [[ "$1" == ps ]]; then exit 0; fi\n'
            'echo "unexpected Docker mutation" >&2\n'
            'exit 97\n',
            encoding="utf-8",
        )
        docker.chmod(0o700)
        expected = self.snapshot()
        for flag in ("--purge-image", "--purge-all"):
            with self.subTest(flag=flag):
                result = self._run_crash_test(fake_bin, flag)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("cannot establish Docker image presence or absence", result.stderr)
                self.assertIn("PHASE=complete", self.manifest.read_text(encoding="utf-8"))
                self.assertEqual(registry.read_bytes(), expected["state/qwen38-spark/asset-ownership.json"])
                self.assertTrue((self.model / "keep-model.bin").is_file())
                self.assertTrue((self.data / "keep-release").is_file())
                self.assertFalse(list(self.state.glob(".uninstall-preflight.*")))
                observed = self.snapshot()
                observed.pop("state/qwen38-spark/operation.lock", None)
                self.assertEqual(observed, expected)

    def test_real_orcarouter_purge_is_blocked_before_any_host_action(self) -> None:
        """Canonical keeper model cannot be purged even if --yes was supplied."""
        protected = self.model.with_name("qwen3.8-flash-next-orcarouter")
        self.model.rename(protected)
        self.manifest.write_text(
            self.manifest.read_text(encoding="utf-8").replace(str(self.model), str(protected)),
            encoding="utf-8",
        )
        for flag in ("--purge-model", "--purge-all"):
            with self.subTest(flag=flag):
                result = subprocess.run(
                    ["bash", str(UNINSTALL), "--lang", "en", "--yes", flag],
                    cwd=REPO, env={**os.environ, "HOME": str(self.home),
                        "XDG_STATE_HOME": str(self.home / "state"),
                        "XDG_DATA_HOME": str(self.home / "data")},
                    text=True, capture_output=True, check=False, timeout=12,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ORCAROUTER_PROTECTED", result.stderr)
                self.assertEqual((protected / "keep-model.bin").read_bytes(), b"KEEP MODEL")

if __name__ == "__main__":
    unittest.main()
