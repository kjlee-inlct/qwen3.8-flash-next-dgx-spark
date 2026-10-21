#!/usr/bin/env python3
"""P1d synthetic-only M1 control-envelope admission model.

Pure in-memory validation: no socket, peer credentials, cryptographic
authenticator, worker, systemd, Docker, journal, host process or time access.
Mocked UID/owner/timestamps/approval are NOT real security attestation.
This cannot be used for a live STOP request or background model operation.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import re

HEX32 = re.compile(r"[0-9a-f]{32}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
MAX_TTL_MS = 30_000
MAX_NONCES = 4096
ACTIONS = frozenset(("VIEW_STATUS", "REQUEST_STOP"))


class CommandBlocked(ValueError):
    pass


def require(value: bool, reason: str) -> None:
    if not value:
        raise CommandBlocked(reason)


@dataclass(frozen=True)
class OwnerBinding:
    candidate_id: str
    predecessor_id: str
    owner_token: str
    invocation_id: str
    supervisor_pid: int
    supervisor_start_ticks: int
    owner_uid: int

    def __post_init__(self) -> None:
        require(bool(HEX64.fullmatch(self.candidate_id)), "candidate_id_invalid")
        require(bool(HEX64.fullmatch(self.predecessor_id))
                and self.predecessor_id != self.candidate_id,
                "predecessor_id_invalid")
        require(bool(HEX32.fullmatch(self.owner_token)), "owner_token_invalid")
        require(bool(HEX32.fullmatch(self.invocation_id)), "invocation_id_invalid")
        require(type(self.supervisor_pid) is int and self.supervisor_pid > 1,
                "supervisor_pid_invalid")
        require(type(self.supervisor_start_ticks) is int
                and self.supervisor_start_ticks > 0, "supervisor_start_invalid")
        require(type(self.owner_uid) is int and self.owner_uid >= 0,
                "owner_uid_invalid")


@dataclass(frozen=True)
class Envelope:
    version: int
    action: str
    owner: OwnerBinding
    request_nonce: str
    issued_ms: int
    expires_ms: int

    def __post_init__(self) -> None:
        require(type(self.version) is int and self.version == 1,
                "protocol_version_unsupported")
        require(self.action in ACTIONS, "command_action_forbidden")
        require(isinstance(self.owner, OwnerBinding), "request_owner_invalid")
        require(bool(HEX32.fullmatch(self.request_nonce)),
                "request_nonce_invalid")
        require(type(self.issued_ms) is int and self.issued_ms >= 0,
                "issued_ms_invalid")
        require(type(self.expires_ms) is int
                and 0 < self.expires_ms - self.issued_ms <= MAX_TTL_MS,
                "command_ttl_invalid")


@dataclass(frozen=True)
class ReplayState:
    used_nonces: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        require(isinstance(self.used_nonces, frozenset)
                and len(self.used_nonces) <= MAX_NONCES,
                "nonce_state_invalid")
        require(all(isinstance(x, str) and HEX32.fullmatch(x)
                    for x in self.used_nonces), "nonce_history_invalid")


@dataclass(frozen=True)
class SyntheticReceipt:
    request_nonce: str
    command: str
    gate: str
    worker_action_performed: bool = False

    def __post_init__(self) -> None:
        require(self.gate in ("VIEW_STATUS_ADMITTED_SYNTHETIC",
                              "STOP_GATE_ADMITTED_SYNTHETIC"),
                "receipt_gate_invalid")
        require(self.worker_action_performed is False,
                "real_worker_action_forbidden")


def admit(
    envelope: Envelope,
    trusted_owner: OwnerBinding,
    history: ReplayState,
    *,
    peer_uid: int,
    now_ms: int,
    operator_approved: bool = False,
    benchmark_lease_free: bool = False,
    watchdog_fresh: bool = False,
    supervisor_verified: bool = False,
    linger_enabled: bool = False,
) -> tuple[SyntheticReceipt, ReplayState]:
    """Validate injected facts and return a NEW immutable replay state.

    This function does not implement safe concurrent durable nonce storage.
    A future real worker must atomically serialize admission, authenticate the
    caller via actual kernel credentials, persist replay state and independently
    attest the Docker ID, watchdog, journaling and peer consent.
    """
    require(isinstance(envelope, Envelope) and isinstance(trusted_owner, OwnerBinding)
            and isinstance(history, ReplayState), "invalid_input_type")
    for name, value in (
        ("operator_approved", operator_approved),
        ("benchmark_lease_free", benchmark_lease_free),
        ("watchdog_fresh", watchdog_fresh),
        ("supervisor_verified", supervisor_verified),
        ("linger_enabled", linger_enabled),
    ):
        require(type(value) is bool, name + "_not_bool")
    require(type(peer_uid) is int and peer_uid >= 0, "peer_uid_invalid")
    require(type(now_ms) is int and now_ms >= 0, "now_ms_invalid")
    require(envelope.owner == trusted_owner, "owner_binding_drift")
    require(peer_uid == trusted_owner.owner_uid, "peer_uid_mismatch")
    require(envelope.issued_ms <= now_ms <= envelope.expires_ms,
            "command_expired_or_future")
    require(envelope.request_nonce not in history.used_nonces,
            "command_nonce_replay")
    require(len(history.used_nonces) < MAX_NONCES, "nonce_history_full")

    if envelope.action == "REQUEST_STOP":
        require(operator_approved, "explicit_stop_approval_missing")
        require(linger_enabled, "persistent_user_manager_unqualified")
        require(supervisor_verified, "worker_identity_unverified")
        require(watchdog_fresh, "watchdog_stale_or_untrusted")
        require(benchmark_lease_free, "benchmark_lease_held")
        gate = "STOP_GATE_ADMITTED_SYNTHETIC"
    else:
        gate = "VIEW_STATUS_ADMITTED_SYNTHETIC"

    receipt = SyntheticReceipt(envelope.request_nonce, envelope.action, gate)
    next_state = ReplayState(history.used_nonces | {envelope.request_nonce})
    return receipt, next_state


def simulated_example() -> None:
    owner = OwnerBinding(
        candidate_id="a" * 64, predecessor_id="b" * 64,
        owner_token="c" * 32, invocation_id="d" * 32,
        supervisor_pid=24578, supervisor_start_ticks=110,
        owner_uid=1000,
    )
    status = Envelope(1, "VIEW_STATUS", owner, "e" * 32, 1000, 5000)
    receipt, state = admit(
        status, owner, ReplayState(), peer_uid=1000, now_ms=2000,
    )
    require(receipt.gate == "VIEW_STATUS_ADMITTED_SYNTHETIC",
            "view_status_simulation_failed")

    stop = Envelope(1, "REQUEST_STOP", owner, "f" * 32, 1000, 5000)
    try:
        admit(stop, owner, state, peer_uid=1000, now_ms=2000)
    except CommandBlocked as error:
        require(str(error) == "explicit_stop_approval_missing",
                "default_stop_denial_failed")
    else:
        raise CommandBlocked("unapproved_stop_admitted")

    try:
        admit(stop, owner, state, peer_uid=1000, now_ms=2000,
              operator_approved=True, supervisor_verified=True,
              watchdog_fresh=True, benchmark_lease_free=True)
    except CommandBlocked as error:
        require(str(error) == "persistent_user_manager_unqualified",
                "linger_no_gate_failed")
    else:
        raise CommandBlocked("linger_no_was_not_blocked")

    receipt, state = admit(
        stop, owner, state, peer_uid=1000, now_ms=2000,
        operator_approved=True, linger_enabled=True,
        supervisor_verified=True, watchdog_fresh=True,
        benchmark_lease_free=True,
    )
    require(receipt.gate == "STOP_GATE_ADMITTED_SYNTHETIC"
            and not receipt.worker_action_performed, "synthetic_stop_gate_failed")
    try:
        admit(stop, owner, state, peer_uid=1000, now_ms=2000,
              operator_approved=True, linger_enabled=True,
              supervisor_verified=True, watchdog_fresh=True,
              benchmark_lease_free=True)
    except CommandBlocked as error:
        require(str(error) == "command_nonce_replay", "replay_gate_failed")
    else:
        raise CommandBlocked("replayed_command_admitted")

    expired = Envelope(1, "VIEW_STATUS", owner, "1" * 32, 1000, 1500)
    try:
        admit(expired, owner, state, peer_uid=1000, now_ms=2000)
    except CommandBlocked as error:
        require(str(error) == "command_expired_or_future", "expiry_gate_failed")
    else:
        raise CommandBlocked("expired_command_admitted")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "simulate"))
    args = parser.parse_args()
    print("M1_P1D_MODE=PURE_SYNTHETIC_COMMAND_ADMISSION")
    print("M1_P1D_WORKER_IMPLEMENTED=NO")
    print("M1_P1D_HOST_INSPECTION=NONE")
    print("M1_P1D_DOCKER_ACTION=NONE")
    print("M1_P1D_USER_SERVICE_MUTATION=NONE")
    print("M1_P1D_LINGER_CHANGE=NONE")
    print("M1_P1D_REAL_IPC=NOT_IMPLEMENTED")
    if args.action == "plan":
        print("M1_P1D_VERSION=1")
        print("M1_P1D_MAX_TTL_MS=30000")
        print("M1_P1D_STOP_GATE=CONSENT,LINGER,OWNER,WATCHDOG,BENCHMARK_LEASE,REPLAY")
        print("M1_P1D_REAL_PEER_ATTESTATION=NOT_IMPLEMENTED")
        return 0
    try:
        simulated_example()
    except CommandBlocked as error:
        print("M1_P1D_SIMULATION=BLOCKED reason=" + str(error))
        return 2
    print("M1_P1D_SIMULATION=PASS_IN_MEMORY")
    print("M1_P1D_SIM_UNAPPROVED_STOP=BLOCKED")
    print("M1_P1D_SIM_LINGER_NO=BLOCKED")
    print("M1_P1D_SIM_NONCE_REPLAY=BLOCKED")
    print("M1_P1D_SIM_EXPIRED_REQUEST=BLOCKED")
    print("M1_P1D_SIM_REAL_STOP=NOT_PERFORMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
