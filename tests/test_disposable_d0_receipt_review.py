"""Fixture-only D0 receipt binding; never invokes real Docker or systemd."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifecycle" / "disposable-d0-receipt-review.py"

from test_disposable_d0_preflight import base_inventory, base_policy


def fake_receipt(policy_bytes: bytes, inventory_bytes: bytes) -> dict:
    return {
        "schema_version": 1,
        "scope": "ON_HOST_READ_ONLY_ASSERTION_CROSSCHECK",
        "git_sha": "a" * 40,
        "host_identity": "MATCHED_SUPPLIED_INVENTORY_NOT_ATTESTED",
        "docker_daemon": "MATCHED_SUPPLIED_INVENTORY_NOT_ATTESTED",
        "docker_containers": "NONE_REPORTED",
        "configured_service_unit": "NOT_FOUND",
        "candidate_root_mounts": "NONE_DETECTED_IN_SELECTED_ROOTS",
        "independence": "NOT_ATTESTED",
        "d0_admission": "NOT_GRANTED",
        "d1_d5": "NOT_AUTHORIZED",
        "live_host_e2e": "NOT_QUALIFIED",
        "policy_sha256": hashlib.sha256(policy_bytes).hexdigest(),
        "inventory_sha256": hashlib.sha256(inventory_bytes).hexdigest(),
    }


class D0ReceiptReviewTests(unittest.TestCase):
    def run_review(
        self, *, alter_policy=None, alter_inventory=None, alter_receipt=None,
        raw_receipt: str | None = None, symlink: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            policy = base_policy()
            inventory = base_inventory()
            p = root / "policy.json"
            i = root / "inventory.json"
            r = root / "crosscheck.json"
            p.write_text(json.dumps(policy), encoding="utf-8")
            i.write_text(json.dumps(inventory), encoding="utf-8")
            receipt = fake_receipt(p.read_bytes(), i.read_bytes())
            if alter_policy is not None:
                alter_policy(policy)
                p.write_text(json.dumps(policy), encoding="utf-8")
            if alter_inventory is not None:
                alter_inventory(inventory)
                i.write_text(json.dumps(inventory), encoding="utf-8")
            if alter_receipt is not None:
                alter_receipt(receipt)
            r.write_text(
                raw_receipt if raw_receipt is not None else json.dumps(receipt),
                encoding="utf-8",
            )
            if symlink:
                link = root / "linked.json"
                link.symlink_to(r)
                r = link
            p_before = p.read_bytes()
            i_before = i.read_bytes()
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--policy", str(p),
                 "--inventory", str(i), "--crosscheck", str(r)],
                cwd=ROOT, capture_output=True, text=True, timeout=5, check=False,
            )
            self.assertEqual(p.read_bytes(), p_before)
            self.assertEqual(i.read_bytes(), i_before)
            return result

    def check_refusal(self, result, reason: str | None = None):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("D0_RECEIPT_REVIEW=REFUSED", result.stdout)
        self.assertIn("D0_ADMISSION=NOT_GRANTED", result.stdout)
        if reason is not None:
            self.assertIn("D0_REASON=" + reason, result.stdout)

    def test_matching_untrusted_receipt_never_grants_admission(self):
        result = self.run_review()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("D0_RECEIPT_REVIEW=CONSISTENT_UNTRUSTED", result.stdout)
        self.assertIn("D0_RECEIPT_FRESHNESS=NOT_VERIFIED", result.stdout)
        self.assertIn("D0_EXTERNAL_ATTESTATION=NOT_VERIFIED", result.stdout)
        self.assertIn("D0_ADMISSION=NOT_GRANTED", result.stdout)

    def test_policy_bytes_drift_is_refused(self):
        result = self.run_review(alter_policy=lambda p: p.update(
            {"protected_machine_id_hashes": ["d" * 64]}
        ))
        self.check_refusal(result, "policy_sha256_mismatch")

    def test_inventory_bytes_drift_is_refused(self):
        result = self.run_review(alter_inventory=lambda i: i["host"].update(
            {"restore_point": "another-snapshot"}
        ))
        self.check_refusal(result, "inventory_sha256_mismatch")

    def test_git_sha_drift_refused(self):
        self.check_refusal(
            self.run_review(alter_receipt=lambda r: r.update({"git_sha": "f" * 40})),
            "receipt_git_sha_mismatch",
        )

    def test_modified_receipt_admission_claim_refused(self):
        for key, value in (
            ("d0_admission", "GRANTED"),
            ("independence", "ATTESTED"),
            ("d1_d5", "AUTHORIZED"),
            ("live_host_e2e", "QUALIFIED"),
            ("docker_containers", "UNKNOWN"),
        ):
            with self.subTest(key=key):
                self.check_refusal(
                    self.run_review(alter_receipt=lambda r: r.update({key: value})),
                    "unexpected_receipt_claim",
                )

    def test_missing_extra_and_bad_schema_fields_refused(self):
        for mutation, reason in (
            (lambda r: r.pop("policy_sha256"), "unexpected_receipt_schema"),
            (lambda r: r.update({"unknown": "x"}), "unexpected_receipt_schema"),
            (lambda r: r.update({"schema_version": True}), "unexpected_receipt_schema_version"),
            (lambda r: r.update({"policy_sha256": "g" * 64}), "invalid_receipt_digest"),
        ):
            with self.subTest(reason=reason):
                self.check_refusal(self.run_review(alter_receipt=mutation), reason)

    def test_duplicate_key_and_symlinked_receipt_refused(self):
        self.check_refusal(
            self.run_review(raw_receipt='{"git_sha":"a","git_sha":"b"}'),
            "invalid_or_incomplete_evidence",
        )
        self.check_refusal(
            self.run_review(symlink=True),
            "invalid_or_incomplete_evidence",
        )

    def test_invalid_policy_remains_refused_before_receipt_claim(self):
        self.check_refusal(self.run_review(
            alter_policy=lambda p: p.update({"protected_machine_id_hashes": []})
        ), "invalid_or_incomplete_evidence")

    def test_readonly_cli_reports_no_sensitive_values(self):
        result = self.run_review(alter_receipt=lambda r: r.update(
            {"git_sha": "f" * 40}
        ))
        self.check_refusal(result, "receipt_git_sha_mismatch")
        self.assertNotIn("protected-daemon", result.stdout)
        self.assertNotIn("/srv/production-models", result.stdout)

    def test_replay_with_same_bytes_is_not_proof_of_freshness(self):
        result = self.run_review()
        self.assertEqual(result.returncode, 0)
        self.assertIn("D0_RECEIPT_FRESHNESS=NOT_VERIFIED", result.stdout)


if __name__ == "__main__":
    unittest.main()
