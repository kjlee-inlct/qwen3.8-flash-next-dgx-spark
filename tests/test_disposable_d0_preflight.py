"""Offline, fixture-only D0 policy validation with no live host operations."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "lifecycle" / "disposable-d0-preflight.py"


def base_policy() -> dict:
    return {
        "schema_version": 1,
        "expected_repo": "kjlee-inlct/qwen3.8-flash-next-dgx-spark",
        "expected_sha": "a" * 40,
        "protected_machine_id_hashes": ["b" * 64],
        "protected_docker_daemon_ids": ["protected-daemon"],
        "forbidden_roots": ["/srv/production-models", "/srv/production-states"],
    }


def base_inventory() -> dict:
    return {
        "schema_version": 1,
        "git": {
            "sha": "a" * 40,
            "origin": "https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark.git",
            "clean": True,
        },
        "host": {
            "machine_id_sha256": "c" * 64,
            "host_id": "disposable-test-vm",
            "architecture": "x86_64",
            "owner_declares_disposable": True,
            "restore_point": "snapshot-before-test",
        },
        "docker": {
            "daemon_id": "disposable-daemon",
            "context": "isolated-fixture",
            "isolated": True,
            "external_users": False,
        },
        "paths": {
            "work_root": "/srv/d0-work",
            "model_root": "/srv/d0-model",
            "log_root": "/srv/d0-logs",
        },
        "fixture": {
            "model_bytes": 4096,
            "is_production_checkpoint": False,
            "owned": True,
        },
        "service": {
            "unit": "qwen38-d0-fixture.service",
            "exclusive": True,
        },
        "pending_transactions": [],
    }


class DisposableD0PreflightTests(unittest.TestCase):
    def test_same_validated_bytes_have_stable_sha256_digest(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("d0_offline_test", SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "policy.json"
            data = json.dumps(base_policy()).encode("utf-8")
            file.write_bytes(data)
            parsed, actual_hash = module.read_json_with_digest(file)
            self.assertEqual(parsed, base_policy())
            self.assertEqual(actual_hash, module.hashlib.sha256(data).hexdigest())

    def run_check(
        self, policy: dict | None = None, inventory: dict | None = None,
        *, raw_policy: str | None = None, as_symlink: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            policy_path = root / "policy.json"
            inventory_path = root / "inventory.json"
            policy_path.write_text(
                raw_policy if raw_policy is not None else json.dumps(
                    base_policy() if policy is None else policy
                ), encoding="utf-8"
            )
            inventory_path.write_text(
                json.dumps(base_inventory() if inventory is None else inventory),
                encoding="utf-8",
            )
            if as_symlink:
                alias = root / "policy-symlink.json"
                alias.symlink_to(policy_path)
                policy_path = alias
            original = inventory_path.read_bytes()
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--policy", str(policy_path),
                 "--inventory", str(inventory_path)],
                capture_output=True, text=True, check=False, timeout=5,
            )
            self.assertEqual(inventory_path.read_bytes(), original)
            return result

    def test_complete_static_evidence_never_grants_live_admission(self) -> None:
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("D0_STATIC_REVIEW=READY_FOR_INDEPENDENT_REVIEW", result.stdout)
        self.assertIn("D0_ADMISSION=NOT_GRANTED", result.stdout)
        self.assertIn("D0_LIVE_E2E=NOT_AUTHORIZED", result.stdout)

    def check_rejected(self, policy: dict, inv: dict, reason: str) -> None:
        result = self.run_check(policy, inv)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("D0_STATIC_REVIEW=REFUSED", result.stdout)
        self.assertIn("D0_REFUSAL=" + reason, result.stdout)
        self.assertIn("D0_ADMISSION=NOT_GRANTED", result.stdout)

    def test_known_protected_host_and_daemon_are_refused(self) -> None:
        policy = base_policy()
        for field, value, reason in (
            ("host", "b" * 64, "protected_host_identity"),
            ("docker", "protected-daemon", "protected_docker_daemon"),
        ):
            inventory = base_inventory()
            if field == "host":
                inventory["host"]["machine_id_sha256"] = value
            else:
                inventory["docker"]["daemon_id"] = value
            with self.subTest(field=field):
                self.check_rejected(policy, inventory, reason)

    def test_unknown_protected_identity_or_missing_attestation_refused(self) -> None:
        p = base_policy()
        p["protected_machine_id_hashes"] = []
        self.check_rejected(p, base_inventory(), "protected_machine_set")
        i = base_inventory()
        i["host"]["owner_declares_disposable"] = False
        self.check_rejected(base_policy(), i, "disposable_owner_declaration_missing")

    def test_dirty_checkout_origin_and_sha_are_refused(self) -> None:
        for key, value, reason in (
            ("clean", False, "dirty_or_unverified_checkout"),
            ("origin", "https://github.com/other/repo", "unexpected_git_origin"),
            ("sha", "d" * 40, "unexpected_checkout_sha"),
        ):
            i = base_inventory()
            i["git"][key] = value
            with self.subTest(key=key):
                self.check_rejected(base_policy(), i, reason)

    def test_unsafe_disposable_roots_refused(self) -> None:
        for root, reason in (
            ("/srv/production-models/test", "overlap_with_protected_root"),
            ("/srv/d0-work/../d0-model", "unsafe_model_root"),
            ("/srv/d0-work/subdir", "overlapping_disposable_roots"),
            ("/var/lib/docker/containers", "unsafe_system_path"),
        ):
            i = base_inventory()
            i["paths"]["model_root"] = root
            with self.subTest(root=root):
                self.check_rejected(base_policy(), i, reason)

    def test_shared_daemon_external_users_and_production_service_refused(self) -> None:
        for field, value, reason in (
            ("context", "default", "shared_or_default_docker_context"),
            ("external_users", True, "docker_isolation_unproven"),
        ):
            i = base_inventory()
            i["docker"][field] = value
            with self.subTest(field=field):
                self.check_rejected(base_policy(), i, reason)
        i = base_inventory()
        i["service"]["unit"] = "qwen38-flash-next.service"
        self.check_rejected(base_policy(), i, "nonexclusive_or_production_service")

    def test_fixture_and_pending_transactions_refused(self) -> None:
        i = base_inventory()
        i["fixture"]["is_production_checkpoint"] = True
        self.check_rejected(base_policy(), i, "fixture_ownership_or_production_risk")
        i = base_inventory()
        i["fixture"]["model_bytes"] = 80 * 1024 * 1024
        self.check_rejected(base_policy(), i, "fixture_size_not_bounded")
        i = base_inventory()
        i["pending_transactions"] = ["update"]
        self.check_rejected(base_policy(), i, "pending_or_unknown_transactions")

    def test_symlink_duplicate_and_oversized_policy_are_refused(self) -> None:
        result = self.run_check(as_symlink=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("D0_REFUSAL=unsafe_or_oversized_evidence_file", result.stdout)
        result = self.run_check(raw_policy='{"schema_version":1,"schema_version":1}')
        self.assertEqual(result.returncode, 2)
        self.assertIn("D0_REFUSAL=duplicate_json_field", result.stdout)
        result = self.run_check(raw_policy=' ' * 70000)
        self.assertEqual(result.returncode, 2)
        self.assertIn("D0_REFUSAL=unsafe_or_oversized_evidence_file", result.stdout)

    def test_unexpected_fields_and_boolean_schema_version_refused(self) -> None:
        p = base_policy()
        p["schema_version"] = True
        self.check_rejected(p, base_inventory(), "policy_version")
        i = base_inventory()
        i["extra"] = "unexpected"
        self.check_rejected(base_policy(), i, "inventory_schema")


if __name__ == "__main__":
    unittest.main()
