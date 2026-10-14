"""Synthetic-only, fail-closed mazinb service/proxy/port/Docker post-audit tests."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/diagnostics/verify-mazinb-retirement.py"
SPEC = importlib.util.spec_from_file_location("mazinb_post_audit", SOURCE)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class MzinbPostAuditTests(unittest.TestCase):
    def test_unit_parsing_covers_system_user_timer_and_socket(self):
        cases = [
            ("qwen38-mazinb-m1-background.service", True),
            ("qwen38-mazinb-debug.socket", True),
            ("qwen38-mazinb-run.timer", True),
            ("mazinb.service", True),
            ("qwen38-openwebui-proxy.socket", False),
            ("qwen38-flash-next.service", False),
        ]
        for unit, included in cases:
            with self.subTest(unit=unit):
                self.assertEqual(unit in AUDIT.unit_names(unit + " enabled enabled\n"), included)

    def test_dedicated_user_or_system_unit_blocks(self):
        for prefix in ((), ("--user",)):
            def fake_cmd(*args):
                if "list-unit-files" in args:
                    return "qwen38-mazinb-m1-background.service enabled enabled\n"
                return ""
            with mock.patch.object(AUDIT, "command", side_effect=fake_cmd):
                result = AUDIT.systemd_scope(prefix, "TEST")
            self.assertIn("qwen38-mazinb-m1-background.service", result)

    def test_systemd_query_failure_is_not_a_false_pass(self):
        with mock.patch.object(AUDIT, "command",
                               side_effect=AUDIT.AuditBlocked("USER_SYSTEMD_QUERY_FAILED")):
            with self.assertRaisesRegex(AUDIT.AuditBlocked, "USER_SYSTEMD_QUERY_FAILED"):
                AUDIT.systemd_scope(("--user",), "USER")

    def test_m1_port_18889_blocks_even_if_other_shared_ports_are_expected(self):
        with mock.patch.object(AUDIT, "command",
                               return_value="LISTEN 0 4096 127.0.0.1:8888 0.0.0.0:*\n"
                                            "LISTEN 0 4096 [::]:8000 [::]:*\n"):
            AUDIT.sockets_check()
        for bound in ("127.0.0.1:18889", "0.0.0.0:18889", "[::]:18889"):
            with self.subTest(bound=bound), \
                 mock.patch.object(AUDIT, "command",
                                   return_value=f"LISTEN 0 4096 {bound} 0.0.0.0:*\n"):
                with self.assertRaisesRegex(AUDIT.AuditBlocked, "18889"):
                    AUDIT.sockets_check()

    def test_unexpected_ma_m1_or_old_model_process_blocks(self):
        for process in (
            "812 python3 /repo/scripts/runtime/mazinb-m1.py run --old-id 0",
            "813 bash /repo/scripts/runtime/mazinb-kv-ab.sh start",
            "814 python /tools/test.py --model /repo/models/qwen3.8-flash-next-mazinb",
        ):
            with self.subTest(process=process), \
                 mock.patch.object(AUDIT, "command", return_value=process + "\n"):
                with self.assertRaisesRegex(AUDIT.AuditBlocked, "MAZINB_RELATED_HOST_PROCESS"):
                    AUDIT.processes_check()
        with mock.patch.object(AUDIT, "command", return_value=(
            "816 systemd-socket-proxyd 127.0.0.1:8888\n"
            "817 python /repo/scripts/diagnostics/verify-mazinb-retirement.py\n")):
            AUDIT.processes_check()

    def test_retirement_archive_is_exact_five_pairs_and_all_hashes_are_rechecked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            m1 = state / "mazinb-m1"
            m1.mkdir(parents=True)
            expected_name = "qwen38-mazinb-m1-20261014013811-16ced779"
            (m1 / "active.json").write_text(json.dumps({
                "phase": "stopped", "name": expected_name,
                "id": AUDIT.RETIRE.EXPECTED[expected_name]}))
            archive = state / "retirement-archives/mazinb-docker-test"
            archive.mkdir(parents=True)
            lines = []
            for name, cid in AUDIT.RETIRE.EXPECTED.items():
                for ext in ("log", "json"):
                    path = archive / (cid[:16] + "." + ext)
                    payload = (json.dumps({"id": cid, "name": "/" + name})
                               if ext == "json" else "log-data")
                    path.write_text(payload)
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    lines.append(f"{digest}  {path.name}\n")
            (archive / "SHA256SUMS").write_text("".join(lines))
            (m1 / "retired-docker.json").write_text(json.dumps({
                "schema_version": 1, "state": "archived_docker_removed",
                "name": expected_name, "id": AUDIT.RETIRE.EXPECTED[expected_name],
                "archive_path": str(archive),
                "archive_sha256_manifest":
                    hashlib.sha256((archive / "SHA256SUMS").read_bytes()).hexdigest()}))
            with mock.patch.object(AUDIT.RETIRE, "evidence") as evidence:
                self.assertEqual(AUDIT.archive_check(root, root, state), archive)
                evidence.assert_called_once()
                (archive / (next(iter(AUDIT.RETIRE.EXPECTED.values()))[:16] + ".log")).write_text("TAMPER")
                with self.assertRaisesRegex(AUDIT.AuditBlocked, "DOCKER_ARCHIVE_FILE_CHANGED"):
                    AUDIT.archive_check(root, root, state)

    def test_docker_inventory_excludes_mazinb_names_and_labels(self):
        old = AUDIT.RETIRE.PROTECTED_ID
        other = "a" * 64
        objects = {
            old: {"Id": old, "Name": "/" + AUDIT.RETIRE.PROTECTED_NAME,
                  "Config": {"Labels": {}}},
            other: {"Id": other, "Name": "/other",
                    "Config": {"Labels": {}}},
        }
        def simulate(*args):
            if args[:3] == ("docker", "ps", "-aq"):
                return "\n".join(objects) + "\n"
            if args[:2] == ("docker", "inspect"):
                return json.dumps([objects[x] for x in args[2:]])
            if args[:3] == ("docker", "image", "inspect"):
                return "[]"
            raise AssertionError(args)
        with mock.patch.object(AUDIT, "command", side_effect=simulate):
            AUDIT.docker_check()
            objects[other]["Config"]["Labels"]["qwen38.abtrial"] = "mazinb"
            with self.assertRaisesRegex(AUDIT.AuditBlocked, "UNEXPECTED_MAZINB"):
                AUDIT.docker_check()

    def test_host_success_requires_all_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            state = home / "state"
            state.mkdir()
            (state / "install.env").write_text("test")
            model_root = home / "models"
            model_root.mkdir()
            model = model_root / "orcarouter"
            model.mkdir()
            with mock.patch.object(AUDIT, "parse_install", return_value={
                    "PHASE": "complete", "MODEL_PROFILE": "orcarouter", "MODEL_DIR": str(model)}), \
                 mock.patch.object(AUDIT, "archive_check"), \
                 mock.patch.object(AUDIT, "docker_check"), \
                 mock.patch.object(AUDIT, "systemd_check") as svc, \
                 mock.patch.object(AUDIT, "sockets_check"), \
                 mock.patch.object(AUDIT, "processes_check"):
                AUDIT.inspect(home, state)
                svc.assert_called_once_with(home)


if __name__ == "__main__":
    unittest.main()
