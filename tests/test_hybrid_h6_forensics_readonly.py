"""Pure safety tests for H6 first-failure readonly forensic collector."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/wizard/hybrid-h6-forensics-readonly.py"
spec = importlib.util.spec_from_file_location("hybrid_h6_forensics_readonly", SCRIPT)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class H6ForensicTests(unittest.TestCase):
    def setUp(self):
        self.name = "qwen38-hybrid-h6-m1-20261014141803-69ef3492"
        self.cid = "e526189f1093e95d81568d82eb10b8beaeb6227adca49029f241634769e6cbc7"

    def test_exact_stop_marker(self):
        data = ("RUNTIME_STOP_SCHEMA_VERSION=1\n"
                "STOP_REASON=memory-protection\n"
                f"STOP_CONTAINER_NAME={self.name}\n"
                f"STOP_CONTAINER_ID={self.cid}\n"
                "UPDATED_AT=2026-10-14T14:28:45Z\n")
        d = m.marker_fields(data, name=self.name, container_id=self.cid)
        self.assertEqual(d["STOP_REASON"], "memory-protection")
        with self.assertRaises(m.EvidenceError):
            m.marker_fields(data.replace(self.cid, "a" * 64),
                            name=self.name, container_id=self.cid)

    def test_stop_marker_rejects_shell_expansion_and_duplicates(self):
        data = ("RUNTIME_STOP_SCHEMA_VERSION=1\n"
                "STOP_REASON=$(touch /tmp/never)\n"
                f"STOP_CONTAINER_NAME={self.name}\n"
                f"STOP_CONTAINER_ID={self.cid}\n"
                "UPDATED_AT=2026-10-14T14:28:45Z\n")
        with self.assertRaises(m.EvidenceError):
            m.marker_fields(data, name=self.name, container_id=self.cid)
        with self.assertRaises(m.EvidenceError):
            m.marker_fields(data.replace("STOP_REASON=$(touch /tmp/never)",
                                         "STOP_REASON=memory-protection\nSTOP_REASON=memory-protection"),
                            name=self.name, container_id=self.cid)

    def test_invalid_params_fail_before_host_probe(self):
        p = subprocess.run(["python3", "-B", str(SCRIPT), "--name", self.name,
                            "--expected-id", "nothex", "--expected-source-sha", "a" * 40],
                           capture_output=True, text=True, check=False, timeout=15)
        self.assertEqual(p.returncode, 2)
        self.assertIn("H6_FORENSIC_HOST_MUTATION=NONE", p.stderr)

    def test_monitor_log_filter_does_not_interpret_tensor_progress(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "monitor.log"
            path.write_text("Loading safetensors checkpoint shards: 99% Completed\n"
                            "2026-10-14 WARNING memory margin low protect=5/5: "
                            "noncma_available=23000MiB noncmafree=800MiB swapgrowth=500MiB\n"
                            "2026-10-14 PROTECT stopping qwen38-hybrid-h6-m1-xxx\n")
            lines, protect, count = m.monitor_events(path)
            self.assertTrue(protect)
            self.assertEqual(count, 1)
            self.assertEqual(len(lines), 2)

    def test_docker_traceback_cannot_displace_causal_memory_warnings(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "monitor.log"
            warnings = [
                "2026-10-14 WARNING memory margin low protect=%d/5: noncmafree=800MiB swapgrowth=500MiB" % i
                for i in range(1, 6)
            ]
            path.write_text(
                "\n".join(warnings + [
                    "2026-10-14 PROTECT stopping qwen38-hybrid-h6-m1-trial"
                ] + ["ERROR: vLLM shutdown traceback"] * 100) + "\n"
            )
            events, protected, count = m.monitor_events(path)
            self.assertTrue(protected)
            self.assertEqual(count, 5)
            self.assertTrue(any("protect=5/5" in line for line in events))
            self.assertTrue(any("PROTECT stopping" in line for line in events))

    def test_kernel_check_skips_bad_timestamp(self):
        with patch.object(m.subprocess, "run") as run:
            m.kernel_summary("invalid")
            run.assert_not_called()

    def test_latest_missing_state_is_readonly_rejection(self):
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as folder:
            env = dict(os.environ)
            env["XDG_STATE_HOME"] = folder
            res = subprocess.run(["python3", "-B", str(SCRIPT), "--latest"],
                                 capture_output=True, text=True, check=False,
                                 env=env, timeout=15)
            self.assertEqual(res.returncode, 2)
            self.assertIn("H6_FORENSIC_VERDICT=INVALID_OR_INCONSISTENT", res.stderr)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_latest_and_explicit_ids_do_not_mix(self):
        p = subprocess.run(
            ["python3", "-B", str(SCRIPT), "--latest",
             "--expected-id", self.cid],
            capture_output=True, text=True, check=False, timeout=15)
        self.assertEqual(p.returncode, 2)
        self.assertIn("cannot_combine_latest_and_explicit_ids", p.stderr)

    def test_wizard_menu21_is_readonly_audit(self):
        menu = (ROOT / "scripts/wizard/benchmark-menu.sh").read_text()
        self.assertIn("wizard_menu_option 21", menu)
        self.assertIn("wizard_h6_forensics_readonly", menu)
        self.assertIn("hybrid-h6-forensics-readonly.py", menu)
        self.assertIn("--latest", menu)

    def test_no_host_mutations(self):
        source = SCRIPT.read_text()
        for forbidden in ("docker start", "docker stop", "docker rm", "systemctl start",
                          "systemctl enable", "rm -rf", "rmtree(", "unlink(", "git reset",
                          "swapoff", "open('w'", "write_text(", "write_bytes("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
