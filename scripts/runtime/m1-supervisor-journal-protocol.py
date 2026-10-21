#!/usr/bin/env python3
"""P1e PURE in-memory journal transaction simulation (NO durable file I/O).

This models a proposed journal write-ahead ordering contract. It is NOT a
persistent journal, fsync, IPC, authenticated authority, worker, or Docker
controller. Boolean commit acknowledgements are synthetic injected facts.
Never use this to authorize or restart a real M1 Docker.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import re

HEX32 = re.compile(r"[a-f0-9]{32}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
GENESIS = "0" * 64
MAX_ENTRIES = 4096


class JournalBlocked(ValueError):
    pass


def require(value: bool, reason: str) -> None:
    if not value:
        raise JournalBlocked(reason)


@dataclass(frozen=True)
class Owner:
    candidate_id: str
    predecessor_id: str
    owner_token: str

    def __post_init__(self) -> None:
        require(isinstance(self.candidate_id, str)
                and bool(HEX64.fullmatch(self.candidate_id)),
                "candidate_id_invalid")
        require(isinstance(self.predecessor_id, str)
                and bool(HEX64.fullmatch(self.predecessor_id))
                and self.predecessor_id != self.candidate_id,
                "predecessor_id_invalid")
        require(isinstance(self.owner_token, str)
                and bool(HEX32.fullmatch(self.owner_token)),
                "owner_token_invalid")


@dataclass(frozen=True)
class Entry:
    seq: int
    prev_hash: str
    owner: Owner
    nonce: str
    phase: str
    docker_exit_code: int | None
    cause: str
    digest: str

    def __post_init__(self) -> None:
        require(type(self.seq) is int and 1 <= self.seq <= MAX_ENTRIES,
                "sequence_invalid")
        require(isinstance(self.prev_hash, str)
                and bool(HEX64.fullmatch(self.prev_hash)), "prev_hash_invalid")
        require(isinstance(self.owner, Owner), "owner_invalid")
        require(isinstance(self.nonce, str)
                and bool(HEX32.fullmatch(self.nonce)), "nonce_invalid")
        require(self.phase in ("STOP_INTENT", "EXIT_PROVEN"), "phase_invalid")
        require(self.cause in ("PENDING", "EXACT_STOP_ACK",
                               "MEMORY_PROTECTION_MARKER", "UNDETERMINED"),
                "cause_invalid")
        require((self.phase == "STOP_INTENT" and self.docker_exit_code is None
                 and self.cause == "PENDING")
                or (self.phase == "EXIT_PROVEN"
                    and type(self.docker_exit_code) is int
                    and 0 <= self.docker_exit_code <= 255
                    and self.cause != "PENDING"), "outcome_invalid")
        require(isinstance(self.digest, str)
                and bool(HEX64.fullmatch(self.digest)), "digest_invalid")


def content_digest(entry: Entry) -> str:
    """Unkeyed hash is a synthetic corruption check, NOT authentication."""
    record = {
        "seq": entry.seq, "prev_hash": entry.prev_hash,
        "candidate_id": entry.owner.candidate_id,
        "predecessor_id": entry.owner.predecessor_id,
        "owner_token": entry.owner.owner_token,
        "nonce": entry.nonce, "phase": entry.phase,
        "docker_exit_code": entry.docker_exit_code, "cause": entry.cause,
    }
    return hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def make_entry(seq: int, previous: str, owner: Owner, nonce: str,
               phase: str, exit_code: int | None = None,
               cause: str = "PENDING") -> Entry:
    candidate = Entry(seq, previous, owner, nonce, phase, exit_code,
                      cause, GENESIS)
    return Entry(seq, previous, owner, nonce, phase, exit_code,
                 cause, content_digest(candidate))


@dataclass(frozen=True)
class Ledger:
    """Imaginary durable snapshot; never backed by any disk writes."""
    records: tuple[Entry, ...] = ()

    def __post_init__(self) -> None:
        require(isinstance(self.records, tuple)
                and len(self.records) <= MAX_ENTRIES, "ledger_size_invalid")


@dataclass(frozen=True)
class Prepared:
    """Uncommitted copy-on-write proposal: a crash discards this object."""
    expected_revision: int
    entry: Entry


def checked(ledger: Ledger, owner: Owner) -> None:
    require(isinstance(ledger, Ledger) and isinstance(owner, Owner),
            "ledger_or_owner_invalid")
    previous = GENESIS
    phases = []
    nonce = None
    for index, entry in enumerate(ledger.records, 1):
        require(isinstance(entry, Entry), "ledger_entry_invalid")
        require(entry.seq == index and entry.prev_hash == previous
                and entry.digest == content_digest(entry), "journal_chain_invalid")
        require(entry.owner == owner, "journal_owner_drift")
        if nonce is None:
            nonce = entry.nonce
        require(entry.nonce == nonce, "journal_nonce_drift")
        phases.append(entry.phase)
        previous = entry.digest
    require(phases in ([], ["STOP_INTENT"], ["STOP_INTENT", "EXIT_PROVEN"]),
            "journal_phase_sequence_invalid")


def prepare_intent(ledger: Ledger, owner: Owner, nonce: str,
                   *, operator_approved: bool = False,
                   admission_verified: bool = False) -> Prepared:
    """Even synthetic intent requires consent; rejected requests have no entry."""
    checked(ledger, owner)
    require(type(operator_approved) is bool
            and type(admission_verified) is bool, "approval_type_invalid")
    require(operator_approved and admission_verified,
            "stop_consent_or_admission_missing")
    require(not ledger.records, "nonce_or_intent_already_recorded")
    return Prepared(len(ledger.records),
                    make_entry(1, GENESIS, owner, nonce, "STOP_INTENT"))


def commit(ledger: Ledger, owner: Owner, proposal: Prepared,
           *, flush_acknowledged: bool = False) -> Ledger:
    """Simulate atomic compare-and-swap + fsync ACK; no real fsync occurs."""
    checked(ledger, owner)
    require(isinstance(proposal, Prepared), "proposal_invalid")
    require(type(flush_acknowledged) is bool and flush_acknowledged,
            "durable_commit_not_acknowledged")
    require(proposal.expected_revision == len(ledger.records),
            "journal_compare_and_swap_conflict")
    require(proposal.entry.seq == len(ledger.records) + 1
            and proposal.entry.prev_hash == (
                ledger.records[-1].digest if ledger.records else GENESIS)
            and proposal.entry.owner == owner
            and proposal.entry.digest == content_digest(proposal.entry),
            "prepared_record_identity_or_hash_invalid")
    next_ledger = Ledger(ledger.records + (proposal.entry,))
    checked(next_ledger, owner)
    return next_ledger


def prepare_outcome(ledger: Ledger, owner: Owner, nonce: str,
                    *, candidate_id: str, proven_exited: bool = False,
                    monitor_ended: bool = False,
                    benchmark_lease_free: bool = False,
                    docker_running: bool = True,
                    exit_code: int | None = None,
                    cause: str = "UNDETERMINED") -> Prepared:
    """Prepare exit proof record, never issue STOP or Docker inspect."""
    checked(ledger, owner)
    require(len(ledger.records) == 1
            and ledger.records[0].phase == "STOP_INTENT",
            "no_durable_intent_to_reconcile")
    require(nonce == ledger.records[0].nonce, "nonce_mismatch")
    require(candidate_id == owner.candidate_id, "candidate_identity_mismatch")
    require(type(proven_exited) is bool and proven_exited
            and type(docker_running) is bool and not docker_running,
            "docker_exit_unproven")
    require(type(monitor_ended) is bool and monitor_ended,
            "monitor_end_unproven")
    require(type(benchmark_lease_free) is bool and benchmark_lease_free,
            "benchmark_lease_held")
    require(type(exit_code) is int and 0 <= exit_code <= 255,
            "exit_code_unproven")
    require(cause in ("EXACT_STOP_ACK", "MEMORY_PROTECTION_MARKER",
                      "UNDETERMINED"), "cause_unrecognized")
    return Prepared(1, make_entry(
        2, ledger.records[0].digest, owner, nonce, "EXIT_PROVEN",
        exit_code, cause,
    ))


def recover(ledger: Ledger, owner: Owner) -> str:
    """Fail closed: a durable intent is NEVER automatically executed again."""
    checked(ledger, owner)
    if not ledger.records:
        return "NO_DURABLE_STOP_INTENT"
    if len(ledger.records) == 1:
        return "RECONCILE_REQUIRED_NO_AUTO_REPLAY"
    outcome = ledger.records[-1]
    if (outcome.docker_exit_code != 0
            or outcome.cause == "MEMORY_PROTECTION_MARKER"):
        return "EXIT_RECORDED_FAILED"
    if outcome.cause == "UNDETERMINED":
        return "EXIT_RECORDED_CAUSE_UNDETERMINED"
    return "EXIT_RECORDED_EXACT_ACK"


def simulate() -> None:
    owner = Owner("a" * 64, "b" * 64, "c" * 32)
    nonce = "d" * 32
    empty = Ledger()
    proposal = prepare_intent(
        empty, owner, nonce, operator_approved=True, admission_verified=True)
    require(recover(empty, owner) == "NO_DURABLE_STOP_INTENT",
            "uncommitted_intent_was_mistaken_as_durable")
    try:
        commit(empty, owner, proposal)
    except JournalBlocked as exc:
        require(str(exc) == "durable_commit_not_acknowledged",
                "flush_denial_failed")
    else:
        raise JournalBlocked("unacknowledged_flush_admitted")
    durable = commit(empty, owner, proposal, flush_acknowledged=True)
    require(recover(durable, owner) == "RECONCILE_REQUIRED_NO_AUTO_REPLAY",
            "in_doubt_intent_was_automatically_replayed")
    try:
        commit(durable, owner, proposal, flush_acknowledged=True)
    except JournalBlocked as exc:
        require(str(exc) == "journal_compare_and_swap_conflict",
                "replay_denial_failed")
    else:
        raise JournalBlocked("stale_intent_replayed")
    outcome = prepare_outcome(
        durable, owner, nonce, candidate_id=owner.candidate_id,
        proven_exited=True, monitor_ended=True, benchmark_lease_free=True,
        docker_running=False, exit_code=0, cause="UNDETERMINED",
    )
    require(recover(durable, owner) == "RECONCILE_REQUIRED_NO_AUTO_REPLAY",
            "staged_outcome_was_considered_durable")
    final = commit(durable, owner, outcome, flush_acknowledged=True)
    require(recover(final, owner) == "EXIT_RECORDED_CAUSE_UNDETERMINED",
            "unknown_cause_was_discarded")
    try:
        corrupt = Ledger((durable.records[0], Entry(
            2, durable.records[0].digest, owner, nonce, "EXIT_PROVEN",
            0, "UNDETERMINED", GENESIS,
        )))
        recover(corrupt, owner)
    except JournalBlocked as exc:
        require(str(exc) == "journal_chain_invalid",
                "corrupt_record_not_detected")
    else:
        raise JournalBlocked("corrupt_journal_accepted")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "simulate"))
    args = parser.parse_args()
    print("M1_P1E_MODE=PURE_IN_MEMORY_JOURNAL_MODEL")
    print("M1_P1E_REAL_PERSISTENCE=NOT_IMPLEMENTED")
    print("M1_P1E_REAL_FSYNC=NOT_PERFORMED")
    print("M1_P1E_REAL_WORKER=NOT_IMPLEMENTED")
    print("M1_P1E_HOST_IO=NONE")
    print("M1_P1E_DOCKER_ACTION=NONE")
    print("M1_P1E_SYSTEMD_ACTION=NONE")
    print("M1_P1E_LINGER_CHANGE=NONE")
    if args.action == "plan":
        print("M1_P1E_RULE=INTENT_ACK_BEFORE_ACTION")
        print("M1_P1E_RULE=NO_AUTO_REPLAY_AFTER_UNCERTAIN_SHUTDOWN")
        print("M1_P1E_RULE=EXIT_PROVEN_RECORD_REQUIRES_EXACT_ID_MONITOR_AND_LEASE")
        print("M1_P1E_SECURITY=UNKEYED_HASH_IS_NOT_AUTHENTICATION")
        return 0
    try:
        simulate()
    except JournalBlocked as error:
        print("M1_P1E_SIMULATION=BLOCKED reason=" + str(error))
        return 2
    print("M1_P1E_SIMULATION=PASS_IN_MEMORY")
    print("M1_P1E_SIM_UNACKNOWLEDGED_FLUSH=BLOCKED")
    print("M1_P1E_SIM_STALE_REPLAY=BLOCKED")
    print("M1_P1E_SIM_IN_DOUBT_RESTART=RECONCILE_REQUIRED_NO_AUTO_REPLAY")
    print("M1_P1E_SIM_TORN_RECORD=BLOCKED")
    print("M1_P1E_SIM_UNKNOWN_SHUTDOWN=UNDETERMINED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
