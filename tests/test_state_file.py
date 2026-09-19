from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
PARSER = ROOT / "scripts" / "state_file.py"


class StateFileParserTests(unittest.TestCase):
    def run_parser(self, schema: str, text: str) -> subprocess.CompletedProcess[bytes]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.env"
            path.write_text(text, encoding="utf-8")
            return subprocess.run(["python3", str(PARSER), schema, str(path)], cwd=ROOT,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    @staticmethod
    def install_manifest(*extra: str) -> str:
        lines = [
            "SCHEMA_VERSION=4", "PHASE=complete", "INSTALL_ROOT=/home/inlc/qwen\\ install",
            "MODEL_PROFILE=orcarouter", "MODEL_REPO=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
            "MODEL_REVISION=" + "a" * 40, "MODEL_DIR=/home/inlc/models/qwen\\ model", "MODEL_OWNED=1",
            "SWAP_FILE=/swap-ple.img", "SWAP_OWNED=1", "VLLM_IMAGE=vllm/vllm-openai:qwen38-flash-next-arm64-cu130",
            "IMAGE_OWNED=0", "SERVED_NAME=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
            "CONTAINER_NAME=qwen38-flash-next", "CONFIG_OVERRIDE=/home/inlc/state/config\\ override.json",
            "CONFIG_OWNED=1", "MONITOR_PROTECT=0", "MONITOR_ENABLED=0", "MONITOR_MIN_AVAILABLE_GIB=6",
            "MONITOR_MIN_FREE_GIB=2", "MONITOR_FREE_GATE_GIB=10", "MONITOR_MIN_SWAP_FREE_GIB=8",
            "MONITOR_CONSECUTIVE=5", "MONITOR_HEARTBEAT=60", "API_ACCESS_MODE=docker", "API_DOCKER_PORT=8000",
            "API_LAN_ADDRESS=''", "API_LAN_PORT=8001", "PROXY_ENABLED=1", "PROXY_OWNED=1", "PROXY_PORT=8000",
            "SERVICE_ENABLED=1", "SERVICE_OWNED=1", "SERVICE_UNIT=qwen38-flash-next.service", "UI_LANG=ko",
            *extra, "",
        ]
        return "\n".join(lines)

    @staticmethod
    def schema2_manifest() -> str:
        return "\n".join([
            "SCHEMA_VERSION=2", "PHASE=complete", "INSTALL_ROOT=/home/inlc/qwen\\ install",
            "MODEL_PROFILE=orcarouter", "MODEL_REPO=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
            "MODEL_REVISION=" + "a" * 40, "MODEL_DIR=/home/inlc/models/qwen\\ model", "MODEL_OWNED=0",
            "SWAP_FILE=/swap-ple.img", "SWAP_OWNED=1", "VLLM_IMAGE=test-image", "IMAGE_OWNED=0",
            "CONTAINER_NAME=qwen38-flash-next", "CONFIG_OVERRIDE=", "CONFIG_OWNED=0", "MONITOR_PROTECT=0",
            "PROXY_ENABLED=1", "PROXY_OWNED=1", "PROXY_PORT=8000", "SERVICE_ENABLED=1", "SERVICE_OWNED=1",
            "UI_LANG=en", "",
        ])

    def test_update_state_emits_nul_delimited_values(self) -> None:
        result = self.run_parser("update", "\n".join([
            "UPDATE_SCHEMA_VERSION=1", "UPDATE_STATE=staged", "TARGET_RELEASE=" + "2" * 40,
            "OLD_CURRENT_RELEASE=" + "1" * 40, "OLD_PREVIOUS_RELEASE=''", "UPDATED_AT=2026-09-16T01:00:00Z", "",
        ]))
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        fields = result.stdout.split(b"\0")
        self.assertIn(b"UPDATE_STATE", fields); self.assertIn(b"staged", fields); self.assertIn(b"OLD_PREVIOUS_RELEASE", fields)

    def test_shell_command_substitution_is_rejected_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); marker = root / "executed"; state = root / "state.env"
            state.write_text("\n".join([
                "UPDATE_SCHEMA_VERSION=1", "UPDATE_STATE=staged", "TARGET_RELEASE=$(touch " + str(marker) + ")",
                "OLD_CURRENT_RELEASE=", "OLD_PREVIOUS_RELEASE=", "UPDATED_AT=2026-09-16T01:00:00Z", "",
            ]), encoding="utf-8")
            result = subprocess.run(["python3", str(PARSER), "update", str(state)], cwd=ROOT, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0); self.assertFalse(marker.exists())

    def test_duplicate_and_unknown_keys_are_rejected(self) -> None:
        base = ["UPDATE_SCHEMA_VERSION=1", "UPDATE_STATE=staged", "TARGET_RELEASE=" + "2" * 40,
                "OLD_CURRENT_RELEASE=", "OLD_PREVIOUS_RELEASE=", "UPDATED_AT=2026-09-16T01:00:00Z"]
        self.assertNotEqual(self.run_parser("update", "\n".join(base + ["UPDATE_STATE=staged", ""])).returncode, 0)
        self.assertNotEqual(self.run_parser("update", "\n".join(base + ["EVIL=value", ""])).returncode, 0)

    def test_qualification_and_runtime_stop_schemas_are_strict(self) -> None:
        qualification = self.run_parser("qualification", "\n".join([
            "QUALIFICATION_SCHEMA_VERSION=1", "QUALIFIED_RELEASE=" + "a" * 40,
            "QUALIFIED_AT=2026-09-16T01:00:00Z", "",
        ]))
        stop = self.run_parser("runtime-stop", "\n".join([
            "RUNTIME_STOP_SCHEMA_VERSION=1", "STOP_REASON=memory-protection", "STOP_CONTAINER_NAME=qwen38-flash-next",
            "STOP_CONTAINER_ID=" + "b" * 64, "UPDATED_AT=2026-09-16T01:00:00Z", "",
        ]))
        self.assertEqual(qualification.returncode, 0, qualification.stderr.decode())
        self.assertEqual(stop.returncode, 0, stop.stderr.decode())

    def test_runtime_commit_attestation_binds_root_and_container(self) -> None:
        valid = self.run_parser("runtime-commit", "\n".join([
            "RUNTIME_COMMIT_SCHEMA_VERSION=1", "RUNTIME_ROOT=/home/inlc/.local/share/qwen38-spark/releases/" + "a" * 40,
            "RUNTIME_CONTAINER_NAME=qwen38-flash-next", "RUNTIME_CONTAINER_ID=" + "b" * 64,
            "COMMITTED_AT=2026-09-16T01:00:00Z", "",
        ]))
        unsafe_root = self.run_parser("runtime-commit", "\n".join([
            "RUNTIME_COMMIT_SCHEMA_VERSION=1", "RUNTIME_ROOT=/tmp/runtime $(touch /tmp/should-not-run)",
            "RUNTIME_CONTAINER_NAME=qwen38-flash-next", "RUNTIME_CONTAINER_ID=" + "b" * 64,
            "COMMITTED_AT=2026-09-16T01:00:00Z", "",
        ]))
        self.assertEqual(valid.returncode, 0, valid.stderr.decode()); self.assertNotEqual(unsafe_root.returncode, 0)

    def test_install_runtime_decodes_printf_q_paths_and_emits_only_runtime_fields(self) -> None:
        result = self.run_parser("install-runtime", self.install_manifest())
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        fields = result.stdout.split(b"\0")
        self.assertIn(b"/home/inlc/models/qwen model", fields); self.assertIn(b"/home/inlc/state/config override.json", fields)
        self.assertNotIn(b"INSTALL_ROOT", fields); self.assertNotIn(b"MODEL_REPO", fields); self.assertNotIn(b"PROXY_OWNED", fields)

    def test_install_service_emits_only_service_fields_and_decodes_install_root(self) -> None:
        result = self.run_parser("install-service", self.install_manifest())
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        fields = result.stdout.split(b"\0")
        self.assertIn(b"INSTALL_ROOT", fields); self.assertIn(b"/home/inlc/qwen install", fields)
        self.assertIn(b"SERVED_NAME", fields); self.assertIn(b"CONTAINER_NAME", fields)
        self.assertNotIn(b"MODEL_DIR", fields); self.assertNotIn(b"SERVICE_OWNED", fields)


    def test_install_service_accepts_service_ready_phase(self) -> None:
        manifest = self.install_manifest().replace("PHASE=complete", "PHASE=service_ready")
        result = self.run_parser("install-service", manifest)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_install_runtime_still_requires_complete_phase(self) -> None:
        manifest = self.install_manifest().replace("PHASE=complete", "PHASE=service_ready")
        result = self.run_parser("install-runtime", manifest)
        self.assertNotEqual(result.returncode, 0)

    def test_install_doctor_emits_diagnostic_fields_and_api_values(self) -> None:
        result = self.run_parser("install-doctor", self.install_manifest())
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        fields = result.stdout.split(b"\0")
        self.assertIn(b"MODEL_REPO", fields); self.assertIn(b"SWAP_FILE", fields); self.assertIn(b"API_ACCESS_MODE", fields)
        self.assertIn(b"docker", fields); self.assertIn(b"API_DOCKER_PORT", fields); self.assertNotIn(b"SERVICE_OWNED", fields)

    def test_install_doctor_schema3_falls_back_to_legacy_proxy_fields(self) -> None:
        manifest = self.install_manifest().replace("SCHEMA_VERSION=4", "SCHEMA_VERSION=3")
        manifest = "\n".join(line for line in manifest.splitlines() if not line.startswith("API_")) + "\n"
        result = self.run_parser("install-doctor", manifest)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        fields = result.stdout.split(b"\0")
        mode_index = fields.index(b"API_ACCESS_MODE")
        port_index = fields.index(b"API_DOCKER_PORT")
        self.assertEqual(fields[mode_index + 1], b"docker")
        self.assertEqual(fields[port_index + 1], b"8000")

    def test_install_uninstall_emits_only_deletion_fields(self) -> None:
        result = self.run_parser("install-uninstall", self.install_manifest())
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        fields = result.stdout.split(b"\0")
        self.assertIn(b"INSTALL_ROOT", fields)
        self.assertIn(b"/home/inlc/qwen install", fields)
        self.assertIn(b"MODEL_OWNED", fields)
        self.assertIn(b"PROXY_OWNED", fields)
        self.assertIn(b"SERVICE_OWNED", fields)
        self.assertIn(b"UI_LANG", fields)
        self.assertNotIn(b"MODEL_REPO", fields)
        self.assertNotIn(b"MONITOR_ENABLED", fields)
        self.assertNotIn(b"API_ACCESS_MODE", fields)

    def test_install_maintenance_accepts_schema2_and_preserves_present_fields(self) -> None:
        result = self.run_parser("install-maintenance", self.schema2_manifest())
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        fields = result.stdout.split(b"\0")
        self.assertIn(b"SCHEMA_VERSION", fields); self.assertIn(b"2", fields)
        self.assertIn(b"CONFIG_OVERRIDE", fields); self.assertIn(b"", fields)
        self.assertNotIn(b"API_ACCESS_MODE", fields); self.assertNotIn(b"MONITOR_ENABLED", fields)

    def test_install_maintenance_rejects_executable_or_invalid_ownership_values(self) -> None:
        executable = self.schema2_manifest().replace("MODEL_DIR=/home/inlc/models/qwen\\ model", "MODEL_DIR=$(touch\\ /tmp/qwen38-maintenance-should-not-run)")
        invalid_owned = self.schema2_manifest().replace("MODEL_OWNED=0", "MODEL_OWNED=2")
        self.assertNotEqual(self.run_parser("install-maintenance", executable).returncode, 0)
        self.assertNotEqual(self.run_parser("install-maintenance", invalid_owned).returncode, 0)
        self.assertFalse(Path("/tmp/qwen38-maintenance-should-not-run").exists())

    def test_install_runtime_rejects_unknown_or_executable_manifest_content(self) -> None:
        unknown = self.run_parser("install-runtime", self.install_manifest("EVIL=value"))
        executable = self.run_parser("install-runtime", self.install_manifest().replace(
            "MODEL_DIR=/home/inlc/models/qwen\\ model", "MODEL_DIR=$(touch\\ /tmp/qwen38-parser-should-not-run)"))
        self.assertNotEqual(unknown.returncode, 0); self.assertNotEqual(executable.returncode, 0)
        self.assertFalse(Path("/tmp/qwen38-parser-should-not-run").exists())

    def test_install_runtime_rejects_inconsistent_monitor_protection(self) -> None:
        result = self.run_parser("install-runtime", self.install_manifest().replace("MONITOR_PROTECT=0", "MONITOR_PROTECT=1"))
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
