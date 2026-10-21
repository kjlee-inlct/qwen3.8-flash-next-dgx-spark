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

    def test_protect_stop_records_failed_stopped_not_clean_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            name = "qwen38-mazinb-m1-20261014070000-1234abcd"
            rec = {"name": name, "id": "a"*64, "phase": "failed",
                   "detail": "candidate triggered memory-protection stop"}
            running = {"Id": rec["id"], "State": {"Running": True, "ExitCode": 1}}
            stopped = {"Id": rec["id"], "State": {"Running": False, "ExitCode": 1}}
            with mock.patch.object(M1, "pinned_candidate", side_effect=[running, stopped]), \
                 mock.patch.object(M1, "call") as cmd:
                M1.stop_exact(rec, Path(tmp))
            cmd.assert_called_once_with("docker", "stop", "--timeout", "30", "a"*64)
            self.assertEqual(M1.read_json(Path(tmp) / "active.json")["phase"],
                             "failed_stopped")

    def test_m1_swap_pressure_available_guard_regression(self) -> None:
        # Execute the real source predicate in an isolated Bash snippet.
        # There is no Docker, kernel, or model side effect in this test.
        monitor = (ROOT / "scripts/runtime/monitor-runtime.sh").read_text()
        section = monitor.split("  if (( noncma_free < free_floor )); then", 1)[1]
        predicate = "  if (( noncma_free < free_floor )); then" + section.split(
            "\n  if (( warning_low == 1 )); then", 1
        )[0]
        cases = (
            # observed DGX: 38 GiB available, swap growth 411 MiB => warn-only
            (1496, 38698, 411, 12, "0"),
            # historical behavior remains protected if guard explicitly off
            (1496, 38698, 411, 0, "1"),
            # near-pressure even when free below 2 GiB + 256 MiB swapped
            (1496, 11264, 411, 12, "1"),
            # primary <10 GiB gate is unchanged without swap activity
            (1496, 9216, 0, 12, "1"),
            # high non-CMA free does not trip the low-free condition
            (3072, 9216, 411, 12, "0"),
        )
        for free_mib, available_mib, growth_mib, gate_gib, expected in cases:
            with self.subTest(free=free_mib, available=available_mib,
                              growth=growth_mib, gate=gate_gib):
                env = "\n".join((
                    f"noncma_free={free_mib * 1024}",
                    f"noncma_available={available_mib * 1024}",
                    f"swap_consumed={growth_mib * 1024}",
                    "free_floor=2097152",
                    "free_gate=10485760",
                    "swap_activity_gate=262144",
                    f"swap_pressure_available_floor={gate_gib * 1048576}",
                    "warning_low=0",
                    "protection_low=0",
                ))
                p = subprocess.run(["bash", "-c", env+"\n"+predicate+
                                   '\nprintf "%s" "$protection_low"'],
                                   check=False, capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(p.stdout, expected)

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

    def test_reinstall_session_uses_new_journal_and_preserves_archived_m1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "qwen38-spark"
            old_dir = state / "mazinb-m1"
            old_dir.mkdir(parents=True)
            old = old_dir / "active.json"
            marker = old_dir / "retired-docker.json"
            prior = {"phase": "stopped", "id": "a"*64, "name": "old-m1"}
            old.write_text(json.dumps(prior), encoding="utf-8")
            marker.write_text(json.dumps({
                "state": "archived_docker_removed",
                "id": prior["id"], "name": prior["name"],
            }), encoding="utf-8")
            before = (old.read_bytes(), marker.read_bytes())
            with mock.patch.dict(os.environ, {"XDG_STATE_HOME": tmp}), \
                 mock.patch.object(M1, "SESSION_SLOT", "reinstall"):
                root, _, target = M1.state_paths()
                self.assertEqual(root, state)
                self.assertEqual(target, state / "mazinb-m1-reinstall")
                self.assertEqual(
                    M1.historical_retirement_snapshot(state)["active_sha256"],
                    __import__("hashlib").sha256(before[0]).hexdigest())
                self.assertFalse(target.exists())
                bad = json.loads(marker.read_text())
                bad["id"] = "b"*64
                marker.write_text(json.dumps(bad))
                with self.assertRaisesRegex(M1.M1Error, "retirement identities"):
                    M1.historical_retirement_snapshot(state)
                marker.write_bytes(before[1])
            self.assertEqual((old.read_bytes(), marker.read_bytes()), before)

    def test_reinstall_slot_refuses_managed_enabled_or_owned_service(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "install.env").write_text("synthetic")
            data = {"PHASE": "complete", "MODEL_PROFILE": "orcarouter",
                    "MONITOR_ENABLED": "1", "MONITOR_PROTECT": "1",
                    "SERVICE_ENABLED": "0", "SERVICE_OWNED": "0"}
            with mock.patch.object(M1, "parse_install", return_value=data), \
                 mock.patch.object(M1, "SESSION_SLOT", "reinstall"):
                M1.read_manifest(root)
                data["SERVICE_OWNED"] = "1"
                with self.assertRaisesRegex(M1.M1Error, "disabled/unowned"):
                    M1.read_manifest(root)
                data["SERVICE_OWNED"] = "0"
                data["SERVICE_ENABLED"] = "1"
                with self.assertRaisesRegex(M1.M1Error, "disabled/unowned"):
                    M1.read_manifest(root)
            with mock.patch.object(M1, "parse_install", return_value=data), \
                 mock.patch.object(M1, "SESSION_SLOT", "historical"):
                M1.read_manifest(root)

    def test_reinstalled_slot_cli_is_separate_and_cannot_start_unapproved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "XDG_STATE_HOME": tmp}
            env.pop("QWEN38_M1_WIZARD_APPROVED", None)
            for action, expected, code in (
                ("status", "M1_SESSION=ABSENT", 0),
                ("plan", "M1_SESSION_SLOT=reinstall", 0),
                ("run", "requires Wizard", 2),
            ):
                p = subprocess.run(
                    [sys.executable, str(SCRIPT), action,
                     "--session-slot", "reinstall"],
                    env=env, cwd=ROOT, text=True, capture_output=True, check=False)
                self.assertEqual(p.returncode, code, p.stdout + p.stderr)
                self.assertIn(expected, p.stdout + p.stderr)
            self.assertFalse((Path(tmp) / "qwen38-spark").exists())
            bench = (ROOT / "scripts/wizard/m1-benchmark-lock.sh").read_text()
            self.assertIn('M1_STATE="$STATE_DIR/mazinb-m1-reinstall"', bench)
            self.assertIn('bench-admission --session-slot "$SLOT"', bench)

    def test_reinstall_unit_check_blocks_autostart_and_active_proxy(self) -> None:
        def mock_call(*args, **kwargs):
            return mock.Mock(returncode=0, stdout=(
                "LoadState=not-found\nActiveState=inactive\nUnitFileState=not-found\n"))
        with mock.patch.object(M1, "call", side_effect=mock_call):
            M1.assert_project_units_nonstarting()
        def active_call(*args, **kwargs):
            return mock.Mock(returncode=0, stdout=(
                "LoadState=loaded\nActiveState=active\nUnitFileState=enabled\n"))
        with mock.patch.object(M1, "call", side_effect=active_call):
            with self.assertRaisesRegex(M1.M1Error, "boot enabled"):
                M1.assert_project_units_nonstarting()

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
