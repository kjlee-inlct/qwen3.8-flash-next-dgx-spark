"""P1d in-memory command admission tests; no worker or system APIs."""
from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/runtime/m1-supervisor-command-protocol.py"
SPEC = importlib.util.spec_from_file_location("m1_p1d_protocol", SOURCE)
assert SPEC and SPEC.loader
P = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = P
SPEC.loader.exec_module(P)


class P1dCommandProtocolTests(unittest.TestCase):
    def setUp(self):
        self.owner = P.OwnerBinding(
            candidate_id="a" * 64, predecessor_id="b" * 64,
            owner_token="c" * 32, invocation_id="d" * 32,
            supervisor_pid=24680, supervisor_start_ticks=101,
            owner_uid=1000,
        )
        self.request = P.Envelope(
            version=1, action="REQUEST_STOP", owner=self.owner,
            request_nonce="e" * 32, issued_ms=10_000, expires_ms=20_000,
        )
        self.history = P.ReplayState()

    def stop(self, envelope=None, history=None, **kwargs):
        config = {
            "peer_uid": 1000, "now_ms": 15_000,
            "operator_approved": True, "linger_enabled": True,
            "benchmark_lease_free": True, "watchdog_fresh": True,
            "supervisor_verified": True,
        }
        config.update(kwargs)
        return P.admit(envelope or self.request, self.owner,
                       history if history is not None else self.history, **config)

    def test_successful_stop_only_admits_gate_not_real_action(self):
        receipt, state = self.stop()
        self.assertEqual(receipt.gate, "STOP_GATE_ADMITTED_SYNTHETIC")
        self.assertFalse(receipt.worker_action_performed)
        self.assertIn(self.request.request_nonce, state.used_nonces)
        self.assertEqual(self.history.used_nonces, frozenset())

    def test_default_no_stop_is_blocked(self):
        with self.assertRaisesRegex(P.CommandBlocked, "explicit_stop_approval_missing"):
            self.stop(operator_approved=False)
        with self.assertRaisesRegex(P.CommandBlocked, "operator_approved_not_bool"):
            self.stop(operator_approved=1)

    def test_linger_no_never_admits_synthetic_stop(self):
        with self.assertRaisesRegex(P.CommandBlocked, "persistent_user_manager_unqualified"):
            self.stop(linger_enabled=False)

    def test_stale_monitor_or_unverified_supervisor(self):
        for flag, reason in (
            ("watchdog_fresh", "watchdog_stale_or_untrusted"),
            ("supervisor_verified", "worker_identity_unverified"),
            ("benchmark_lease_free", "benchmark_lease_held"),
        ):
            with self.subTest(flag=flag):
                with self.assertRaisesRegex(P.CommandBlocked, reason):
                    self.stop(**{flag: False})

    def test_nonce_replay_is_blocked(self):
        _, history = self.stop()
        with self.assertRaisesRegex(P.CommandBlocked, "command_nonce_replay"):
            self.stop(history=history)

    def test_expired_future_and_excessive_ttl_blocked(self):
        with self.assertRaisesRegex(P.CommandBlocked, "command_expired_or_future"):
            self.stop(now_ms=20_001)
        with self.assertRaisesRegex(P.CommandBlocked, "command_expired_or_future"):
            self.stop(now_ms=9_999)
        with self.assertRaisesRegex(P.CommandBlocked, "command_ttl_invalid"):
            replace(self.request, expires_ms=40_001)
        with self.assertRaisesRegex(P.CommandBlocked, "command_ttl_invalid"):
            replace(self.request, expires_ms=10_000)

    def test_owner_identity_and_peer_uid_are_pinned(self):
        for field, value in (
            ("candidate_id", "f" * 64),
            ("predecessor_id", "f" * 64),
            ("invocation_id", "f" * 32),
            ("owner_token", "f" * 32),
            ("supervisor_pid", 24681),
            ("supervisor_start_ticks", 102),
            ("owner_uid", 1001),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(
                P.CommandBlocked, "owner_binding_drift"
            ):
                self.stop(envelope=replace(
                    self.request, owner=replace(self.owner, **{field: value})
                ))
        with self.assertRaisesRegex(P.CommandBlocked, "peer_uid_mismatch"):
            self.stop(peer_uid=1001)

    def test_unknown_action_and_invalid_version_fail(self):
        with self.assertRaisesRegex(P.CommandBlocked, "command_action_forbidden"):
            replace(self.request, action="START")
        with self.assertRaisesRegex(P.CommandBlocked, "protocol_version_unsupported"):
            replace(self.request, version=2)
        with self.assertRaisesRegex(P.CommandBlocked, "request_nonce_invalid"):
            replace(self.request, request_nonce="xyz")

    def test_view_status_is_read_only_admission_even_when_linger_no(self):
        request = replace(self.request, action="VIEW_STATUS")
        receipt, state = P.admit(
            request, self.owner, self.history, peer_uid=1000, now_ms=15_000,
        )
        self.assertEqual(receipt.gate, "VIEW_STATUS_ADMITTED_SYNTHETIC")
        self.assertFalse(receipt.worker_action_performed)
        self.assertIn(request.request_nonce, state.used_nonces)

    def test_replay_state_capacity_fails_closed(self):
        history = P.ReplayState(frozenset(f"{i:032x}" for i in range(P.MAX_NONCES)))
        with self.assertRaisesRegex(P.CommandBlocked, "nonce_history_full"):
            self.stop(history=history)
        self.assertEqual(len(history.used_nonces), P.MAX_NONCES)

    def test_no_host_system_calls_in_synthetic_simulator(self):
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("subprocess called")), \
                mock.patch.object(subprocess, "Popen", side_effect=AssertionError("spawned")):
            P.simulated_example()

    def test_cli_emits_synthetic_only_and_no_mutation(self):
        process = subprocess.run(
            [sys.executable, "-B", str(SOURCE), "simulate"], text=True,
            capture_output=True, timeout=8, check=False,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        for marker in (
            "M1_P1D_SIMULATION=PASS_IN_MEMORY",
            "M1_P1D_SIM_LINGER_NO=BLOCKED",
            "M1_P1D_SIM_NONCE_REPLAY=BLOCKED",
            "M1_P1D_SIM_REAL_STOP=NOT_PERFORMED",
            "M1_P1D_DOCKER_ACTION=NONE",
        ):
            self.assertIn(marker, process.stdout)


if __name__ == "__main__":
    unittest.main()
