"""Synthetic guardrails for the experimental, wizard-only OrcaRouter trial."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/runtime/orcarouter-ab-trial.py"
SPEC = importlib.util.spec_from_file_location("orcarouter_ab_trial", PATH)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

class OrcaRouterTrialTests(unittest.TestCase):
    def test_plan_does_not_touch_docker_or_host(self):
        with mock.patch.object(MOD, "call", side_effect=AssertionError("unexpected host command")):
            p = subprocess.run(["python3", str(PATH), "plan"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("AB_TRIAL_WIZARD_PLAN_ONLY=YES", p.stdout)
        self.assertIn("AB_TRIAL_START=OPT_IN_EXACT_OLD_DOCKER_ID", p.stdout)

    def test_preflight_without_exact_old_id_blocks_before_host_access(self):
        run = subprocess.run(["python3", str(PATH), "preflight", "--variant", "v029"],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn("exact old Docker ID", run.stderr)

    def test_physical_preflight_cannot_create_a_candidate(self):
        from argparse import Namespace
        before = {"Id": "f" * 64}
        with mock.patch.object(MOD, "host_state",
                               return_value=(Path("/a"), Path("/b"), Path("/c"))), \
             mock.patch.object(MOD, "safe_dir"), \
             mock.patch.object(MOD, "read_manifest", return_value=({"MODEL_PROFILE": "orcarouter"}, "a" * 64)), \
             mock.patch.object(MOD, "admission", return_value=(before, "/b/releases/abc")), \
             mock.patch.object(MOD, "image_identity", return_value="sha256:" + "a" * 64), \
             mock.patch.object(MOD, "preserve"), \
             mock.patch.object(MOD, "call", side_effect=AssertionError("docker create/start forbidden")), \
             mock.patch.object(MOD.hashlib, "sha256", return_value=mock.Mock(hexdigest=lambda: "a" * 64)), \
             mock.patch.object(MOD.Path, "read_bytes", return_value=b""), \
             mock.patch.object(MOD.Path, "resolve", return_value=Path("/b/releases/abc")):
            MOD.preflight(Namespace(variant="v029", expected_old_id="f" * 64))

    def test_missing_explicit_old_id_blocks_start(self):
        p = subprocess.run(["python3", str(PATH), "start", "--variant", "legacy"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("exact old Docker ID", p.stderr)

    def test_old_container_identity_mismatch_blocks(self):
        old = {"Id": "a" * 64, "Image": "sha256:" + "c"*64,
               "State": {"Status": "exited", "Running": False, "OOMKilled": False}}
        new = {**old, "Id": "b" * 64}
        with mock.patch.object(MOD, "inspect", return_value=new):
            with self.assertRaisesRegex(MOD.TrialError, "identity/status drift"):
                MOD.preserve(old)

    def test_wrong_trial_label_refuses_exact_id_stop(self):
        record = {"name": "qwen38-ab-legacy", "container": "b" * 64,
                  "image_id": "sha256:" + "a"*64,
                  "variant": "legacy", "old_id": "c" * 64}
        test_container = {"Id": "b" * 64, "Image": record["image_id"],
                          "Config": {"Labels": {"qwen38.abtrial": "wrong"}},
                          "State": {"Running": True}}
        with mock.patch.object(MOD, "inspect", return_value=test_container):
            with self.assertRaisesRegex(MOD.TrialError, "labels drift"):
                MOD.trial_identity(record)

    def test_stop_when_wrong_image_never_calls_docker_stop(self):
        record = {"name": "qwen38-ab-v029", "container": "b" * 64,
                  "image_id": "sha256:" + "a"*64,
                  "variant": "v029", "old_id": "c" * 64}
        candidate = {"Id": "b" * 64, "Image": "sha256:" + "d"*64,
                     "Config": {"Labels": {"qwen38.abtrial": "orcarouter",
                                          "qwen38.variant": "v029",
                                          "qwen38.predecessor": "c"*64}},
                     "State": {"Running": True}}
        with mock.patch.object(MOD, "lock_is_held"), mock.patch.object(MOD, "read_json", return_value=record), \
             mock.patch.object(MOD, "inspect", return_value=candidate), \
             mock.patch.object(MOD, "call", side_effect=AssertionError("unexpected Docker STOP")):
            with self.assertRaisesRegex(MOD.TrialError, "image ID drift"):
                MOD.stop()

    def test_admission_rejects_active_service(self):
        with mock.patch.object(MOD, "call", return_value=mock.Mock(returncode=0)):
            import tempfile
            with tempfile.TemporaryDirectory() as d:
                state = Path(d); data = state / "data"; data.mkdir()
                release = data / "releases" / ("a"*40)
                release.mkdir(parents=True)
                (data / "current").symlink_to(release)
                with self.assertRaisesRegex(MOD.TrialError, "managed service is active"):
                    MOD.admission(state, data, {}, "f"*64, "legacy")

    def test_stopped_legacy_allows_v029_without_deletion(self):
        stopped = {"Id": "a" * 64, "Config": {"Labels": {
            "qwen38.abtrial": "orcarouter", "qwen38.variant": "legacy"}},
            "State": {"Running": False, "Status": "exited"}}
        with mock.patch.object(MOD, "inspect",
                               side_effect=lambda name: stopped if name == "qwen38-ab-legacy" else None):
            MOD.check_candidates("v029")
            with self.assertRaisesRegex(MOD.TrialError, "target trial name already exists"):
                MOD.check_candidates("legacy")

    def test_running_legacy_refuses_v029(self):
        running = {"Config": {"Labels": {
            "qwen38.abtrial": "orcarouter", "qwen38.variant": "legacy"}},
            "State": {"Running": True, "Status": "running"}}
        with mock.patch.object(MOD, "inspect",
                               side_effect=lambda name: running if name == "qwen38-ab-legacy" else None):
            with self.assertRaisesRegex(MOD.TrialError, "not cleanly stopped"):
                MOD.check_candidates("v029")

    def test_prearmed_monitor_times_out_without_start_and_no_docker_stop(self):
        import tempfile
        import stat
        import os
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            wd = root / "monitor"
            wd.mkdir()
            docker = bin_dir / "docker"
            docker.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                'if [[ "$1" == inspect ]]; then\n'
                '  if [[ "${2:-}" == --format ]]; then printf "%s\\n" "$AB_FAKE_ID"; exit 0; fi\n'
                '  if [[ "${2:-}" == -f ]]; then printf "false\\n"; exit 0; fi\n'
                '  exit 0\n'
                'fi\n'
                'echo "unexpected Docker mutation: $*" >&2\n'
                'exit 70\n',
                encoding="utf-8",
            )
            docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
            argv = [
                "bash", str(ROOT / "scripts/runtime/monitor-runtime.sh"),
                "--container", "qwen38-ab-legacy", "--expected-id", "a" * 64,
                "--wait-running", "1", "--state-dir", str(wd),
                "--armed-file", str(wd / "armed"), "--heartbeat-file", str(wd / "heartbeat"),
                "--protect",
            ]
            proc = subprocess.run(
                argv, cwd=ROOT, text=True, capture_output=True, timeout=6,
                env={**os.environ, "PATH": str(bin_dir) + ":" + os.environ.get("PATH", ""),
                     "AB_FAKE_ID": "a" * 64}, check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("AB_MONITOR_ARMED_ID=" + "a" * 64, proc.stdout)
            self.assertEqual((wd / "armed").read_text().strip(), "a" * 64)
            self.assertIn("trial never became running", proc.stderr)
            self.assertFalse((wd / "heartbeat").exists())

    def test_prearmed_monitor_refuses_wrong_id_before_creating_arm_file(self):
        import tempfile
        import stat
        import os
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            wd = root / "monitor"
            wd.mkdir()
            docker = bin_dir / "docker"
            docker.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                'if [[ "$1" == inspect ]]; then\n'
                '  if [[ "${2:-}" == --format ]]; then printf "%s\\n" "$AB_FAKE_ID"; fi\n'
                '  exit 0\n'
                'fi\n'
                'exit 70\n',
                encoding="utf-8",
            )
            docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
            proc = subprocess.run([
                "bash", str(ROOT / "scripts/runtime/monitor-runtime.sh"),
                "--container", "qwen38-ab-v029",
                "--expected-id", "a" * 64,
                "--wait-running", "1", "--state-dir", str(wd),
                "--armed-file", str(wd / "armed"),
                "--heartbeat-file", str(wd / "heartbeat"), "--protect",
            ], text=True, capture_output=True, timeout=6, cwd=ROOT,
                env={**os.environ, "PATH": str(bin_dir) + ":" + os.environ.get("PATH", ""),
                     "AB_FAKE_ID": "b" * 64},
                check=False)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("trial container ID drift before arm", proc.stderr)
            self.assertFalse((wd / "armed").exists())

    def test_source_isolation_honors_legacy_and_v029(self):
        script = (ROOT / "scripts/serve.sh").read_text()
        self.assertIn('DOCKER_LAUNCH=(create)', script)
        self.assertIn('TRIAL_PREDECESSOR_ID', script)
        self.assertIn('TRIAL_CREATE_ONLY', script)
        self.assertIn('qwen38.abtrial=orcarouter', script)
        monitor = (ROOT / "scripts/runtime/monitor-runtime.sh").read_text()
        self.assertIn('--expected-id', monitor)
        self.assertIn('--armed-file', monitor)
        self.assertIn('--heartbeat-file', monitor)
        self.assertIn('stop_target="${EXPECTED_ID}"', monitor)

if __name__ == "__main__":
    unittest.main()
