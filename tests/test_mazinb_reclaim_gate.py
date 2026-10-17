"""Host-free adversarial tests for mazinb checkpoint-only reclaim admission."""
from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/model/mazinb-reclaim-gate.py"
spec = importlib.util.spec_from_file_location("mazinb_reclaim_gate", SCRIPT)
assert spec and spec.loader
GATE = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = GATE
spec.loader.exec_module(GATE)


class MzinbReclaimGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home / "models"
        self.root.mkdir()
        self.target = self.root / GATE.MODEL
        self.target.mkdir()
        self.state = self.home / "state"
        self.state.mkdir()
        (self.state / "install.env").write_text("strict-parser-is-manager-owned\n")
        self.write_manifest()

    def write_manifest(self, **updates) -> None:
        data = {"status": "complete", "repository": GATE.EXPECTED_REPO,
                "revision": "f2c21eb987654321"}
        data.update(updates)
        (self.target / ".qwen38-model-manifest.json").write_text(json.dumps(data))

    def test_manifest_identity_is_strict_and_no_external_steps_run_on_failure(self) -> None:
        for update in ({"repository": "other/model"}, {"status": "downloading"},
                       {"revision": "bad-revision"}):
            with self.subTest(update=update):
                self.write_manifest(**update)
                with mock.patch.object(GATE, "archived_evidence") as archive, \
                     mock.patch.object(GATE, "docker_inventory") as docker:
                    with self.assertRaises(GATE.Blocked):
                        GATE.inspect(self.home, self.root, self.state)
                    archive.assert_not_called()
                    docker.assert_not_called()

    def test_valid_synthetic_admission_is_read_only(self) -> None:
        with mock.patch.object(GATE, "archived_evidence") as archive, \
             mock.patch.object(GATE, "hybrid_provenance") as hybrid, \
             mock.patch.object(GATE, "docker_inventory") as docker:
            out = io.StringIO()
            with redirect_stdout(out):
                GATE.inspect(self.home, self.root, self.state)
        self.assertIn("MAZINB_RECLAIM_GATE=PASS_SOURCE_ONLY_READ_ONLY", out.getvalue())
        archive.assert_called_once()
        hybrid.assert_called_once()
        docker.assert_called_once()
        self.assertTrue(self.target.is_dir())

    def test_archive_payloads_are_verified_against_two_copies(self) -> None:
        repo_root = self.home / "checkout"
        archive = repo_root / "docs/model-reports/evidence/mazinb" / GATE.TRIAL
        original = self.home / "Workspace/llm/qwen38-m1-bench-results" / GATE.TRIAL
        for folder in (archive, original):
            folder.mkdir(parents=True)
        report = repo_root / "docs/model-reports/mazinb.md"
        report.write_text("**BENCHMARK_STATUS: MEASURED**\n")
        expected = {}
        for name in GATE.EXPECTED:
            data = ("fixture-" + name).encode("utf-8")
            expected[name] = hashlib.sha256(data).hexdigest()
            (archive / name).write_bytes(data)
            (original / name).write_bytes(data)
        (archive / "SHA256SUMS").write_text(
            "".join(f"{expected[name]}  {name}\n" for name in expected))
        with mock.patch.object(GATE, "ROOT", repo_root), \
             mock.patch.object(GATE, "EXPECTED", expected):
            GATE.archived_evidence(self.home, self.target)
            (original / "mazinb.json").write_text("TAMPERED")
            with self.assertRaisesRegex(GATE.Blocked, "original DGX archive corrupt"):
                GATE.archived_evidence(self.home, self.target)

    def test_hybrid_partial_chain_blocks_source_retirement(self) -> None:
        (self.root / "qwen3.8-hybrid-quant-layout").mkdir()
        (self.root / "qwen3.8-h4-orca-all").mkdir()
        good = subprocess.CompletedProcess([], 0, "PASS", "")
        with mock.patch.object(GATE.subprocess, "run", return_value=good):
            with self.assertRaisesRegex(GATE.Blocked, "incomplete H4/H5/H6"):
                GATE.hybrid_provenance(self.root, self.target)

    def test_hybrid_symlink_into_source_blocks(self) -> None:
        h3 = self.root / "qwen3.8-hybrid-quant-layout"
        h3.mkdir()
        (h3 / "weights").symlink_to(self.target)
        with self.assertRaisesRegex(GATE.Blocked, "Hybrid stage references mazinb"):
            GATE.hybrid_provenance(self.root, self.target)

    def docker_objects(self, running=False, restart="no", old_present=True):
        old = GATE.PROTECTED_ID
        candidate = "a" * 64
        objects = [
            {"Id": candidate, "Name": "/qwen38-mazinb-m1-fixture",
             "State": {"Running": running},
             "Mounts": [{"Source": str(self.target)}],
             "HostConfig": {"RestartPolicy": {"Name": restart}}},
        ]
        if old_present:
            objects.append({"Id": old, "Name": "/" + GATE.PROTECTED_NAME,
                            "State": {"Running": False}, "Mounts": [],
                            "HostConfig": {"RestartPolicy": {"Name": "no"}}})
        journal = self.state / "mazinb-m1"
        journal.mkdir(exist_ok=True)
        (journal / "active.json").write_text(json.dumps({
            "phase": "stopped", "id": candidate}))
        return objects

    def simulate_inventory(self, objects):
        ids = "\n".join(x["Id"] for x in objects) + "\n"
        return [
            subprocess.CompletedProcess([], 0, ids, ""),
            subprocess.CompletedProcess([], 0, json.dumps(objects), ""),
        ]

    def test_running_mazinb_or_non_no_restart_policy_is_blocked(self) -> None:
        for kwargs in ({"running": True}, {"restart": "always"}):
            with self.subTest(kwargs=kwargs):
                objects = self.docker_objects(**kwargs)
                with mock.patch.object(GATE.subprocess, "run",
                                       side_effect=self.simulate_inventory(objects)):
                    with self.assertRaises(GATE.Blocked):
                        GATE.docker_inventory(self.target, self.root, self.state)

    def test_missing_protected_predecessor_is_blocked(self) -> None:
        objects = self.docker_objects(old_present=False)
        with mock.patch.object(GATE.subprocess, "run",
                               side_effect=self.simulate_inventory(objects)):
            with self.assertRaisesRegex(GATE.Blocked, "protected OrcaRouter"):
                GATE.docker_inventory(self.target, self.root, self.state)

    def test_stopped_trials_are_preserved_but_lose_restartability(self) -> None:
        objects = self.docker_objects()
        with mock.patch.object(GATE.subprocess, "run",
                               side_effect=self.simulate_inventory(objects)):
            out = io.StringIO()
            with redirect_stdout(out):
                GATE.docker_inventory(self.target, self.root, self.state)
        self.assertIn("MAZINB_RECLAIM_STOPPED_MOUNTS=1", out.getvalue())
        self.assertIn("MAZINB_RECLAIM_ARCHIVE_ONLY_CONTAINER", out.getvalue())
        self.assertTrue(self.target.exists())

    def test_manager_reuses_single_removal_engine_under_locks(self) -> None:
        manager = (ROOT / "scripts/manage-models.sh").read_text(encoding="utf-8")
        self.assertIn("reclaim_mazinb_checkpoint()", manager)
        self.assertIn("acquire_operation_lock", manager)
        self.assertIn('flock -n "${MAZINB_BENCH_FD}"', manager)
        self.assertIn('python3 -B "${SCRIPT_ROOT}/scripts/model/mazinb-reclaim-gate.py"', manager)
        self.assertIn('remove_model\n', manager)
        self.assertIn("MAZINB_RECLAIM_DOCKER_OBJECTS=UNCHANGED", manager)
        self.assertNotIn("docker rm", manager[manager.index("reclaim_mazinb_checkpoint()"):manager.index("discover() {")])


if __name__ == "__main__":
    unittest.main()
