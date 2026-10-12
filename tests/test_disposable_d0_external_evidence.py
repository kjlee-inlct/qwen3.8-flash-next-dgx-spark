"""Purely offline D0 owner/isolation/restore artifact-chain fixture tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_disposable_d0_preflight import base_inventory, base_policy
from test_disposable_d0_receipt_review import fake_receipt

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifecycle" / "disposable-d0-external-evidence-review.py"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def standard_manifest(policy: bytes, inventory: bytes, receipt: bytes, proofs: dict[str, bytes]) -> dict:
    host = base_inventory()["host"]["machine_id_sha256"]
    daemon = base_inventory()["docker"]["daemon_id"]
    return {
        "schema_version": 1,
        "source_sha": "a" * 40,
        "policy_sha256": digest(policy),
        "inventory_sha256": digest(inventory),
        "receipt_sha256": digest(receipt),
        "owner": {
            "actor": "owner-person", "host_machine_sha256": host,
            "docker_daemon_id": daemon, "disposable": True,
            "permitted_scope": "D0_READ_ONLY_REVIEW",
            "evidence_sha256": digest(proofs["owner"]),
        },
        "isolation": {
            "actor": "outside-reviewer",
            "host_machine_sha256": host, "docker_daemon_id": daemon,
            "no_external_users": True, "no_shared_volumes": True,
            "no_production_credentials": True,
            "evidence_sha256": digest(proofs["isolation"]),
        },
        "restore": {
            "actor": "restore-witness",
            "host_machine_sha256": host,
            "restore_point": "snapshot-before-test",
            "test_data_only": True, "drill_result": "PASS_ASSERTED",
            "evidence_sha256": digest(proofs["restore"]),
        },
    }


class D0ExternalEvidenceTests(unittest.TestCase):
    def review(
        self, *, manifest_mutation=None, receipt_mutation=None,
        proof_mutation=None, symlink=None, raw_manifest=None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {name: root / (name + ".json") for name in (
                "policy", "inventory", "crosscheck", "manifest",
            )}
            for name, item in (
                ("policy", base_policy()), ("inventory", base_inventory()),
            ):
                paths[name].write_text(json.dumps(item), encoding="utf-8")
            receipt = fake_receipt(paths["policy"].read_bytes(), paths["inventory"].read_bytes())
            if receipt_mutation is not None:
                receipt_mutation(receipt)
            paths["crosscheck"].write_text(json.dumps(receipt), encoding="utf-8")

            proofs = {
                "owner": b"fixture owner confirmation - untrusted",
                "isolation": b"fixture docker inventory and exclusivity - untrusted",
                "restore": b"fixture snapshot restore result - untrusted",
            }
            artifact_paths = {}
            for name, content in proofs.items():
                path = root / (name + ".bin")
                path.write_bytes(content)
                artifact_paths[name] = path
            manifest = standard_manifest(
                paths["policy"].read_bytes(), paths["inventory"].read_bytes(),
                paths["crosscheck"].read_bytes(), proofs,
            )
            if proof_mutation is not None:
                proof_mutation(artifact_paths)
            if manifest_mutation is not None:
                manifest_mutation(manifest)
            paths["manifest"].write_text(
                raw_manifest if raw_manifest is not None else json.dumps(manifest),
                encoding="utf-8",
            )
            if symlink:
                old = paths[symlink]
                link = root / (symlink + ".link")
                link.symlink_to(old)
                paths[symlink] = link
            snapshot = {name: path.read_bytes() for name, path in paths.items()}
            cmd = [
                sys.executable, str(SCRIPT),
                "--policy", str(paths["policy"]),
                "--inventory", str(paths["inventory"]),
                "--crosscheck", str(paths["crosscheck"]),
                "--manifest", str(paths["manifest"]),
                "--owner-evidence", str(artifact_paths["owner"]),
                "--isolation-evidence", str(artifact_paths["isolation"]),
                "--restore-evidence", str(artifact_paths["restore"]),
            ]
            result = subprocess.run(
                cmd, cwd=ROOT, capture_output=True, text=True,
                check=False, timeout=5,
            )
            for name, path in paths.items():
                self.assertEqual(path.read_bytes(), snapshot[name])
            return result

    def rejected(self, result, code=None):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("D0_EXTERNAL_EVIDENCE_REVIEW=REFUSED", result.stdout)
        self.assertIn("D0_ADMISSION=NOT_GRANTED", result.stdout)
        if code:
            self.assertIn("D0_REASON=" + code, result.stdout)

    def test_consistent_assertions_still_never_grant_admission(self):
        r = self.review()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("STRUCTURALLY_CONSISTENT_UNTRUSTED", r.stdout)
        self.assertIn("D0_OWNER_AUTHORIZATION=NOT_AUTHENTICATED", r.stdout)
        self.assertIn("D0_RESTORE_EXECUTION=NOT_INDEPENDENTLY_VERIFIED", r.stdout)
        self.assertIn("D0_ADMISSION=NOT_GRANTED", r.stdout)
        self.assertIn("D1_D5=NOT_AUTHORIZED", r.stdout)

    def test_owner_evidence_file_drift_refused(self):
        def mutate(paths):
            paths["owner"].write_bytes(b"altered owner text")
        self.rejected(self.review(proof_mutation=mutate), "owner_artifact_sha256_mismatch")

    def test_isolation_and_restore_evidence_file_drift_refused(self):
        for role in ("isolation", "restore"):
            with self.subTest(role=role):
                self.rejected(self.review(
                    proof_mutation=lambda paths: paths[role].write_bytes(b"drifted")
                ), role + "_artifact_sha256_mismatch")

    def test_receipt_sha_drift_refused(self):
        self.rejected(self.review(
            manifest_mutation=lambda m: m.update({"receipt_sha256": "f" * 64})
        ), "receipt_sha256_mismatch")

    def test_policy_and_inventory_manifest_digest_drift_refused(self):
        for key in ("policy_sha256", "inventory_sha256"):
            with self.subTest(key=key):
                self.rejected(self.review(
                    manifest_mutation=lambda m: m.update({key: "f" * 64})
                ), key + "_mismatch")

    def test_shared_owner_reviewer_identity_refused(self):
        self.rejected(self.review(
            manifest_mutation=lambda m: m["isolation"].update(
                {"actor": m["owner"]["actor"]}
            )
        ), "evidence_roles_not_distinct")

    def test_host_and_daemon_disagreement_refused(self):
        self.rejected(self.review(
            manifest_mutation=lambda m: m["owner"].update(
                {"host_machine_sha256": "e" * 64}
            )
        ), "external_host_identity_mismatch")
        self.rejected(self.review(
            manifest_mutation=lambda m: m["isolation"].update(
                {"docker_daemon_id": "foreign-daemon"}
            )
        ), "external_daemon_identity_mismatch")

    def test_restore_point_and_drill_claim_refused(self):
        for update in (
            {"restore_point": "wrong-snapshot"},
            {"drill_result": "NOT_RUN"},
            {"test_data_only": False},
        ):
            with self.subTest(update=update):
                self.rejected(self.review(
                    manifest_mutation=lambda m: m["restore"].update(update)
                ), "restore_claim_incomplete_or_mismatched")

    def test_owner_and_isolation_scope_claims_refused(self):
        self.rejected(self.review(
            manifest_mutation=lambda m: m["owner"].update(
                {"permitted_scope": "D1_D5_AUTHORIZED"}
            )
        ), "owner_disposable_scope_not_asserted")
        self.rejected(self.review(
            manifest_mutation=lambda m: m["isolation"].update(
                {"no_shared_volumes": False}
            )
        ), "isolation_claim_incomplete")

    def test_unexpected_and_missing_schema_refused(self):
        self.rejected(self.review(
            manifest_mutation=lambda m: m.update({"unrecognized": "x"})
        ), "external_manifest_schema")
        self.rejected(self.review(
            manifest_mutation=lambda m: m.pop("restore")
        ), "external_manifest_schema")
        self.rejected(self.review(
            manifest_mutation=lambda m: m.update({"schema_version": True})
        ), "external_manifest_version")

    def test_duplicate_keys_and_symlinked_manifest_refused(self):
        self.rejected(self.review(
            raw_manifest='{"schema_version":1,"schema_version":1}'
        ), "invalid_or_unreadable_evidence_chain")
        self.rejected(self.review(symlink="manifest"), "invalid_or_unreadable_evidence_chain")

    def test_empty_or_symlinked_proof_refused(self):
        self.rejected(self.review(
            proof_mutation=lambda paths: paths["owner"].write_bytes(b"")
        ), "unsafe_or_empty_external_artifact")
        def symlink(paths):
            original = paths["owner"]
            replacement = original.with_suffix(".linked")
            replacement.symlink_to(original)
            paths["owner"] = replacement
        self.rejected(self.review(proof_mutation=symlink), "unsafe_or_empty_external_artifact")

    def test_proof_reuse_refused(self):
        def mutate(m):
            m["restore"]["evidence_sha256"] = m["owner"]["evidence_sha256"]
        self.rejected(self.review(
            manifest_mutation=mutate,
            proof_mutation=lambda paths: paths["restore"].write_bytes(
                b"fixture owner confirmation - untrusted"
            ),
        ), "non_distinct_external_artifacts")

    def test_receipt_claim_tampering_stays_refused(self):
        self.rejected(self.review(
            receipt_mutation=lambda r: r.update({"d0_admission": "GRANTED"})
        ), "invalid_or_unreadable_evidence_chain")

    def test_review_does_not_emit_sensitive_evidence_or_authenticity_claim(self):
        r = self.review()
        self.assertEqual(r.returncode, 0)
        for secret in ("protected-daemon", "owner-person", "snapshot-before-test"):
            self.assertNotIn(secret, r.stdout)
        self.assertIn("D0_EXTERNAL_ROLES=CLAIMED_DISTINCT_NOT_AUTHENTICATED", r.stdout)
        self.assertIn("D0_EVIDENCE_FRESHNESS=NOT_VERIFIED", r.stdout)


if __name__ == "__main__":
    unittest.main()
