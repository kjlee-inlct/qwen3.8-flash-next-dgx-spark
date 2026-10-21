"""No DGX access: static catplusplus install/run/benchmark gates and read-only lock path."""
from __future__ import annotations

import importlib.util
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/model/catplusplus_admission_plan.py"
spec = importlib.util.spec_from_file_location("catplusplus_admission", SCRIPT)
assert spec and spec.loader
MODULE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MODULE)


class CatplusplusAdmissionTests(unittest.TestCase):
    def test_memory_envelope_exceeds_gb10_even_after_publisher_fp8_ple_subtraction(self):
        m = MODULE.data()
        self.assertEqual(m["revision"], "3251fd8afbd08f76368a9bfa71132d9aef364813")
        self.assertGreater(m["root_weight_gib_rounded"],
                           m["nominal_unified_memory_gib"])
        self.assertGreater(m["optimistic_stored_weight_gib_after_ple_subtraction"],
                           m["nominal_unified_memory_gib"])
        self.assertEqual(m["live_admission"], False)
        self.assertIn("BLOCKED", m["engine_gate"])
        self.assertIn("BLOCKED", m["gpu_gate"])
        self.assertIn("BLOCKED", m["benchmark_gate"])
        self.assertIn("BLOCKED_WHILE_MAZINB", m["download_gate"])

    def test_plan_is_pure_and_never_creates_host_state(self):
        with tempfile.TemporaryDirectory() as t:
            env = {**os.environ, "HOME": t, "XDG_STATE_HOME": str(Path(t) / "xdg")}
            p = subprocess.run([sys.executable, "-B", str(SCRIPT), "plan"],
                               cwd=ROOT, env=env, text=True,
                               capture_output=True, check=False, timeout=10)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("CATPLUSPLUS_PREP_SOURCE_GATE=PINNED_RAW_GET_AUDIT_REQUIRED",
                          p.stdout)
            self.assertIn("CATPLUSPLUS_PREP_BENCHMARK_SHAPE=PP512_2048_TG128", p.stdout)
            self.assertIn("CATPLUSPLUS_PREP_WEIGHT_DOWNLOAD=NOT_PERFORMED", p.stdout)
            self.assertIn("CATPLUSPLUS_PREP_HOST_MUTATION=NONE", p.stdout)
            self.assertFalse((Path(t) / "xdg").exists())

    def test_disk_probe_rejects_missing_lock_without_creating_it(self):
        with tempfile.TemporaryDirectory() as t:
            env = {**os.environ, "HOME": t, "XDG_STATE_HOME": str(Path(t) / "xdg")}
            p = subprocess.run([sys.executable, "-B", str(SCRIPT), "disk-check"],
                               cwd=ROOT, env=env, text=True,
                               capture_output=True, check=False, timeout=10)
            self.assertEqual(p.returncode, 2, p.stdout)
            self.assertIn("HOST_LIFECYCLE_LOCK_MISSING_OR_UNSAFE", p.stderr)
            self.assertIn("CATPLUSPLUS_PREP_DOWNLOAD_DOCKER_GPU_SERVICE=NOT_PERFORMED",
                          p.stdout)
            self.assertFalse((Path(t) / "xdg").exists())

    def test_active_mazinb_download_lifecycle_lock_blocks_catplusplus_disk_probe(self):
        with tempfile.TemporaryDirectory() as t:
            state = Path(t) / "state" / "qwen38-spark"
            state.mkdir(parents=True)
            lock = state / "operation.lock"
            lock.write_bytes(b"")
            env = {**os.environ, "XDG_STATE_HOME": str(Path(t) / "state")}
            with lock.open("rb") as stream:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                p = subprocess.run(
                    [sys.executable, "-B", str(SCRIPT), "disk-check"],
                    cwd=ROOT, env=env, text=True, capture_output=True,
                    check=False, timeout=10)
                self.assertEqual(p.returncode, 2, p.stdout)
                self.assertIn("HOST_LIFECYCLE_BUSY_MAZINB_DOWNLOAD_MAY_BE_ACTIVE",
                              p.stderr)
            self.assertEqual(list(state.iterdir()), [lock])

    def test_wizard_stage_9_plan_and_stage_10_disk_refusal(self):
        with tempfile.TemporaryDirectory() as t:
            env = {**os.environ, "HOME": t,
                   "XDG_STATE_HOME": str(Path(t) / "xdg")}
            p = subprocess.run(
                ["bash", str(ROOT / "wizard.sh"), "--lang", "en"],
                cwd=ROOT, env=env, input="5\n23\n9\n10\n0\n0\n0\n",
                capture_output=True, text=True, timeout=20, check=False)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("CATPLUSPLUS_PREP_STATUS=PREPARATION_SOURCE_ONLY", p.stdout)
            self.assertIn("HOST_LIFECYCLE_LOCK_MISSING_OR_UNSAFE", p.stderr)
            self.assertFalse((Path(t) / "xdg").exists())

    def test_source_and_wizard_do_not_authorize_download_or_live_run(self):
        source = SCRIPT.read_text(encoding="utf-8")
        wizard = (ROOT / "scripts/wizard/benchmark-menu.sh").read_text()
        self.assertIn("9) python3 -B", wizard)
        self.assertIn("catplusplus_admission_plan.py", wizard)
        self.assertIn("10) python3 -B", wizard)
        self.assertIn("LOCK_SH | fcntl.LOCK_NB", source)
        for forbidden in ("docker run", "docker start", "docker rm",
                          "hf download", "snapshot_download(",
                          "systemctl start", "os.system(", "rm -rf"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
