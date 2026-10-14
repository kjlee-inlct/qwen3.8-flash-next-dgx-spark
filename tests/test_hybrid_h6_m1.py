"""Host-free H6 isolated session safety regression."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/wizard/hybrid-h6-m1.py"
BENCH = ROOT / "scripts/wizard/with-h6-session-lock.sh"
SERVE = ROOT / "scripts/serve.sh"
MONITOR = ROOT / "scripts/runtime/monitor-runtime.sh"
MENU = ROOT / "scripts/wizard/benchmark-menu.sh"
spec = importlib.util.spec_from_file_location("hybrid_h6_m1", SCRIPT)
assert spec and spec.loader
h6 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h6)


class HybridH6M1Tests(unittest.TestCase):
    def test_plan_no_host_mutation(self):
        result = subprocess.run(["python3", "-B", str(SCRIPT), "plan"],
                                capture_output=True, text=True, check=False, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("H6_PLAN=ISOLATED_16G_NO_BOOT", result.stdout)
        self.assertIn("H6_EXPERIMENT_PORT=127.0.0.1:18890", result.stdout)

    def test_missing_full_old_id_rejected(self):
        with self.assertRaises(h6.GuardError):
            h6.old_snapshot("incorrect")

    def sample(self):
        record = {"name": "qwen38-hybrid-h6-m1-20261014130000-aaaaaaaa",
                  "id": "a" * 64, "old_id": "f" * 64,
                  "image_id": "sha256:" + "c" * 64}
        container = {
            "Id": record["id"], "Image": record["image_id"],
            "Config": {"Labels": {"qwen38.abtrial": "hybrid",
                                  "qwen38.variant": "h6-m1",
                                  "qwen38.predecessor": record["old_id"]}},
            "HostConfig": {
                "RestartPolicy": {"Name": "no"},
                "PortBindings": {"18890/tcp": [{"HostIp": "127.0.0.1",
                                                 "HostPort": "18890"}]},
            },
        }
        return record, container

    def test_exact_id_and_labels(self):
        record, container = self.sample()
        with patch.object(h6, "inspect", return_value=container):
            self.assertEqual(h6.validate_record(record), container)
            container["Id"] = "b" * 64
            with self.assertRaises(h6.GuardError):
                h6.validate_record(record)

    def test_public_bind_rejected(self):
        record, container = self.sample()
        container["HostConfig"]["PortBindings"]["18890/tcp"][0]["HostIp"] = "0.0.0.0"
        with patch.object(h6, "inspect", return_value=container):
            with self.assertRaises(h6.GuardError):
                h6.validate_record(record)

    def test_shell_syntax_and_pinned_contract(self):
        for path in (SERVE, MONITOR, BENCH, MENU):
            p = subprocess.run(["bash", "-n", str(path)], capture_output=True,
                               text=True, check=False, timeout=15)
            self.assertEqual(p.returncode, 0, f"{path}: {p.stderr}")
        serve = SERVE.read_text()
        monitor = MONITOR.read_text()
        self.assertIn("hybrid-h6-m1", serve)
        self.assertIn("17179869184", serve)
        self.assertIn("--label qwen38.abtrial=hybrid", serve)
        self.assertIn('"${EXPECTED_ID}|true|hybrid|"*', monitor)
        self.assertIn('"--expected-id"', SCRIPT.read_text())
        self.assertIn('"--wait-running"', SCRIPT.read_text())
        self.assertIn('"docker", "start", record["id"]', SCRIPT.read_text())
        self.assertIn('"docker", "stop", "--timeout", "30", record["id"]', SCRIPT.read_text())

    def test_wizard_approval_is_default_no(self):
        menu = MENU.read_text()
        self.assertIn("wizard_menu_option 20", menu)
        self.assertIn("START_HYBRID_H6_16G", menu)
        self.assertIn("wizard_yes_no 'Approve NEW protected H6 GPU experiment? / 새 H6 실험 기동' no", menu)
        self.assertIn("QWEN38_H6_WIZARD_APPROVED=1", menu)
        script = SCRIPT.read_text()
        self.assertIn("wizard_approval_missing", script)
        self.assertIn("interactive_foreground_tty_required", script)

    def test_bench_lock_attests_before_running(self):
        content = BENCH.read_text()
        self.assertIn("flock -n -s", content)
        self.assertIn("flock -n -x", content)
        self.assertLess(content.index("bench-admission"), content.index('"$@"'))
        self.assertNotIn("docker start", content)
        self.assertNotIn("docker rm", content)

    def test_no_broad_delete(self):
        ctrl = SCRIPT.read_text()
        for forbidden in ("docker rm", "docker image rm", "docker system prune",
                          "rm -rf", "rmtree(", "unlink(", "git reset", "swapoff"):
            self.assertNotIn(forbidden, ctrl)


if __name__ == "__main__":
    unittest.main()
