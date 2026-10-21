"""P1c pure supervisor protocol tests: no host I/O, no real worker."""
from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/runtime/m1-supervisor-protocol.py"
SPEC = importlib.util.spec_from_file_location("m1_p1c_protocol", SOURCE)
assert SPEC and SPEC.loader
P = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = P
SPEC.loader.exec_module(P)


class P1cProtocolTests(unittest.TestCase):
    def setUp(self):
        self.owner = P.Identity(
            candidate_name="qwen38-mazinb-m1-20261014013811-16ced779",
            candidate_id="a" * 64, predecessor_id="b" * 64,
            owner_token="c" * 32, supervisor_pid=23456,
            supervisor_start_ticks=987, systemd_invocation_id="d" * 32,
        )
        self.base = P.Observation(
            owner=self.owner, journal_token=self.owner.owner_token,
            journal_candidate_id=self.owner.candidate_id,
            monitor_candidate_id=self.owner.candidate_id,
            monitor_armed=True, monitor_alive=True,
            heartbeat_age_seconds=1.0, supervisor_alive=True,
            docker_running=False, docker_exited_proven=False,
            docker_exit_code=None, docker_oom_killed=False,
            benchmark_lease_free=True,
        )
        self.created = P.Session(self.owner)
        self.armed = P.advance(self.created, "ARM_OBSERVED", self.base)
        self.live_obs = replace(self.base, docker_running=True)
        self.running = P.advance(self.armed, "RUNNING_OBSERVED", self.live_obs)

    def stopped(self, **kwargs):
        data = {
            "docker_running": False, "docker_exited_proven": True,
            "docker_exit_code": 0, "monitor_alive": False,
            "monitor_ended_evidence": True, "exact_stop_ack": True,
        }
        data.update(kwargs)
        return replace(self.live_obs, **data)

    def stopped_after_crash(self, **kwargs):
        data = {"supervisor_alive": False, "exact_stop_ack": False}
        data.update(kwargs)
        return replace(self.stopped(), **data)

    def assert_blocks(self, session, event, observed, reason, **kwargs):
        with self.assertRaisesRegex(P.ProtocolBlocked, reason):
            P.advance(session, event, observed, **kwargs)

    def test_synthetic_scenario_does_not_execute_any_commands(self):
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("subprocess called")), \
                mock.patch.object(subprocess, "Popen", side_effect=AssertionError("spawned")):
            P.synthetic_scenario()

    def test_valid_explicit_stop_needs_ack_and_lease(self):
        stopping = P.advance(self.running, "REQUEST_STOP", self.live_obs,
                             operator_approved=True)
        finished = P.advance(stopping, "STOP_VERIFIED", self.stopped())
        self.assertEqual((finished.phase, finished.exit_code, finished.shutdown_cause),
                         ("STOPPED", 0, "EXACT_STOP_ACK_OBSERVED"))

    def test_default_no_never_authorizes_stop(self):
        self.assert_blocks(self.running, "REQUEST_STOP", self.live_obs,
                           "explicit_stop_approval_missing")
        self.assert_blocks(self.running, "REQUEST_STOP", self.live_obs,
                           "approval_invalid", operator_approved=1)

    def test_no_stop_during_benchmark_lease(self):
        self.assert_blocks(self.running, "REQUEST_STOP",
                           replace(self.live_obs, benchmark_lease_free=False),
                           "benchmark_lease_held", operator_approved=True)

    def test_identity_replay_pid_reuse_and_invocation_drift(self):
        for owner in (
            replace(self.owner, supervisor_start_ticks=988),
            replace(self.owner, supervisor_pid=23457),
            replace(self.owner, systemd_invocation_id="e" * 32),
            replace(self.owner, owner_token="f" * 32),
            replace(self.owner, candidate_id="9" * 64),
        ):
            with self.subTest(owner=owner):
                self.assert_blocks(self.running, "REQUEST_STOP",
                                   replace(self.live_obs, owner=owner),
                                   "owner_identity_drift", operator_approved=True)

    def test_independent_journal_and_watchdog_pins(self):
        for field, value, reason in (
            ("journal_token", "0" * 32, "journal_token_drift"),
            ("journal_candidate_id", "0" * 64, "journal_candidate_drift"),
            ("monitor_candidate_id", "0" * 64, "watchdog_candidate_drift"),
            ("monitor_armed", False, "watchdog_not_armed"),
        ):
            with self.subTest(field=field):
                self.assert_blocks(self.running, "REQUEST_STOP",
                                   replace(self.live_obs, **{field: value}),
                                   reason, operator_approved=True)

    def test_stale_watchdog_and_unproven_supervisor_block_stop(self):
        self.assert_blocks(self.running, "REQUEST_STOP",
                           replace(self.live_obs, heartbeat_age_seconds=16),
                           "watchdog_heartbeat_stale", operator_approved=True)
        self.assert_blocks(self.running, "REQUEST_STOP",
                           replace(self.live_obs, supervisor_alive=False),
                           "candidate_not_supervised_running",
                           operator_approved=True)

    def test_no_stop_finalization_without_exact_ack_and_exited_proof(self):
        stopping = P.advance(self.running, "REQUEST_STOP", self.live_obs,
                             operator_approved=True)
        self.assert_blocks(stopping, "STOP_VERIFIED",
                           self.stopped(exact_stop_ack=False),
                           "exact_stop_not_acknowledged")
        self.assert_blocks(stopping, "STOP_VERIFIED",
                           self.stopped(docker_exited_proven=False),
                           "candidate_not_proved_exited")
        self.assert_blocks(stopping, "STOP_VERIFIED",
                           self.stopped(monitor_alive=True),
                           "monitor_end_not_proved")
        self.assert_blocks(stopping, "STOP_VERIFIED",
                           self.stopped(monitor_ended_evidence=False),
                           "monitor_end_not_proved")
        self.assert_blocks(stopping, "STOP_VERIFIED",
                           self.stopped(benchmark_lease_free=False),
                           "benchmark_lease_held")

    def test_supervisor_loss_requires_reconcile_not_implicit_stop(self):
        lost = P.advance(self.running, "SUPERVISOR_LOST",
                         replace(self.live_obs, supervisor_alive=False))
        self.assertEqual((lost.phase, lost.shutdown_cause),
                         ("RECOVERY_REQUIRED", "UNDETERMINED"))
        self.assert_blocks(lost, "REQUEST_STOP", self.stopped_after_crash(),
                           "invalid_stop_phase", operator_approved=True)
        self.assert_blocks(lost, "RECONCILE_STOPPED",
                           replace(self.live_obs, supervisor_alive=False),
                           "candidate_not_proved_exited")
        self.assert_blocks(lost, "RECONCILE_STOPPED",
                           self.stopped(supervisor_alive=True),
                           "supervisor_still_active")
        recovered = P.advance(lost, "RECONCILE_STOPPED", self.stopped_after_crash())
        self.assertEqual((recovered.phase, recovered.exit_code,
                          recovered.shutdown_cause), ("STOPPED", 0, "UNDETERMINED"))

    def test_memory_protection_and_oom_are_not_clean_success(self):
        lost = P.advance(self.running, "SUPERVISOR_LOST",
                         replace(self.live_obs, supervisor_alive=False))
        for observation in (
            self.stopped_after_crash(protective_stop_marker_pinned=True),
            self.stopped_after_crash(docker_oom_killed=True),
            self.stopped_after_crash(docker_exit_code=137),
        ):
            with self.subTest(observation=observation):
                recovered = P.advance(lost, "RECONCILE_STOPPED", observation)
                self.assertEqual(recovered.phase, "FAILED_STOPPED")

    def test_invalid_identity_and_observation_types_block(self):
        with self.assertRaisesRegex(P.ProtocolBlocked, "predecessor_alias"):
            replace(self.owner, predecessor_id=self.owner.candidate_id)
        with self.assertRaisesRegex(P.ProtocolBlocked, "supervisor_pid_invalid"):
            replace(self.owner, supervisor_pid=True)
        with self.assertRaisesRegex(P.ProtocolBlocked, "invalid_heartbeat_age"):
            replace(self.live_obs, heartbeat_age_seconds=float("nan"))
        with self.assertRaisesRegex(P.ProtocolBlocked, "docker_exit_code_invalid"):
            lost = P.advance(self.running, "SUPERVISOR_LOST",
                             replace(self.live_obs, supervisor_alive=False))
            P.advance(lost, "RECONCILE_STOPPED",
                      self.stopped_after_crash(docker_exit_code=True))

    def test_illegal_replay_and_non_monotonic_transitions_fail_closed(self):
        self.assert_blocks(self.created, "RUNNING_OBSERVED", self.live_obs,
                           "invalid_running_phase")
        self.assert_blocks(self.running, "ARM_OBSERVED", self.base,
                           "invalid_arm_phase")
        self.assert_blocks(self.running, "MAGIC_START", self.live_obs,
                           "unknown_event")

    def test_cli_simulation_has_no_host_commands(self):
        p = subprocess.run([sys.executable, "-B", str(SOURCE), "simulate"],
                           check=False, text=True, capture_output=True, timeout=8)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("M1_P1C_SIMULATION=PASS_IN_MEMORY", p.stdout)
        self.assertIn("M1_P1C_DOCKER_ACTION=NONE", p.stdout)
        self.assertIn("M1_P1C_USER_SERVICE_MUTATION=NONE", p.stdout)


if __name__ == "__main__":
    unittest.main()
