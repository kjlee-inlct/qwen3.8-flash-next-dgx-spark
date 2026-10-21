"""M1 journal provenance survives exact archived Docker object retirement."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/runtime/mazinb-m1.py"
SPEC = importlib.util.spec_from_file_location("mazinb_m1_retirement_test", SOURCE)
assert SPEC and SPEC.loader
M1 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M1
SPEC.loader.exec_module(M1)

ID = "7af3966f3d0cae79f8277eaf9ad003fb04c1e15ea01f86574c2d8eeac396e7a1"
NAME = "qwen38-mazinb-m1-20261014013811-16ced779"


class RetiredM1Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "state"
        self.m1 = self.state / "mazinb-m1"
        self.m1.mkdir(parents=True)
        self.original = {
            "phase": "stopped", "name": NAME,
            "id": ID, "exit_code": 0,
        }
        (self.m1 / "active.json").write_text(json.dumps(self.original))
        self.archive = self.state / "retirement-archives/mazinb-docker-20261014-fixture"
        self.archive.mkdir(parents=True)
        lines = []
        for i in range(5):
            for ext in ("log", "json"):
                name = f"{i:016x}.{ext}"
                (self.archive / name).write_text(f"fixture-{i}-{ext}")
                sha = hashlib.sha256((self.archive / name).read_bytes()).hexdigest()
                lines.append(f"{sha}  {name}\n")
        (self.archive / "SHA256SUMS").write_text("".join(lines))
        self.marker = {
            "schema_version": 1, "state": "archived_docker_removed",
            "id": ID, "name": NAME, "archive_path": str(self.archive),
            "archive_sha256_manifest":
                hashlib.sha256((self.archive / "SHA256SUMS").read_bytes()).hexdigest(),
        }
        (self.m1 / "retired-docker.json").write_text(json.dumps(self.marker))

    def test_archived_identity_requires_absent_docker_and_valid_archive(self):
        with mock.patch.object(M1, "inspect", return_value=None):
            result = M1.retired_docker_marker(self.original, self.m1)
        self.assertEqual(result["id"], ID)
        with mock.patch.object(M1, "inspect", return_value={"Id": ID}):
            with self.assertRaisesRegex(M1.M1Error, "still resolves"):
                M1.retired_docker_marker(self.original, self.m1)

    def test_tombstone_archive_mutation_or_id_mismatch_blocks(self):
        wrong = dict(self.original, id="a"*64)
        with mock.patch.object(M1, "inspect", return_value=None):
            with self.assertRaisesRegex(M1.M1Error, "identity"):
                M1.retired_docker_marker(wrong, self.m1)
            (self.archive / "SHA256SUMS").write_text("tampered")
            with self.assertRaisesRegex(M1.M1Error, "hash manifest changed"):
                M1.retired_docker_marker(self.original, self.m1)

    def test_status_distinguishes_removed_archived_from_unexpected_disappearance(self):
        output = io.StringIO()
        with mock.patch.object(M1, "state_paths",
                               return_value=(self.state, self.state, self.m1)), \
             mock.patch.object(M1, "inspect", return_value=None), \
             contextlib.redirect_stdout(output):
            M1.status()
        self.assertIn("M1_DOCKER_REMOVED=YES_ARCHIVED", output.getvalue())
        self.assertIn(f"M1_CONTAINER_ID={ID}", output.getvalue())
        self.assertIn("M1_EXIT_CODE=0", output.getvalue())
        (self.m1 / "retired-docker.json").unlink()
        with mock.patch.object(M1, "state_paths",
                               return_value=(self.state, self.state, self.m1)), \
             mock.patch.object(M1, "inspect", return_value=None):
            with self.assertRaises(M1.M1Error):
                M1.status()


if __name__ == "__main__":
    unittest.main()
