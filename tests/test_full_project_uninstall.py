"""Isolated full-project wipe-engine policy tests; never use real Docker or sudo."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/lifecycle/full-project-uninstall.py"
SPEC = importlib.util.spec_from_file_location("qwen_full_reset_fixture", SOURCE)
assert SPEC is not None and SPEC.loader is not None
full = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(full)


class FullProjectUninstallTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.home = self.base / "home"
        self.checkout = self.base / "repo"
        self.state = self.home / ".local/state/qwen38-spark"
        self.data = self.home / ".local/share/qwen38-spark"
        self.model_root = self.home / "models"
        self.hf = self.home / ".cache/huggingface"
        self.units = self.base / "units"
        self.fstab = self.base / "fstab"
        self.swap = self.base / "swap-ple.img"
        for path in (self.state, self.data, self.model_root, self.hf,
                     self.units, self.checkout):
            path.mkdir(parents=True, exist_ok=True)
        self.fstab.write_text("")
        self.scope = {
            "home": str(self.home), "checkout": str(self.checkout),
            "state": str(self.state), "data": str(self.data),
            "models": str(self.model_root), "hf": str(self.hf),
            "units": str(self.units), "fstab": str(self.fstab),
            "swap": str(self.swap),
        }

    def _make_exception_fixture(self):
        import hashlib
        model = self.model_root / "qwen3.8-flash-next-orcarouter"
        model.mkdir()
        (model / "weight.bin").write_bytes(b"abc")
        marker = model / ".qwen38-model-manifest.json"
        marker.write_text(json.dumps({
            "schema_version": 1, "repository": "orcarouter/test",
            "revision": "a" * 40, "status": "complete",
            "files": [{"path": "weight.bin", "size": 3,
                       "sha256": "b" * 64}],
        }))
        model_fp = hashlib.sha256(marker.read_bytes()).hexdigest()
        tag = "vllm-orcarouter-v029:v1"
        image_fp = "sha256:" + "c" * 64
        (self.state / "asset-ownership.json").write_text(json.dumps({
            "schema_version": 1, "assets": [
                {"kind": "model", "locator": str(model), "root": str(self.model_root),
                 "owned": False, "state": "ready",
                 "fingerprint": model_fp, "depends_on": []},
                {"kind": "image", "locator": tag, "root": "",
                 "owned": False, "state": "ready",
                 "fingerprint": image_fp, "depends_on": []},
            ],
        }))
        rows = [
            {"kind": "state-root", "locator": str(self.state),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "data-root", "locator": str(self.data),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "model", "locator": str(model),
             "status": "PRESENT", "ownership": "UNVERIFIED"},
            {"kind": "image", "locator": tag,
             "status": "PRESENT", "ownership": "UNVERIFIED"},
        ]
        baseline = {"schema": 1, "mode": "READ_ONLY_PROJECT_SCOPE",
                    "scope": self.scope, "issues": [], "resources": rows}
        baseline_file = self.home / "review-inventory.json"
        baseline_raw = json.dumps(baseline).encode()
        baseline_file.write_bytes(baseline_raw)
        exception = {
            "schema": 1,
            "inventory_sha256": hashlib.sha256(baseline_raw).hexdigest(),
            "entries": [
                {"kind": "model", "locator": str(model), "fingerprint": model_fp},
                {"kind": "image", "locator": tag, "fingerprint": image_fp},
            ],
        }
        exception_file = self.home / "review-approval.json"
        exception_file.write_text(json.dumps(exception))
        return (rows, model, tag, image_fp, exception_file, baseline_file)

    def test_exact_owner_exception_plans_without_promoting_registry(self) -> None:
        rows, model, tag, image_fp, owner_path, baseline_path = (
            self._make_exception_fixture())
        approval, baseline = full.load_owner_exception(
            owner_path, baseline_path, self.scope)
        observed = {"scope": self.scope, "resources": rows, "issues": []}
        with (patch.object(full.inventory, "gather", return_value=observed),
              patch.object(full.inventory, "reference_audit",
                           return_value={"result": "NO_OBSERVED_CONFLICTS"}),
              patch.object(full.inventory, "model_provenance_audit",
                           return_value={"result": "CONSISTENT_METADATA_NOT_OWNERSHIP"}),
              patch.object(full, "image_identity",
                           return_value={"tag": tag, "id": image_fp}),
              patch.object(full, "inspect_swap", return_value=None),
              patch.object(full, "inspect_image_references", return_value=None)):
            with self.assertRaisesRegex(full.Blocked, "candidate_ownership_not_proven"):
                full.scan(self.scope)
            plan = full.scan(self.scope, approval, baseline)
        self.assertEqual(full.verify_plan(plan), plan)
        self.assertEqual(len([x for x in plan["targets"] if x["kind"] == "model"]), 1)
        self.assertEqual(len([x for x in plan["targets"] if x["kind"] == "image"]), 1)
        self.assertFalse(full.inventory.load_registry(
            self.state / "asset-ownership.json")["assets"][0]["owned"])
        plan["owner_exception"]["entries"][0]["fingerprint"] = "sha256:" + "f" * 64
        with self.assertRaisesRegex(full.Blocked, "integrity"):
            full.verify_plan(plan)

    def test_exception_missing_candidate_or_mismatched_inventory_is_blocked(self) -> None:
        rows, model, tag, image_fp, owner_path, baseline_path = (
            self._make_exception_fixture())
        raw = json.loads(owner_path.read_text())
        raw["entries"] = raw["entries"][:1]
        owner_path.write_text(json.dumps(raw))
        approval, baseline = full.load_owner_exception(
            owner_path, baseline_path, self.scope)
        observed = {"scope": self.scope, "resources": rows, "issues": []}
        with (patch.object(full.inventory, "gather", return_value=observed),
              patch.object(full.inventory, "reference_audit",
                           return_value={"result": "NO_OBSERVED_CONFLICTS"}),
              patch.object(full.inventory, "model_provenance_audit",
                           return_value={"result": "CONSISTENT_METADATA_NOT_OWNERSHIP"})):
            with self.assertRaisesRegex(full.Blocked, "extra_or_missing"):
                full.scan(self.scope, approval, baseline)
        raw["inventory_sha256"] = "f" * 64
        owner_path.write_text(json.dumps(raw))
        with self.assertRaisesRegex(full.Blocked, "inventory_sha_mismatch"):
            full.load_owner_exception(owner_path, baseline_path, self.scope)

    def test_exception_rejects_image_drift_and_foreign_reference(self) -> None:
        rows, model, tag, image_fp, owner_path, baseline_path = (
            self._make_exception_fixture())
        approval, baseline = full.load_owner_exception(
            owner_path, baseline_path, self.scope)
        observed = {"scope": self.scope, "resources": rows, "issues": []}
        with (patch.object(full.inventory, "gather", return_value=observed),
              patch.object(full.inventory, "reference_audit",
                           return_value={"result": "CONFLICTS"})):
            with self.assertRaisesRegex(full.Blocked, "references_not_clear"):
                full.scan(self.scope, approval, baseline)
        with (patch.object(full.inventory, "gather", return_value=observed),
              patch.object(full.inventory, "reference_audit",
                           return_value={"result": "NO_OBSERVED_CONFLICTS"}),
              patch.object(full.inventory, "model_provenance_audit",
                           return_value={"result": "CONSISTENT_METADATA_NOT_OWNERSHIP"}),
              patch.object(full, "image_identity",
                           return_value={"tag": tag, "id": "sha256:" + "f" * 64}),
              patch.object(full, "inspect_swap", return_value=None),
              patch.object(full, "inspect_image_references", return_value=None)):
            with self.assertRaisesRegex(full.Blocked, "owner_exception_image_identity_changed"):
                full.scan(self.scope, approval, baseline)

    def test_exception_input_inside_project_root_is_blocked(self) -> None:
        rows, model, tag, image_fp, owner_path, baseline_path = (
            self._make_exception_fixture())
        inside = self.state / "permission.json"
        inside.write_bytes(owner_path.read_bytes())
        with self.assertRaisesRegex(full.Blocked, "inside_deletion_scope"):
            full.load_owner_exception(inside, baseline_path, self.scope)

    def test_mount_drift_order_only_does_not_authorize_deletion(self) -> None:
        left = {"Type": "bind", "Destination": "/model",
                "Source": "/private/model", "RW": False}
        right = {"Type": "bind", "Destination": "/cache",
                 "Source": "/private/cache", "RW": True}
        result = full.describe_mount_drift([left, right], [right, left])
        self.assertEqual(result["classification"], "ORDER_ONLY")
        self.assertEqual(result["saved_count"], 2)
        self.assertNotIn("/private/", json.dumps(result))

    def test_mount_drift_exposes_only_changed_fields_and_container_destinations(self) -> None:
        old = [
            {"Type": "bind", "Destination": "/model", "Source": "/host/original",
             "RW": False, "Propagation": "rprivate"},
            {"Type": "bind", "Destination": "/cache", "Source": "/host/cache",
             "RW": True},
        ]
        fresh = [
            {"Type": "bind", "Destination": "/model", "Source": "/host/different",
             "RW": False, "Propagation": "rprivate"},
            {"Type": "bind", "Destination": "/cache", "Source": "/host/cache",
             "RW": False},
        ]
        detail = full.describe_mount_drift(old, fresh)
        self.assertEqual(detail["classification"], "CONTENT_CHANGED")
        self.assertEqual(detail["mount_change_count"], 2)
        entries = {x["destination"]: x for x in detail["mount_changes"]}
        self.assertEqual(entries["/model"]["changed_fields"], ["Source"])
        self.assertEqual(entries["/cache"]["changed_fields"], ["RW"])
        self.assertNotIn("/host/", json.dumps(detail))
        removed = full.describe_mount_drift(old, [fresh[0]])
        self.assertEqual(removed["mount_change_count"], 2)
        self.assertEqual(
            next(x["status"] for x in removed["mount_changes"]
                 if x["destination"] == "/cache"), "REMOVED")

    def test_mount_drift_ambiguous_metadata_is_not_misclassified_as_order(self) -> None:
        entry = {"Type": "bind", "Destination": "/model",
                 "Source": "/host/model"}
        detail = full.describe_mount_drift([entry, entry], [entry])
        self.assertEqual(detail["classification"], "AMBIGUOUS_MOUNT_IDENTITIES")
        detail = full.describe_mount_drift([{"Source": "/host/model"}], [entry])
        self.assertEqual(detail["classification"], "AMBIGUOUS_MOUNT_IDENTITIES")
        detail = full.describe_mount_drift("not-list", [entry])
        self.assertEqual(detail["classification"], "UNVERIFIABLE_MOUNT_METADATA")

    def test_compare_receipts_reports_mount_detail_without_mutation(self) -> None:
        cid = "b" * 64
        old_mount = [{"Type": "bind", "Destination": "/model",
                      "Source": "/private/a", "RW": False}]
        new_mount = [{"Type": "bind", "Destination": "/model",
                      "Source": "/private/b", "RW": False}]
        def receipt(mounts: list) -> dict:
            body = {"schema": 1, "mode": "EXACT_PROJECT_RESET",
                    "scope": self.scope, "targets": [
                        {"kind": "container", "id": cid, "fingerprint": {
                            "id": cid, "mounts": mounts,
                        }},
                    ]}
            return {**body, "sha256": full.digest(body)}
        old, new = receipt(old_mount), receipt(new_mount)
        result = full.compare_receipts(old, new)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["fields"], ["fingerprint.mounts"])
        self.assertEqual(result[0]["mounts"]["classification"], "CONTENT_CHANGED")
        self.assertEqual(result[0]["mounts"]["mount_change_count"], 1)
        self.assertNotIn("/private/", json.dumps(result))

    def test_read_only_receipt_comparison_reports_only_safe_changed_fields(self) -> None:
        model = self.model_root / "qwen3.8-flash-next-orcarouter"
        container_id = "a" * 64
        body = {"schema": 1, "mode": "EXACT_PROJECT_RESET",
                "scope": self.scope, "targets": [
                    {"kind": "container", "id": container_id, "fingerprint": {
                        "id": container_id, "image_id": "sha256:" + "b" * 64,
                        "running": False, "status": "exited",
                        "labels": {"qwen38.profile": "orcarouter"},
                    }},
                    {"kind": "model", "id": str(model), "fingerprint": {
                        "dev": 1, "ino": 2, "mode": 16877,
                    }},
                ]}
        original = {**body, "sha256": full.digest(body)}
        self.assertEqual(full.compare_receipts(original, original), [])
        changed = json.loads(json.dumps(original))
        changed["targets"][0]["fingerprint"]["status"] = "running"
        changed["targets"][1]["fingerprint"]["ino"] = 3
        changed["sha256"] = full.digest(
            {k: v for k, v in changed.items() if k != "sha256"})
        delta = full.compare_receipts(original, changed)
        self.assertEqual(len(delta), 2)
        self.assertEqual(delta[0]["kind"], "container")
        self.assertEqual(delta[0]["fields"], ["fingerprint.status"])
        self.assertEqual(delta[1]["kind"], "model")
        self.assertEqual(delta[1]["fields"], ["fingerprint.ino"])
        self.assertNotIn("sha256:" + "b" * 64, json.dumps(delta))

    def test_diagnose_does_not_call_mutating_executor(self) -> None:
        import contextlib
        import io
        import sys
        lock = self.state / "operation.lock"
        lock.write_text("")
        body = {"schema": 1, "mode": "EXACT_PROJECT_RESET",
                "scope": self.scope, "targets": []}
        plan = {**body, "sha256": full.digest(body)}
        argv = [
            str(SOURCE), "diagnose", "--plan-file",
            str(self.home / "saved-receipt.json"),
            "--home", str(self.home), "--checkout", str(self.checkout),
            "--state-home", str(self.home / ".local/state"),
            "--data-home", str(self.home / ".local/share"),
            "--model-root", str(self.model_root), "--hf-home", str(self.hf),
            "--unit-dir", str(self.units), "--fstab", str(self.fstab),
            "--swap", str(self.swap),
        ]
        printed = io.StringIO()
        with (patch.object(sys, "argv", argv),
              patch.object(full, "load_plan", return_value=plan),
              patch.object(full, "scan", return_value=plan),
              patch.object(full, "execute", side_effect=AssertionError(
                  "diagnose may not execute any deletion")),
              contextlib.redirect_stdout(printed)):
            code = full.main()
        self.assertEqual(code, 0)
        self.assertIn("PLAN_MATCHES_CURRENT_INVENTORY", printed.getvalue())
        self.assertIn("HOST_DELETION=NOT_PERFORMED", printed.getvalue())
        self.assertTrue(lock.is_file())

    def test_receipt_sha_tamper_is_blocked(self) -> None:
        body = {"schema": 1, "mode": "EXACT_PROJECT_RESET",
                "scope": self.scope, "targets": []}
        raw = {**body, "sha256": full.digest(body)}
        self.assertEqual(full.verify_plan(raw), raw)
        raw["targets"] = [{"kind": "model", "id": "/foreign"}]
        with self.assertRaisesRegex(full.Blocked, "integrity"):
            full.verify_plan(raw)

    def test_short_docker_id_refused(self) -> None:
        with self.assertRaisesRegex(full.Blocked, "full_sha"):
            full.docker_identity("123abc")

    def test_docker_mount_order_is_canonical_and_content_remains_exact(self) -> None:
        cid = "b" * 64
        mounts = [
            {"Type": "bind", "Destination": "/model",
             "Source": "/home/project/models/model", "RW": False,
             "Propagation": "rprivate"},
            {"Type": "bind", "Destination": "/cache",
             "Source": "/home/project/.cache", "RW": True,
             "Propagation": "rprivate"},
            {"Type": "volume", "Destination": "/scratch",
             "Name": "qwen38-scratch", "Source": "/var/lib/docker/volumes/a",
             "RW": True},
        ]
        obj = {"Id": cid, "Name": "/qwen38-m1-test",
               "Config": {"Labels": {"qwen38.bench": "mazinb"}},
               "State": {"Running": False, "Status": "exited"},
               "Image": "sha256:" + "c" * 64, "Mounts": mounts}
        with patch.object(full, "json_command", return_value=[obj]):
            initial = full.docker_identity(cid)
        with patch.object(full, "json_command",
                          return_value=[{**obj, "Mounts": mounts[::-1]}]):
            reversed_identity = full.docker_identity(cid)
        self.assertEqual(initial, reversed_identity)
        self.assertEqual(len(initial["mounts"]), 3)
        self.assertEqual(full.digest(initial), full.digest(reversed_identity))

        shifted = [dict(m) for m in mounts]
        shifted[0]["Source"] = "/home/foreign/models/model"
        with patch.object(full, "json_command",
                          return_value=[{**obj, "Mounts": shifted}]):
            changed = full.docker_identity(cid)
        self.assertNotEqual(initial, changed)
        self.assertNotEqual(full.digest(initial), full.digest(changed))

        flags = [dict(m) for m in mounts]
        flags[1]["RW"] = False
        with patch.object(full, "json_command",
                          return_value=[{**obj, "Mounts": flags}]):
            changed_flags = full.docker_identity(cid)
        self.assertNotEqual(initial, changed_flags)

        doubled = mounts + [mounts[0]]
        with patch.object(full, "json_command",
                          return_value=[{**obj, "Mounts": doubled}]):
            duplicate = full.docker_identity(cid)
        self.assertEqual(len(duplicate["mounts"]), 4)
        self.assertNotEqual(initial, duplicate)

    def test_plan_digest_stable_across_docker_mount_reorder(self) -> None:
        cid = "d" * 64
        mounts = [
            {"Type": "bind", "Destination": "/model",
             "Source": "/home/project/model", "RW": False},
            {"Type": "bind", "Destination": "/cache",
             "Source": "/home/project/cache", "RW": False},
        ]
        obj = {"Id": cid, "Name": "/qwen38-trial",
               "Config": {"Labels": {"qwen38.test": "yes"}},
               "State": {"Running": False, "Status": "exited"},
               "Image": "sha256:" + "e" * 64}
        rows = [
            {"kind": "state-root", "locator": str(self.state),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "data-root", "locator": str(self.data),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "container", "locator": cid,
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
        ]
        with (patch.object(full.inventory, "gather",
                           return_value={"issues": [], "resources": rows}),
              patch.object(full, "inspect_swap", return_value=None),
              patch.object(full, "inspect_image_references", return_value=None)):
            with patch.object(full, "json_command",
                              return_value=[{**obj, "Mounts": mounts}]):
                first = full.scan(self.scope)
            with patch.object(full, "json_command",
                              return_value=[{**obj, "Mounts": mounts[::-1]}]):
                second = full.scan(self.scope)
        self.assertEqual(first, second)
        self.assertEqual(first["sha256"], second["sha256"])

    def test_apply_refuses_actual_mount_content_drift_before_docker_rm(self) -> None:
        cid = "f" * 64
        original = [{"Type": "bind", "Destination": "/model",
                     "Source": "/safe/model", "RW": False}]
        moved = [{"Type": "bind", "Destination": "/model",
                  "Source": "/foreign/model", "RW": False}]
        obj = {"Id": cid, "Name": "/qwen38-trial",
               "Config": {"Labels": {"qwen38.test": "yes"}},
               "State": {"Running": False, "Status": "exited"},
               "Image": "sha256:" + "e" * 64}
        with patch.object(full, "json_command",
                          return_value=[{**obj, "Mounts": original}]):
            first = full.docker_identity(cid)
        with (patch.object(full, "json_command",
                           return_value=[{**obj, "Mounts": moved}]),
              patch.object(full, "run", side_effect=AssertionError(
                  "Docker removal must not be reached"))):
            with self.assertRaisesRegex(full.Blocked, "container_identity_changed"):
                full.execute({"scope": self.scope, "targets": [
                    {"kind": "container", "id": cid, "fingerprint": first},
                ]})

    def test_invalid_docker_mount_rows_remain_fail_closed(self) -> None:
        cid = "e" * 64
        obj = {"Id": cid, "Name": "/qwen38-test",
               "Config": {"Labels": {"qwen38.test": "yes"}},
               "State": {"Running": False, "Status": "exited"},
               "Image": "sha256:" + "a" * 64}
        for bad in (None, [None], ["not-a-dict"], [{"Destination": "/model"}, 3]):
            with self.subTest(mounts=repr(bad)):
                with patch.object(full, "json_command",
                                  return_value=[{**obj, "Mounts": bad}]):
                    with self.assertRaisesRegex(full.Blocked, "inspect_incomplete"):
                        full.docker_identity(cid)

    def test_docker_exact_id_must_match_inspect_and_project_label(self) -> None:
        cid = "a" * 64
        baseline = {"Id": cid, "Name": "/qwen38-mazinb-m1-R2",
                    "Config": {"Labels": {"qwen38.abtrial": "mazinb"}},
                    "State": {"Running": False, "Status": "exited"},
                    "Image": "sha256:" + "b" * 64, "Mounts": []}
        with patch.object(full, "json_command", return_value=[baseline]):
            result = full.docker_identity(cid)
        self.assertEqual(result["id"], cid)
        self.assertEqual(result["labels"]["qwen38.abtrial"], "mazinb")
        foreign = {**baseline, "Config": {"Labels": {"app": "unrelated"}}}
        with patch.object(full, "json_command", return_value=[foreign]):
            with self.assertRaisesRegex(full.Blocked, "ownership_label"):
                full.docker_identity(cid)
        wrong = {**baseline, "Id": "b" * 64}
        with patch.object(full, "json_command", return_value=[wrong]):
            with self.assertRaisesRegex(full.Blocked, "identity_mismatch"):
                full.docker_identity(cid)

    def test_legacy_canonical_container_requires_exact_manifest_model_bind(self) -> None:
        model = self.model_root / "qwen3.8-flash-next-orcarouter"
        model.mkdir()
        foreign = self.home / "foreign" / model.name
        foreign.mkdir(parents=True)
        # A foreign model may have the same recognizable basename.
        (self.state / "install.env").write_text("FIXTURE")
        rows = [{"kind": "model", "locator": str(model),
                 "status": "PRESENT", "ownership": "UNVERIFIED"}]
        baseline = {"name": "/qwen38-flash-next",
                    "mounts": [{"Type": "bind", "Source": str(model),
                                "Destination": "/model", "RW": False}],
                    "image_id": "sha256:" + "d" * 64}
        with patch.object(full.inventory, "parse_install",
                          return_value={"MODEL_DIR": str(model)}):
            full.verify_legacy_canonical_model_mount(
                baseline, self.scope, rows)
            other = {"name": baseline["name"],
                     "mounts": [{"Type": "bind", "Source": str(foreign),
                                 "Destination": "/model", "RW": False}]}
            with self.assertRaisesRegex(
                    full.Blocked, "canonical_container_manifest_model_mount_mismatch"):
                full.verify_legacy_canonical_model_mount(other, self.scope, rows)
            writable = {"name": baseline["name"],
                        "mounts": [{**baseline["mounts"][0], "RW": True}]}
            with self.assertRaisesRegex(
                    full.Blocked, "canonical_container_manifest_model_mount_mismatch"):
                full.verify_legacy_canonical_model_mount(
                    writable, self.scope, rows)
            with self.assertRaisesRegex(
                    full.Blocked, "canonical_container_model_not_in_inventory"):
                full.verify_legacy_canonical_model_mount(
                    baseline, self.scope, [])

    def test_legacy_canonical_container_scan_rejects_similar_foreign_bind(self) -> None:
        model = self.model_root / "qwen3.8-flash-next-orcarouter"
        model.mkdir()
        foreign = self.home / "third-party" / model.name
        foreign.mkdir(parents=True)
        (foreign / "KEEP").write_text("foreign")
        (self.state / "install.env").write_text("FIXTURE")
        cid = "a" * 64
        rows = [
            {"kind": "state-root", "locator": str(self.state),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "data-root", "locator": str(self.data),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "model", "locator": str(model),
             "status": "PRESENT", "ownership": "INSTALLER_OWNED"},
            {"kind": "container", "locator": cid,
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
        ]
        identity = {"id": cid, "name": "/qwen38-flash-next",
                    "mounts": [{"Type": "bind", "Source": str(foreign),
                                "Destination": "/model", "RW": False}],
                    "image_id": "sha256:" + "d" * 64}
        with (patch.object(full.inventory, "gather",
                           return_value={"issues": [], "resources": rows}),
              patch.object(full.inventory, "parse_install",
                           return_value={"MODEL_DIR": str(model)}),
              patch.object(full, "docker_identity", return_value=identity)):
            with self.assertRaisesRegex(
                    full.Blocked, "canonical_container_manifest_model_mount_mismatch"):
                full.scan(self.scope)
        self.assertEqual((foreign / "KEEP").read_text(), "foreign")

    def test_docker_preflight_blocks_foreign_image_dependency(self) -> None:
        foreign = "f" * 64
        managed = "a" * 64
        image = "sha256:" + "b" * 64
        def fake_json(*argv: str):
            self.assertEqual(argv[-1], foreign)
            return [{"Id": foreign, "Image": image, "Mounts": []}]
        with (patch.object(full.inventory, "run_docker", return_value=[
                  {"ID": managed}, {"ID": foreign}]),
              patch.object(full, "json_command", side_effect=fake_json)):
            with self.assertRaisesRegex(full.Blocked, "external_container"):
                full.inspect_image_references(
                    [{"id": managed}],
                    [{"kind": "image", "id": "vllm-orcarouter-v029:v1",
                      "fingerprint": {"id": image}}],
                )

    def test_docker_preflight_blocks_foreign_volume_dependency(self) -> None:
        foreign = "f" * 64
        with (patch.object(full.inventory, "run_docker", return_value=[
                  {"ID": foreign}]),
              patch.object(full, "json_command", return_value=[
                  {"Id": foreign, "Image": "sha256:" + "e" * 64,
                   "Mounts": [{"Name": "qwen38-temp"}]}])):
            with self.assertRaisesRegex(full.Blocked, "volume_used"):
                full.inspect_image_references(
                    [], [], [{"kind": "volume", "id": "qwen38-temp"}],
                )

    def test_foreign_docker_bind_mount_blocks_project_file_deletion(self) -> None:
        foreign = "e" * 64
        model = self.model_root / "qwen3.8-flash-next-orcarouter"
        model.mkdir()
        with (patch.object(full.inventory, "run_docker", return_value=[
                  {"ID": foreign}]),
              patch.object(full, "json_command", return_value=[
                  {"Id": foreign, "Image": "sha256:" + "d" * 64,
                   "Mounts": [{"Type": "bind", "Source": str(model),
                               "Destination": "/model"}]}])):
            with self.assertRaisesRegex(full.Blocked, "file_mount_used"):
                full.inspect_image_references(
                    [], [], [], [{"kind": "model", "id": str(model)}],
                )

    def test_prefix_only_foreign_assets_fail_closed_before_identity_lookup(self) -> None:
        # A recognizable name is an inventory hint, not ownership evidence.
        # Even an unused foreign image is not safe to delete.
        foreign_model = self.model_root / "qwen3.8-foreign-model"
        foreign_model.mkdir()
        (foreign_model / "KEEP").write_text("external")
        foreign_cache = self.hf / "hub/models--mazinb--Qwen3.8-Flash-Next"
        foreign_cache.mkdir(parents=True)
        candidates = [
            {"kind": "image", "locator": "vllm-foreign-runtime:v1",
             "status": "PRESENT", "ownership": "UNVERIFIED"},
            {"kind": "model", "locator": str(foreign_model),
             "status": "PRESENT", "ownership": "UNVERIFIED"},
            {"kind": "model-cache", "locator": str(foreign_cache),
             "status": "PRESENT", "ownership": "UNVERIFIED"},
        ]
        base = [
            {"kind": "state-root", "locator": str(self.state),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "data-root", "locator": str(self.data),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
        ]
        for candidate in candidates:
            with self.subTest(kind=candidate["kind"]):
                with (patch.object(full.inventory, "gather",
                                   return_value={"issues": [], "resources": base + [candidate]}),
                      patch.object(full, "image_identity",
                                   side_effect=AssertionError("no image inspection for foreign asset")),
                      patch.object(full, "inspect_swap", return_value=None),
                      patch.object(full, "inspect_image_references", return_value=None)):
                    with self.assertRaisesRegex(
                            full.Blocked,
                            "candidate_ownership_not_proven:" + candidate["kind"]):
                        full.scan(self.scope)
        self.assertEqual((foreign_model / "KEEP").read_text(), "external")
        self.assertTrue(foreign_cache.exists())

    def test_unverified_asset_blocker_lists_candidates_with_bounded_overflow(self) -> None:
        names = [f"vllm-other-{i:02d}:v1" for i in range(14)]
        rows = [
            {"kind": "image", "locator": name,
             "status": "PRESENT", "ownership": "UNVERIFIED"}
            for name in names
        ]
        with patch.object(full.inventory, "gather",
                          return_value={"issues": [], "resources": rows}):
            with self.assertRaises(full.Blocked) as raised:
                full.scan(self.scope)
        message = str(raised.exception)
        self.assertIn("candidate_ownership_not_proven:", message)
        self.assertIn(names[0], message)
        self.assertIn(names[11], message)
        self.assertNotIn(names[12], message)
        self.assertIn("additional_unverified=2", message)

    def test_positive_owned_image_can_enter_exact_identity_bound_plan(self) -> None:
        tag = "vllm-skinny-tp1:v1"
        rows = [
            {"kind": "state-root", "locator": str(self.state),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "data-root", "locator": str(self.data),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "image", "locator": tag,
             "status": "PRESENT", "ownership": "INSTALLER_OWNED"},
        ]
        identity = {"tag": tag, "id": "sha256:" + "b" * 64}
        with (patch.object(full.inventory, "gather",
                           return_value={"issues": [], "resources": rows}),
              patch.object(full, "image_identity", return_value=identity),
              patch.object(full, "inspect_swap", return_value=None),
              patch.object(full, "inspect_image_references", return_value=None)):
            plan = full.scan(self.scope)
        self.assertIn({"kind": "image", "id": tag, "fingerprint": identity},
                      plan["targets"])

    def test_registry_image_id_drift_blocks_plan_even_if_tag_is_owned(self) -> None:
        tag = "vllm-skinny-tp1:v1"
        original = "sha256:" + "a" * 64
        current = "sha256:" + "b" * 64
        (self.state / "asset-ownership.json").write_text(json.dumps({
            "schema_version": 1,
            "assets": [{
                "kind": "image", "locator": tag, "root": "",
                "owned": True, "state": "ready",
                "fingerprint": original, "depends_on": [],
            }],
        }))
        rows = [
            {"kind": "state-root", "locator": str(self.state),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "data-root", "locator": str(self.data),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "image", "locator": tag,
             "status": "PRESENT", "ownership": "INSTALLER_OWNED"},
        ]
        with (patch.object(full.inventory, "gather",
                           return_value={"issues": [], "resources": rows}),
              patch.object(full, "image_identity",
                           return_value={"tag": tag, "id": current}),
              patch.object(full, "inspect_swap", return_value=None),
              patch.object(full, "inspect_image_references", return_value=None)):
            with self.assertRaisesRegex(full.Blocked, "registered_image_id_drift"):
                full.scan(self.scope)

    def test_registered_model_marker_fingerprint_is_checked(self) -> None:
        import hashlib
        model = self.model_root / "qwen3.8-flash-next-mazinb"
        model.mkdir()
        marker = model / ".qwen38-model-manifest.json"
        marker.write_text('{"project":"owned"}')
        original = hashlib.sha256(marker.read_bytes()).hexdigest()
        record = {"owned": True, "state": "ready", "fingerprint": original}
        full.check_recorded_asset_provenance("model", str(model), record)
        marker.write_text('{"project":"foreign"}')
        with self.assertRaisesRegex(full.Blocked, "registered_model_manifest_drift"):
            full.check_recorded_asset_provenance("model", str(model), record)
        marker.unlink()
        with self.assertRaisesRegex(full.Blocked, "registered_model_manifest_missing"):
            full.check_recorded_asset_provenance("model", str(model), record)

    def test_registered_unowned_and_incomplete_assets_never_override_provenance(self) -> None:
        tag = "vllm-skinny-tp1:v1"
        observed = {"tag": tag, "id": "sha256:" + "b" * 64}
        with self.assertRaisesRegex(full.Blocked, "registry_manifest_ownership_conflict"):
            full.check_recorded_asset_provenance(
                "image", tag,
                {"owned": False, "state": "ready", "fingerprint": observed["id"]},
                observed)
        with self.assertRaisesRegex(full.Blocked, "registered_asset_not_fingerprint_ready"):
            full.check_recorded_asset_provenance(
                "image", tag,
                {"owned": True, "state": "claimed", "fingerprint": ""},
                observed)

    def test_plan_scope_rejects_parent_and_model_symlink(self) -> None:
        with self.assertRaisesRegex(full.Blocked, "model_outside"):
            full.scoped_file(self.home, "model", self.scope)
        foreign = self.home / "foreign"
        foreign.mkdir()
        item = self.model_root / "qwen3.8-evil"
        item.symlink_to(foreign)
        with self.assertRaisesRegex(full.Blocked, "symlink"):
            full.scoped_file(item, "model", self.scope)

    def test_managed_release_pointer_links_are_identity_bound_and_not_followed(self) -> None:
        release = self.data / "releases" / ("a" * 40)
        release.mkdir(parents=True)
        (release / "payload").write_text("owned")
        external = self.home / "foreign"
        external.mkdir()
        (external / "KEEP").write_text("foreign")
        current = self.data / "current"
        previous = self.data / "previous"
        current.symlink_to("releases/" + "a" * 40)
        previous.symlink_to("releases/" + "b" * 40)  # retired release
        rows = [
            {"kind": "state-root", "locator": str(self.state),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "data-root", "locator": str(self.data),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "release", "locator": str(current),
             "status": "UNSAFE_SYMLINK", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "release", "locator": str(previous),
             "status": "UNSAFE_SYMLINK", "ownership": "PROJECT_ASSOCIATED"},
        ]
        with (patch.object(full.inventory, "gather",
                           return_value={"issues": [], "resources": rows}),
              patch.object(full, "inspect_swap", return_value=None),
              patch.object(full, "inspect_image_references", return_value=None)):
            plan = full.scan(self.scope)
        links = [x for x in plan["targets"] if x["kind"] == "release-link"]
        self.assertEqual({x["id"] for x in links}, {str(current), str(previous)})
        for link in links:
            self.assertEqual(
                link["fingerprint"],
                full.managed_release_link_identity(Path(link["id"]), self.scope))
        with patch.object(full, "inspect_image_references", return_value=None):
            full.execute(plan)
        self.assertFalse(current.is_symlink())
        self.assertFalse(previous.is_symlink())
        self.assertFalse(self.data.exists())
        self.assertEqual((external / "KEEP").read_text(), "foreign")

    def test_release_link_outside_project_releases_is_blocked(self) -> None:
        external = self.home / "unrelated-release"
        external.mkdir()
        current = self.data / "current"
        current.symlink_to(external)
        with self.assertRaisesRegex(full.Blocked, "release_link_points_outside"):
            full.managed_release_link_identity(current, self.scope)
        self.assertTrue(current.is_symlink())
        self.assertTrue(external.is_dir())

    def test_release_link_identity_drift_blocks_before_file_deletion(self) -> None:
        current = self.data / "current"
        current.symlink_to("releases/" + "a" * 40)
        old = full.managed_release_link_identity(current, self.scope)
        current.unlink()
        current.symlink_to("releases/" + "b" * 40)
        with patch.object(full, "inspect_image_references", return_value=None):
            with self.assertRaisesRegex(full.Blocked, "release_link_drift_during_apply"):
                full.execute({"scope": self.scope, "targets": [
                    {"kind": "release-link", "id": str(current), "fingerprint": old},
                ]})
        self.assertTrue(self.data.is_dir())
        self.assertTrue(current.is_symlink())

    def test_legacy_checkout_model_link_is_planned_and_unlinked_only(self) -> None:
        target = self.model_root / "qwen3.8-flash-next-orcarouter"
        target.mkdir()
        (target / "config.json").write_text("MODEL_DATA")
        link = self.checkout / "model"
        link.symlink_to(target)
        self.assertTrue(link.is_symlink())
        self.assertEqual(full.inventory.path_status(link), "UNSAFE_SYMLINK")
        fingerprint = full.legacy_model_link_identity(link, self.scope)
        self.assertEqual(fingerprint["resolved_target"], str(target))
        rows = [
            {"kind": "model", "locator": str(link),
             "status": "UNSAFE_SYMLINK", "ownership": "UNVERIFIED"},
            {"kind": "model", "locator": str(target),
             "status": "PRESENT", "ownership": "INSTALLER_OWNED"},
            {"kind": "state-root", "locator": str(self.state),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "data-root", "locator": str(self.data),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
        ]
        with (patch.object(full.inventory, "gather",
                           return_value={"issues": [], "resources": rows}),
              patch.object(full, "inspect_swap", return_value=None),
              patch.object(full, "inspect_image_references", return_value=None)):
            plan = full.scan(self.scope)
        link_entry = next(item for item in plan["targets"]
                          if item["kind"] == "legacy-model-link")
        self.assertEqual(link_entry["fingerprint"], fingerprint)
        self.assertIn({"kind": "model", "id": str(target),
                       "fingerprint": next(x["fingerprint"] for x in plan["targets"]
                                           if x["kind"] == "model")},
                      plan["targets"])
        with patch.object(full, "inspect_image_references", return_value=None):
            full.execute(plan)
        self.assertFalse(link.exists())
        self.assertFalse(link.is_symlink())
        self.assertFalse(target.exists())
        self.assertTrue(self.checkout.is_dir())
        self.assertTrue(self.model_root.is_dir())

    def test_legacy_model_link_to_foreign_live_target_stays_blocked(self) -> None:
        foreign = self.home / "unrelated-data"
        foreign.mkdir()
        (foreign / "important.txt").write_text("KEEP")
        link = self.checkout / "model"
        link.symlink_to(foreign)
        with self.assertRaisesRegex(full.Blocked,
                                     "legacy_model_link_target_outside"):
            full.legacy_model_link_identity(link, self.scope)
        self.assertTrue(link.is_symlink())
        self.assertEqual((foreign / "important.txt").read_text(), "KEEP")

    def test_legacy_model_link_to_untracked_project_directory_stays_blocked(self) -> None:
        target = self.model_root / "qwen3.8-flash-next-mazinb"
        target.mkdir()
        link = self.checkout / "model"
        link.symlink_to(target)
        rows = [
            {"kind": "model", "locator": str(link),
             "status": "UNSAFE_SYMLINK", "ownership": "UNVERIFIED"},
            {"kind": "state-root", "locator": str(self.state),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "data-root", "locator": str(self.data),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
        ]
        with (patch.object(full.inventory, "gather",
                           return_value={"issues": [], "resources": rows}),
              patch.object(full, "inspect_swap", return_value=None),
              patch.object(full, "inspect_image_references", return_value=None)):
            with self.assertRaisesRegex(full.Blocked,
                                         "legacy_model_link_target_not_selected"):
                full.scan(self.scope)

    def test_legacy_link_drift_refuses_unlink_and_preserves_targets(self) -> None:
        model = self.model_root / "qwen3.8-flash-next-orcarouter"
        model.mkdir()
        other = self.model_root / "qwen3.8-flash-next-mazinb"
        other.mkdir()
        link = self.checkout / "model"
        link.symlink_to(model)
        recorded = full.legacy_model_link_identity(link, self.scope)
        link.unlink()
        link.symlink_to(other)
        with patch.object(full, "inspect_image_references", return_value=None):
            with self.assertRaisesRegex(full.Blocked, "legacy_model_link_drift"):
                full.execute({"scope": self.scope, "targets": [
                    {"kind": "legacy-model-link", "id": str(link),
                     "fingerprint": recorded},
                ]})
        self.assertTrue(link.is_symlink())
        self.assertTrue(model.exists())
        self.assertTrue(other.exists())

    def test_discovery_does_not_make_foreign_model_permitted(self) -> None:
        foreign = self.home / "unrelated-model"
        foreign.mkdir()
        with self.assertRaisesRegex(full.Blocked, "model_outside"):
            full.scoped_file(foreign, "model", self.scope)
        owned_candidate = self.model_root / "qwen3.8-flash-next-mazinb"
        owned_candidate.mkdir()
        full.scoped_file(owned_candidate, "model", self.scope)

    def test_project_forensic_is_a_removal_target_and_shared_cache_is_not(self) -> None:
        target = self.home / "Workspace/llm/qwen38-m1-bench-results"
        target.mkdir(parents=True)
        full.scoped_file(target, "forensic", self.scope)
        shared = self.hf / "hub/models--other--unrelated"
        shared.mkdir(parents=True)
        with self.assertRaisesRegex(full.Blocked, "unverified_shared"):
            full.scoped_file(shared, "model-cache", self.scope)

    def test_nested_symlink_is_unlinked_without_following_foreign_target(self) -> None:
        folder = self.model_root / "qwen3.8-flash-next-mazinb"
        folder.mkdir()
        external = self.home / "unrelated"
        external.mkdir()
        (external / "keep.txt").write_text("KEEP")
        (folder / "link").symlink_to(external)
        full.scoped_file(folder, "model", self.scope)
        full.remove_tree(folder, "model", self.scope)
        self.assertFalse(folder.exists())
        self.assertEqual((external / "keep.txt").read_text(), "KEEP")

    def test_transaction_markers_fail_closed(self) -> None:
        (self.state / "settings-transition.phase").write_text("pending")
        with self.assertRaisesRegex(full.Blocked, "active_or_stale"):
            full.ensure_no_live_transitions(self.scope)

    def test_drift_blocks_before_any_mutator(self) -> None:
        saved = {"schema": 1, "mode": "EXACT_PROJECT_RESET",
                 "scope": self.scope, "targets": []}
        saved["sha256"] = full.digest(saved)
        current = dict(saved)
        current["targets"] = [{"kind": "container", "id": "a" * 64}]
        self.assertNotEqual(saved, current)

    def test_service_remove_inherits_shared_lifecycle_lock(self) -> None:
        unit = {"kind": "systemd", "id": "qwen38-flash-next.service"}
        commands = []
        def command(*argv: str) -> str:
            commands.append(argv)
            return ""
        with (patch.object(full, "run", side_effect=command),
              patch.object(full, "inspect_image_references", return_value=None)):
            full.execute({"scope": self.scope, "targets": [unit]})
        self.assertEqual(len(commands), 1)
        call = commands[0]
        self.assertEqual(call[:2], ("sudo", "env"))
        self.assertIn("QWEN38_OPERATION_LOCK_HELD=1", call)
        self.assertIn("QWEN38_OPERATION_LOCK_FILE=" +
                      str(self.state / "operation.lock"), call)
        self.assertEqual(call[-2:], ("remove", "--yes"))

    def test_nonproject_unit_is_rejected_even_when_named_correctly(self) -> None:
        path = self.units / "qwen38-flash-next.service"
        path.write_text("[Unit]\nDescription=foreign\n")
        with self.assertRaisesRegex(full.Blocked, "not_provably"):
            full.check_units(self.scope, [])

    def test_postcheck_only_passes_when_project_scoped_inventory_empty(self) -> None:
        empty = {"issues": [], "resources": [
            {"kind": "hf-cache", "locator": str(self.hf),
             "status": "PRESENT", "ownership": "EXCLUDED_SHARED"},
            {"kind": "state-root", "locator": str(self.state),
             "status": "ABSENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "unit-runtime", "locator": "qwen38-flash-next.service",
             "status": "ABSENT", "ownership": "PROJECT_ASSOCIATED"},
        ]}
        with patch.object(full.inventory, "gather", return_value=empty):
            clean, issues = full.verify_removed({"scope": self.scope})
            self.assertTrue(clean)
            self.assertEqual(issues, [])
        empty["resources"][1]["status"] = "PRESENT"
        with patch.object(full.inventory, "gather", return_value=empty):
            clean, issues = full.verify_removed({"scope": self.scope})
            self.assertFalse(clean)
            self.assertIn("state-root:" + str(self.state) + ":PRESENT", issues)

    def test_project_only_runtime_caches_are_removable_but_shared_flashinfer_not(self) -> None:
        dedicated = self.home / ".cache/vllm-qwen38-v029"
        dedicated.mkdir(parents=True)
        (dedicated / "token").write_text("safe fixture")
        full.scoped_file(dedicated, "project-cache", self.scope)
        full.remove_tree(dedicated, "project-cache", self.scope)
        self.assertFalse(dedicated.exists())
        shared = self.home / ".cache/flashinfer"
        shared.mkdir(parents=True)
        with self.assertRaisesRegex(full.Blocked, "unverified_runtime_cache"):
            full.scoped_file(shared, "project-cache", self.scope)
        self.assertTrue(shared.exists())

    def test_disposable_full_file_teardown_removes_models_evidence_state_data(self) -> None:
        model = self.model_root / "qwen3.8-flash-next-orcarouter"
        model.mkdir()
        (model / "config.json").write_text("{}")
        forensic = self.home / "Workspace/llm/qwen38-m1-bench-results"
        forensic.mkdir(parents=True)
        (forensic / "monitor.log").write_text("fake")
        (self.state / "install.env").write_text("FAKE")
        (self.data / "current").mkdir()
        targets = []
        for kind, path in (
            ("model", model), ("forensic", forensic),
            ("data-root", self.data), ("state-root", self.state),
        ):
            st = path.lstat()
            targets.append({"kind": kind, "id": str(path),
                            "fingerprint": {"dev": st.st_dev, "ino": st.st_ino,
                                            "mode": st.st_mode}})
        with patch.object(full, "inspect_image_references", return_value=None):
            full.execute({"scope": self.scope, "targets": targets})
        for path in (model, forensic, self.data, self.state):
            self.assertFalse(path.exists(), str(path))
        self.assertTrue(self.home.exists())
        self.assertTrue(self.checkout.exists())
        self.assertTrue(self.hf.exists())

    def test_unsafe_foreign_mount_boundary_is_fail_closed(self) -> None:
        foreign = self.home / "unrelated"
        foreign.mkdir()
        with self.assertRaisesRegex(full.Blocked, "forensic_outside"):
            full.scoped_file(foreign, "forensic", self.scope)

    def test_mutation_sequence_is_exactly_project_scoped_and_checked(self) -> None:
        # Every deletion command is inspect-bound, never docker prune.
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('"docker", "rm", "-f", item["id"]', source)
        self.assertIn('"docker", "image", "rm", item["id"]', source)
        self.assertIn('"docker", "volume", "rm", item["id"]', source)
        for dangerous in ('"docker", "system", "prune"', '"docker", "volume", "prune"',
                          '"rm", "-rf"', '"swapoff", "/swap.img"'):
            self.assertNotIn(dangerous, source)
        self.assertIn("typed_approval_or_full_digest_not_matched", source)

    def test_plan_receipt_cannot_be_inside_deletion_scope(self) -> None:
        with self.assertRaisesRegex(full.Blocked, "receipt_inside"):
            full.ensure_receipt_outside_scope(
                self.state / "uninstall-receipt.json",
                {"scope": self.scope},
            )
        full.ensure_receipt_outside_scope(
            self.home / "uninstall-receipt.json",
            {"scope": self.scope},
        )


if __name__ == "__main__":
    unittest.main()
