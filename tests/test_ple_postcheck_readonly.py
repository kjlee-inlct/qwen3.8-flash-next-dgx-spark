"""Offline-only tests for exact-ID protected metadata current-state postcheck."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[1] / "scripts/model"
sys.path.insert(0, str(SRC_DIR))
spec = importlib.util.spec_from_file_location(
    "isolated_ple_current_postcheck", SRC_DIR / "inspect_ple_postcheck_readonly.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def objects():
    image = {
        "Id": mod.probe.EXPECTED_IMAGE_ID,
        "Size": mod.probe.EXPECTED_IMAGE_SIZE,
    }
    mounts = [
        {"Destination": "/model", "Type": "bind", "RW": False, "Source": "/private/a"},
        {"Destination": "/model/config.json", "Type": "bind", "RW": False,
         "Source": "/private/b"},
    ]
    def make(cid, name):
        return {
            "Id": cid,
            "Image": mod.probe.EXPECTED_IMAGE_ID,
            "Name": "/" + name,
            "Config": {"Image": mod.audit.IMAGE_TAG, "Env": ["TOKEN=private"]},
            "Mounts": copy.deepcopy(mounts),
            "State": {"Status": "exited", "Error": "private error"},
            "HostConfig": {"ReadonlyRootfs": False, "Binds": ["/private/a:/model:ro"]},
        }
    return image, make(mod.probe.EXPECTED_MANAGED_ID, mod.audit.MANAGED_CONTAINER), make(
        mod.probe.EXPECTED_LEGACY_ID, mod.audit.LEGACY_CONTAINER
    )


class FakeDocker:
    def __init__(self):
        self.image, self.managed, self.legacy = objects()
        self.calls = []
        self.temp_present = False
        self.referred_by_name_diff = False
        self.changed_managed = False
        self.reorder_legacy_mounts = False
        self.change_legacy_mount_source = False

    def __call__(self, args, limit=mod.probe.MAX_DOCKER_META_BYTES):
        self.calls.append(tuple(args))
        if args[:2] != ["container", "inspect"] and args[:2] != ["image", "inspect"]:
            raise AssertionError("Read-only inspect only")
        if args in (
            ["container", "inspect", mod.TEMP_ID],
            ["container", "inspect", mod.TEMP_NAME],
        ):
            if self.temp_present:
                return json.dumps([{
                    "Id": mod.TEMP_ID, "Name": "/" + mod.TEMP_NAME
                }]).encode()
            raise mod.probe.CommandFailed("CONTAINER_NOT_FOUND")
        if args == ["image", "inspect", mod.audit.IMAGE_TAG]:
            return json.dumps([self.image]).encode()
        if args[-1] in (mod.audit.MANAGED_CONTAINER, mod.probe.EXPECTED_MANAGED_ID):
            item = copy.deepcopy(self.managed)
            if self.changed_managed:
                item["State"]["Status"] = "running"
            if self.referred_by_name_diff and args[-1] == mod.audit.MANAGED_CONTAINER:
                item["HostConfig"]["LogConfig"] = {"Type": "json-file"}
            return json.dumps([item]).encode()
        if args[-1] in (mod.audit.LEGACY_CONTAINER, mod.probe.EXPECTED_LEGACY_ID):
            item = copy.deepcopy(self.legacy)
            if args[-1] == mod.audit.LEGACY_CONTAINER:
                if self.reorder_legacy_mounts:
                    item["Mounts"].reverse()
                if self.change_legacy_mount_source:
                    item["Mounts"][0]["Source"] = "/private/changed-SECRET"
            return json.dumps([item]).encode()
        raise AssertionError("Unknown request")


class ReadonlyPostcheckTests(unittest.TestCase):
    def test_current_pass_even_when_historic_mismatch_cannot_be_recovered(self):
        fake = FakeDocker()
        with patch.object(mod.probe, "docker", side_effect=fake):
            result, ok = mod.inspect_now()
        self.assertTrue(ok)
        self.assertEqual(result["temp_absence"], "ABSENT_ID_AND_NAME")
        self.assertEqual(result["image"], "MATCH_PINNED_ID_AND_SIZE")
        self.assertEqual(result["managed_name_vs_id_fields"], "MATCH")
        self.assertEqual(result["legacy_name_vs_id_fields"], "MATCH")
        self.assertEqual(result["current_static_postcheck"], "PASS_CURRENT_ONLY")
        self.assertEqual(
            result["historical_failure_cause"],
            "UNRECOVERABLE_WITHOUT_PRE_POST_FIELD_SNAPSHOTS",
        )
        self.assertEqual(len(fake.calls), 7)
        self.assertTrue(all(x[1] == "inspect" for x in fake.calls))
        self.assertNotIn("/private", repr(result))
        self.assertNotIn("TOKEN", repr(result))

    def test_existing_temp_blocks_pass(self):
        fake = FakeDocker()
        fake.temp_present = True
        with patch.object(mod.probe, "docker", side_effect=fake):
            result, ok = mod.inspect_now()
        self.assertFalse(ok)
        self.assertEqual(result["temp_absence"], "PRESENT_STOP")
        self.assertEqual(result["current_static_postcheck"], "STOP_REVIEW_REQUIRED")

    def test_name_vs_id_different_hostconfig_is_only_named_category(self):
        fake = FakeDocker()
        fake.referred_by_name_diff = True
        with patch.object(mod.probe, "docker", side_effect=fake):
            result, ok = mod.inspect_now()
        self.assertFalse(ok)
        self.assertEqual(result["managed_name_vs_id_fields"], "DIFFERENT_HostConfig")
        self.assertNotIn("/private", repr(result))
        self.assertNotIn("json-file", repr(result))

    def test_order_only_legacy_mounts_are_accepted_current_only(self):
        fake = FakeDocker()
        fake.reorder_legacy_mounts = True
        with patch.object(mod.probe, "docker", side_effect=fake):
            result, ok = mod.inspect_now()
        self.assertTrue(ok)
        self.assertEqual(result["legacy_name_vs_id_mounts"], "ORDER_ONLY")
        self.assertEqual(result["legacy_name_vs_id_fields"], "MATCH")
        self.assertEqual(result["current_static_postcheck"], "PASS_CURRENT_ONLY")
        self.assertEqual(
            result["historical_failure_cause"],
            "UNRECOVERABLE_WITHOUT_PRE_POST_FIELD_SNAPSHOTS",
        )
        self.assertNotIn("/private", repr(result))

    def test_legacy_mount_source_value_drift_is_blocked_and_private(self):
        fake = FakeDocker()
        fake.change_legacy_mount_source = True
        with patch.object(mod.probe, "docker", side_effect=fake):
            result, ok = mod.inspect_now()
        self.assertFalse(ok)
        self.assertEqual(
            result["legacy_name_vs_id_mounts"], "OTHER_MOUNT_METADATA_CHANGED"
        )
        self.assertEqual(result["legacy_name_vs_id_fields"], "DIFFERENT_Mounts")
        self.assertEqual(result["current_static_postcheck"], "STOP_REVIEW_REQUIRED")
        self.assertNotIn("SECRET", repr(result))
        self.assertNotIn("/private", repr(result))

    def test_mount_membership_type_rw_and_duplicate_change_fail_closed(self):
        _, a, _ = objects()
        base = a["Mounts"]
        self.assertEqual(mod.compare_mounts(base, list(reversed(base))), "ORDER_ONLY")
        self.assertEqual(mod.compare_mounts(base, copy.deepcopy(base)), "IDENTICAL_ORDER")

        changed_dest = copy.deepcopy(base)
        changed_dest[1]["Destination"] = "/unexpected/mount"
        self.assertEqual(
            mod.compare_mounts(base, changed_dest), "DESTINATION_MEMBERSHIP_CHANGED"
        )
        changed_type = copy.deepcopy(base)
        changed_type[0]["RW"] = True
        self.assertEqual(mod.compare_mounts(base, changed_type), "TYPE_OR_RW_CHANGED")
        changed_source = copy.deepcopy(base)
        changed_source[0]["Source"] = "/secret/path-shall-not-leak"
        self.assertEqual(
            mod.compare_mounts(base, changed_source),
            "OTHER_MOUNT_METADATA_CHANGED",
        )
        duplicate = copy.deepcopy(base)
        duplicate[1]["Destination"] = duplicate[0]["Destination"]
        self.assertEqual(mod.compare_mounts(base, duplicate), "INVALID_MOUNT_METADATA")
        self.assertEqual(mod.compare_mounts(base, "garbled"), "INVALID_MOUNT_METADATA")

    def test_mount_order_change_cannot_hide_hostconfig_drift(self):
        _, a, _ = objects()
        b = copy.deepcopy(a)
        b["Mounts"].reverse()
        b["HostConfig"]["ReadonlyRootfs"] = True
        self.assertEqual(mod.compare_mounts(a["Mounts"], b["Mounts"]), "ORDER_ONLY")
        self.assertEqual(mod.compare_fields(a, b), "DIFFERENT_HostConfig")

    def test_changed_protected_state_fails_closed(self):
        fake = FakeDocker()
        fake.changed_managed = True
        with patch.object(mod.probe, "docker", side_effect=fake):
            result, ok = mod.inspect_now()
        self.assertFalse(ok)
        self.assertEqual(result["managed_review"], "INCONCLUSIVE_OR_CHANGED")
        self.assertNotIn("managed_identity", result)

    def test_changed_image_size_fails_closed(self):
        fake = FakeDocker()
        fake.image["Size"] += 1
        with patch.object(mod.probe, "docker", side_effect=fake):
            result, ok = mod.inspect_now()
        self.assertFalse(ok)
        self.assertEqual(result["image"], "INCONCLUSIVE_OR_CHANGED")

    def test_unexpected_copy_or_mutation_is_not_issued(self):
        fake = FakeDocker()
        with patch.object(mod.probe, "docker", side_effect=fake):
            _, ok = mod.inspect_now()
        self.assertTrue(ok)
        self.assertFalse(any(
            x[1] in ("create", "cp", "run", "start", "rm", "exec")
            for x in fake.calls
        ))


if __name__ == "__main__":
    unittest.main()
