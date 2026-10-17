"""P1e copy-on-write journal simulation; never writes real files."""
from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/runtime/m1-supervisor-journal-protocol.py"
SPEC = importlib.util.spec_from_file_location("m1_p1e_protocol", SOURCE)
assert SPEC and SPEC.loader
P = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = P
SPEC.loader.exec_module(P)


class P1eJournalSafety(unittest.TestCase):
    def setUp(self):
        self.owner = P.Owner("a" * 64, "b" * 64, "c" * 32)
        self.nonce = "d" * 32
        self.empty = P.Ledger()
        self.intent = P.prepare_intent(
            self.empty, self.owner, self.nonce,
            operator_approved=True, admission_verified=True,
        )
        self.durable = P.commit(
            self.empty, self.owner, self.intent, flush_acknowledged=True,
        )

    def exit_proposal(self, **kw):
        opts = dict(
            candidate_id=self.owner.candidate_id,
            proven_exited=True, monitor_ended=True,
            benchmark_lease_free=True, docker_running=False,
            exit_code=0, cause="UNDETERMINED",
        )
        opts.update(kw)
        return P.prepare_outcome(self.durable, self.owner, self.nonce, **opts)

    def test_in_memory_smoke_never_calls_host(self):
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("host call")), \
                mock.patch.object(subprocess, "Popen", side_effect=AssertionError("spawn")):
            P.simulate()

    def test_prepared_not_committed_is_lost_after_crash(self):
        self.assertEqual(P.recover(self.empty, self.owner),
                         "NO_DURABLE_STOP_INTENT")
        with self.assertRaisesRegex(P.JournalBlocked, "durable_commit_not_acknowledged"):
            P.commit(self.empty, self.owner, self.intent)
        self.assertFalse(self.empty.records)

    def test_durable_intent_never_autoreplays(self):
        self.assertEqual(P.recover(self.durable, self.owner),
                         "RECONCILE_REQUIRED_NO_AUTO_REPLAY")
        with self.assertRaisesRegex(P.JournalBlocked, "nonce_or_intent_already_recorded"):
            P.prepare_intent(
                self.durable, self.owner, self.nonce,
                operator_approved=True, admission_verified=True,
            )
        with self.assertRaisesRegex(P.JournalBlocked, "journal_compare_and_swap_conflict"):
            P.commit(self.durable, self.owner, self.intent,
                     flush_acknowledged=True)

    def test_default_no_and_injected_not_attested_stop_gate(self):
        with self.assertRaisesRegex(P.JournalBlocked, "stop_consent_or_admission_missing"):
            P.prepare_intent(self.empty, self.owner, self.nonce)
        with self.assertRaisesRegex(P.JournalBlocked, "stop_consent_or_admission_missing"):
            P.prepare_intent(
                self.empty, self.owner, self.nonce,
                operator_approved=True, admission_verified=False,
            )
        with self.assertRaisesRegex(P.JournalBlocked, "approval_type_invalid"):
            P.prepare_intent(
                self.empty, self.owner, self.nonce,
                operator_approved=1, admission_verified=True,
            )

    def test_outcome_staged_but_not_committed_cannot_finalize(self):
        stage = self.exit_proposal()
        self.assertEqual(P.recover(self.durable, self.owner),
                         "RECONCILE_REQUIRED_NO_AUTO_REPLAY")
        with self.assertRaisesRegex(P.JournalBlocked, "durable_commit_not_acknowledged"):
            P.commit(self.durable, self.owner, stage)
        done = P.commit(
            self.durable, self.owner, stage, flush_acknowledged=True)
        self.assertEqual(P.recover(done, self.owner),
                         "EXIT_RECORDED_CAUSE_UNDETERMINED")

    def test_exact_candidate_and_immutable_owner_required(self):
        with self.assertRaisesRegex(P.JournalBlocked, "candidate_identity_mismatch"):
            self.exit_proposal(candidate_id="e" * 64)
        with self.assertRaisesRegex(P.JournalBlocked, "journal_owner_drift"):
            P.recover(self.durable, replace(self.owner, owner_token="e" * 32))
        with self.assertRaisesRegex(P.JournalBlocked, "nonce_mismatch"):
            P.prepare_outcome(
                self.durable, self.owner, "e" * 32,
                candidate_id=self.owner.candidate_id,
            )

    def test_unproven_docker_monitor_and_lease_block_finalize(self):
        for field, value, reason in (
            ("proven_exited", False, "docker_exit_unproven"),
            ("docker_running", True, "docker_exit_unproven"),
            ("monitor_ended", False, "monitor_end_unproven"),
            ("benchmark_lease_free", False, "benchmark_lease_held"),
            ("exit_code", True, "exit_code_unproven"),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(
                P.JournalBlocked, reason
            ):
                self.exit_proposal(**{field: value})

    def test_failed_stop_and_undetermined_reason_are_distinct(self):
        for code, cause, outcome in (
            (0, "EXACT_STOP_ACK", "EXIT_RECORDED_EXACT_ACK"),
            (0, "UNDETERMINED", "EXIT_RECORDED_CAUSE_UNDETERMINED"),
            (0, "MEMORY_PROTECTION_MARKER", "EXIT_RECORDED_FAILED"),
            (137, "UNDETERMINED", "EXIT_RECORDED_FAILED"),
        ):
            with self.subTest(code=code, cause=cause):
                proposal = self.exit_proposal(exit_code=code, cause=cause)
                finished = P.commit(
                    self.durable, self.owner, proposal, flush_acknowledged=True,
                )
                self.assertEqual(P.recover(finished, self.owner), outcome)

    def test_torn_hash_or_missing_sequence_fails_closed(self):
        last = self.exit_proposal().entry
        with self.assertRaisesRegex(P.JournalBlocked, "journal_chain_invalid"):
            P.recover(P.Ledger((self.durable.records[0],
                                replace(last, digest="0" * 64))), self.owner)
        with self.assertRaisesRegex(P.JournalBlocked, "journal_chain_invalid"):
            P.recover(P.Ledger((replace(self.durable.records[0],
                                        seq=2),)), self.owner)

    def test_missing_durable_intent_blocks_exit(self):
        with self.assertRaisesRegex(P.JournalBlocked, "no_durable_intent_to_reconcile"):
            P.prepare_outcome(
                self.empty, self.owner, self.nonce,
                candidate_id=self.owner.candidate_id,
            )

    def test_cli_only_reports_pure_simulation(self):
        p = subprocess.run(
            [sys.executable, "-B", str(SOURCE), "simulate"],
            capture_output=True, text=True, timeout=8, check=False,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("M1_P1E_SIMULATION=PASS_IN_MEMORY", p.stdout)
        self.assertIn("M1_P1E_REAL_PERSISTENCE=NOT_IMPLEMENTED", p.stdout)
        self.assertIn("M1_P1E_SIM_TORN_RECORD=BLOCKED", p.stdout)


if __name__ == "__main__":
    unittest.main()
