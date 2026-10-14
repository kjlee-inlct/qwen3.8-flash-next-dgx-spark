"""Host-free safety and archive-order tests for exact mazinb Docker retirement."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/model/retire-mazinb-containers.py"
SPEC = importlib.util.spec_from_file_location("retire_mazinb_containers", SOURCE)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MzinbDockerRetirementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home / "models"
        self.state = self.home / "state"
        self.root.mkdir()
        self.state.mkdir()
        for stage in ("qwen3.8-hybrid-quant-layout", "qwen3.8-h4-orca-all",
                      "qwen3.8-h5-neutral-input-scale", "qwen3.8-h6-modelopt-w4a16"):
            (self.root / stage).mkdir()
        folder = self.home / "Workspace/llm/qwen38-m1-bench-results" / MODULE.TRIAL
        folder.mkdir(parents=True)
        repo = self.home / "fake-repository"
        archived = repo / "docs/model-reports/evidence/mazinb" / MODULE.TRIAL
        archived.mkdir(parents=True)
        report = repo / "docs/model-reports/mazinb.md"
        report.write_text("**BENCHMARK_STATUS: MEASURED**\n")
        sums = {}
        for name in MODULE.CHECKSUMS:
            payload = ("test-" + name).encode("utf-8")
            sums[name] = hashlib.sha256(payload).hexdigest()
            (folder / name).write_bytes(payload)
            (archived / name).write_bytes(payload)
        (archived / "SHA256SUMS").write_text(
            "".join(f"{sha}  {name}\n" for name, sha in sums.items()))
        (self.state / "mazinb-m1").mkdir()
        (self.state / "mazinb-m1/active.json").write_text(json.dumps({
            "id": MODULE.EXPECTED["qwen38-mazinb-m1-20261014013811-16ced779"],
            "phase": "stopped"}))
        self.repo_patch = mock.patch.object(MODULE, "ROOT", repo)
        self.sha_patch = mock.patch.object(MODULE, "CHECKSUMS", sums)
        self.repo_patch.start()
        self.sha_patch.start()
        self.addCleanup(self.repo_patch.stop)
        self.addCleanup(self.sha_patch.stop)

    def test_model_removed_and_two_archives_must_match(self):
        MODULE.evidence(self.home, self.root, self.state)
        original = self.home / "Workspace/llm/qwen38-m1-bench-results" / MODULE.TRIAL
        (original / "mazinb.json").write_text("tampered")
        with self.assertRaisesRegex(MODULE.Blocked, "evidence digest mismatch"):
            MODULE.evidence(self.home, self.root, self.state)

    def test_present_source_checkpoint_blocks_cleanup(self):
        (self.root / "qwen3.8-flash-next-mazinb").mkdir()
        with self.assertRaisesRegex(MODULE.Blocked, "must be previously removed"):
            MODULE.evidence(self.home, self.root, self.state)

    def objects(self):
        objs = {}
        for name, cid in MODULE.EXPECTED.items():
            objs[cid] = {
                "Id": cid, "Name": "/" + name,
                "State": {"Running": False, "Status": "exited"},
                "Config": {"Image": MODULE.EXPECTED_IMAGE},
                "HostConfig": {"RestartPolicy": {"Name": "no"}, "AutoRemove": False},
                "Mounts": [{"Type": "bind", "Source":
                            str(self.root / "qwen3.8-flash-next-mazinb"),
                            "Destination": "/model"}],
            }
        objs[MODULE.PROTECTED_ID] = {
            "Id": MODULE.PROTECTED_ID, "Name": "/" + MODULE.PROTECTED_NAME,
            "State": {"Running": False}, "Mounts": [],
        }
        return objs

    def simulated_docker(self, objects):
        def run(*args, **kwargs):
            if args[:3] == ("ps", "-aq", "--no-trunc"):
                return "\n".join(sorted(objects)) + "\n"
            if args[0] == "inspect":
                return json.dumps([objects[x] for x in args[1:]])
            if args[:2] == ("image", "inspect"):
                return "[]"
            raise AssertionError(f"Unexpected Docker request: {args}")
        return run

    def test_exact_five_qualify_and_never_change_docker_in_plan(self):
        objects = self.objects()
        with mock.patch.object(MODULE, "docker", side_effect=self.simulated_docker(objects)) as d:
            items, ids = MODULE.inventory(self.root / "qwen3.8-flash-next-mazinb")
        self.assertEqual(len(ids), 6)
        self.assertEqual(len(items), 6)
        self.assertEqual(sum(1 for x in d.call_args_list if x.args[0] == "rm"), 0)

    def test_changed_id_running_or_wrong_mount_blocks(self):
        for mode in ("id", "running", "mount", "image", "restart"):
            with self.subTest(mode=mode):
                objects = self.objects()
                name, cid = next(iter(MODULE.EXPECTED.items()))
                if mode == "id":
                    objects.pop(cid)
                elif mode == "running":
                    objects[cid]["State"]["Running"] = True
                elif mode == "mount":
                    objects[cid]["Mounts"][0]["Source"] = "/different"
                elif mode == "image":
                    objects[cid]["Config"]["Image"] = "unrecognized"
                elif mode == "restart":
                    objects[cid]["HostConfig"]["RestartPolicy"]["Name"] = "always"
                with mock.patch.object(MODULE, "docker",
                                       side_effect=self.simulated_docker(objects)):
                    with self.assertRaises(MODULE.Blocked):
                        MODULE.inventory(self.root / "qwen3.8-flash-next-mazinb")

    def test_missing_protected_predecessor_blocks(self):
        objects = self.objects()
        objects.pop(MODULE.PROTECTED_ID)
        with mock.patch.object(MODULE, "docker",
                               side_effect=self.simulated_docker(objects)):
            with self.assertRaisesRegex(MODULE.Blocked, "protected predecessor"):
                MODULE.inventory(self.root / "qwen3.8-flash-next-mazinb")

    def test_apply_requires_manager_lock(self):
        with mock.patch.dict(os.environ, {
            "QWEN38_OPERATION_LOCK_HELD": "0",
            "QWEN38_MAZINB_BENCH_LOCK_HELD": "0",
        }):
            with self.assertRaisesRegex(MODULE.Blocked, "locked lifecycle manager"):
                MODULE.apply(self.home, self.root, self.state)

    def test_archive_is_completed_before_any_exact_docker_removal(self):
        objects = self.objects()
        before_ids = set(objects)
        calls = []
        retired = set()

        def docker(*args, **kwargs):
            if args[:3] == ("ps", "-aq", "--no-trunc"):
                return "\n".join(sorted(before_ids-retired))
            if args[0] == "rm":
                calls.append("remove")
                cid = args[1]
                self.assertIn(cid, MODULE.EXPECTED.values())
                retired.add(cid)
                return cid
            if args[0] == "inspect":
                return json.dumps([objects[x] for x in args[1:]])
            if args[:2] == ("image", "inspect"):
                return "[]"
            raise AssertionError(args)

        def archive(*args):
            calls.append("archive")
            return self.home / "saved"

        with mock.patch.dict(os.environ, {
            "QWEN38_OPERATION_LOCK_HELD": "1",
            "QWEN38_MAZINB_BENCH_LOCK_HELD": "1",
        }), mock.patch.object(MODULE, "docker", side_effect=docker), \
             mock.patch.object(MODULE, "inventory",
                               side_effect=[(objects, before_ids), (objects, before_ids)]), \
             mock.patch.object(MODULE, "save_all_logs_and_metadata", side_effect=archive):
            MODULE.apply(self.home, self.root, self.state)
        self.assertEqual(calls, ["archive"] + ["remove"]*5)
        self.assertEqual(retired, set(MODULE.EXPECTED.values()))
        self.assertTrue((self.state / "mazinb-m1/active.json").exists())

    def test_archive_parent_rejects_symlink(self):
        outside = self.home / "other"
        outside.mkdir()
        (self.state / "retirement-archives").symlink_to(outside)
        with self.assertRaisesRegex(MODULE.Blocked, "unsafe retirement archive root"):
            MODULE.safe_archive_parent(self.state)

    def test_script_has_no_force_or_volume_delete(self):
        content = SOURCE.read_text()
        self.assertIn('docker("rm", cid)', content)
        self.assertNotIn('docker("rm", "-f"', content)
        self.assertNotIn('docker("volume", "rm"', content)
        self.assertIn("MAX_LOG_BYTES =", content)


if __name__ == "__main__":
    unittest.main()
