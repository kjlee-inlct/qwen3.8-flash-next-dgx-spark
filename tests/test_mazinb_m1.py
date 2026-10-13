"""Safety regression tests for isolated mazinb M1. No real Docker start."""
from __future__ import annotations

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
SCRIPT = ROOT / "scripts/runtime/mazinb-m1.py"
spec = importlib.util.spec_from_file_location("mazinb_m1", SCRIPT)
assert spec and spec.loader
M1 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M1
spec.loader.exec_module(M1)


class M1SafetyTests(unittest.TestCase):
    def test_plan_status_missing_and_live_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "HOME": tmp, "XDG_STATE_HOME": str(Path(tmp) / "xdg")}
            env.pop("QWEN38_M1_WIZARD_APPROVED", None)
            for action, expected, rc in (
                ("plan", "M1_START=ONLY_INTERACTIVE_WIZARD_OPT_IN", 0),
                ("status", "M1_SESSION=ABSENT", 0),
                ("run", "requires Wizard", 2),
                ("preflight", "M1_BLOCKED=", 2),
            ):
                with self.subTest(action=action):
                    p = subprocess.run(
                        [sys.executable, str(SCRIPT), action, "--expected-old-id", "a"*64],
                        cwd=ROOT, env=env, text=True, capture_output=True, check=False)
                    self.assertEqual(p.returncode, rc, p.stderr)
                    self.assertIn(expected, p.stdout + p.stderr)
            self.assertFalse((Path(tmp) / "xdg").exists())

    def test_historical_cases_preserved_not_reused(self) -> None:
        names = []
        def fake_inspect(name):
            names.append(name)
            return {"State": {"Status": "exited", "Running": False}}
        with mock.patch.object(M1, "inspect", side_effect=fake_inspect), \
             mock.patch.object(M1, "call", return_value=mock.Mock(stdout="")):
            M1.check_trial_history()
        self.assertEqual(names[:2], ["qwen38-mazinb-kv-a", "qwen38-mazinb-kv-b"])

    def test_running_historical_case_blocks(self) -> None:
        with mock.patch.object(M1, "inspect", side_effect=lambda n: {
                "State": {"Status": "running", "Running": True}} if n.endswith("-kv-a") else None):
            with self.assertRaisesRegex(M1.M1Error, "historical case must be stopped"):
                M1.check_trial_history()

    def test_pinned_id_labels_and_restart_policy(self) -> None:
        rec = {"name": "qwen38-mazinb-m1-20261014070000-1234abcd",
               "id": "a"*64, "old_id": "b"*64, "image_id": "sha256:"+"c"*64}
        obj = {"Id": rec["id"], "Image": rec["image_id"],
               "Config": {"Labels": {"qwen38.abtrial": "mazinb",
                   "qwen38.variant": "m1", "qwen38.predecessor": "b"*64}},
               "HostConfig": {"RestartPolicy": {"Name": "no"}},
               "State": {"Running": False}}
        with mock.patch.object(M1, "inspect", return_value=obj):
            self.assertEqual(M1.pinned_candidate(rec), obj)
        bad = json.loads(json.dumps(obj))
        bad["Config"]["Labels"]["qwen38.predecessor"] = "d"*64
        with mock.patch.object(M1, "inspect", return_value=bad):
            with self.assertRaisesRegex(M1.M1Error, "provenance"):
                M1.pinned_candidate(rec)
        with mock.patch.object(M1, "inspect", return_value=obj):
            with self.assertRaisesRegex(M1.M1Error, "invalid M1 trial identity"):
                M1.pinned_candidate({**rec, "name": "qwen38-flash-next"})

    def test_stop_exact_candidate_only_keeps_docker_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            name = "qwen38-mazinb-m1-20261014070000-1234abcd"
            rec = {"name": name, "id": "a"*64, "phase": "ready_for_bench"}
            running = {"Id": rec["id"], "State": {"Running": True, "ExitCode": 0}}
            stopped = {"Id": rec["id"], "State": {"Running": False, "ExitCode": 0}}
            with mock.patch.object(M1, "pinned_candidate", side_effect=[running, stopped]), \
                 mock.patch.object(M1, "call") as cmd:
                M1.stop_exact(rec, root)
            cmd.assert_called_once_with("docker", "stop", "--timeout", "30", "a"*64)
            self.assertEqual(M1.read_json(root / "active.json")["phase"], "stopped")
            self.assertEqual(M1.read_json(root / (name+".json"))["phase"], "stopped")

    def test_wizard_m1_live_default_no_never_activates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "HOME": tmp, "XDG_STATE_HOME": str(Path(tmp)/"xdg")}
            p = subprocess.run(
                ["/bin/bash", str(ROOT/"wizard.sh"), "--lang", "ko"],
                cwd=ROOT, env=env, input="5\n9\n\n0\n0\n",
                capture_output=True, text=True, timeout=20, check=False)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("NEW GPU-heavy mazinb Docker", p.stdout)
            self.assertFalse((Path(tmp)/"xdg").exists())

    def test_m1_bench_wrapper_blocks_without_active_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            state=root/"xdg"/"qwen38-spark"
            state.mkdir(parents=True)
            (state/"operation.lock").touch()
            env={**os.environ, "HOME":tmp, "XDG_STATE_HOME":str(root/"xdg")}
            p=subprocess.run(["/bin/bash", str(ROOT/"scripts/wizard/m1-benchmark-lock.sh"),
                "--", "/bin/true"], env=env,
                text=True, capture_output=True, check=False)
            self.assertEqual(p.returncode, 2)
            self.assertIn("BENCH_M1=BLOCKED", p.stderr)

    def test_memory_floor_and_active_swap_before_any_start(self) -> None:
        sample = ("MemAvailable: 20000000 kB\nMemFree: 4000000 kB\n"
                  "SwapFree: 9000000 kB\nCmaFree: 100000 kB\n")
        manifest = {"SWAP_FILE": "/swap-ple.img"}
        with mock.patch.object(M1.Path, "read_text", return_value=sample), \
             mock.patch.object(M1, "call", return_value=mock.Mock(stdout="/swap-ple.img\n")):
            M1.memory_admission(manifest)
        low = sample.replace("MemAvailable: 20000000", "MemAvailable: 5000000")
        with mock.patch.object(M1.Path, "read_text", return_value=low), \
             mock.patch.object(M1, "call", side_effect=AssertionError("unexpected swapon")):
            with self.assertRaisesRegex(M1.M1Error, "non-CMA available"):
                M1.memory_admission(manifest)

    def test_inference_smoke_requires_nonempty_assistant_output(self) -> None:
        opener = mock.MagicMock()
        opener.open.return_value.__enter__.return_value.status = 200
        with mock.patch.object(M1.urllib.request, "build_opener", return_value=opener), \
             mock.patch.object(M1.json, "load", return_value={
                 "choices": [{"message": {"role": "assistant", "content": "OK"}}]}):
            M1.inference_smoke()
        with mock.patch.object(M1.urllib.request, "build_opener", return_value=opener), \
             mock.patch.object(M1.json, "load", return_value={"choices": []}):
            with self.assertRaisesRegex(M1.M1Error, "invalid completion"):
                M1.inference_smoke()

    def test_source_enforces_create_before_armed_monitor_and_nonremoval(self) -> None:
        serve=(ROOT/"scripts/serve.sh").read_text()
        watchdog=(ROOT/"scripts/runtime/monitor-runtime.sh").read_text()
        controller=SCRIPT.read_text()
        self.assertIn("DOCKER_LAUNCH=(create)", serve)
        self.assertIn("qwen38.abtrial=mazinb", serve)
        self.assertIn('trial_home = trial_dir / "home"', controller)
        self.assertIn('"HOME": str(trial_home)', controller)
        self.assertIn('"trial_home": str(trial_home)', controller)
        self.assertIn("true|mazinb", watchdog)
        self.assertIn("monitor_dir / \"armed\"", controller)
        self.assertIn("call(\"docker\", \"start\", record[\"id\"])", controller)
        self.assertNotIn('call("docker", "rm"', controller)


if __name__ == "__main__":
    unittest.main()
