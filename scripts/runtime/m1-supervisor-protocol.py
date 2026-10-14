#!/usr/bin/env python3
"""Pure P1c M1 supervisor protocol simulation; no host or model access.

This is NOT a daemon, launcher, watchdog, journal writer, PID inspector,
Docker client, systemd client, or approval mechanism for live operations.
All observations are synthetic values injected by a caller. No production
background worker exists; nothing in this module can start or stop one.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import math
import re

UNIT = "qwen38-mazinb-m1-background.service"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX32 = re.compile(r"[0-9a-f]{32}\Z")
NAME = re.compile(r"qwen38-mazinb-m1-[0-9]{14}-[0-9a-f]{8}\Z")
PHASES = frozenset({
    "CREATED", "ARMED", "RUNNING", "STOP_REQUESTED",
    "RECOVERY_REQUIRED", "STOPPED", "FAILED_STOPPED",
})


class ProtocolBlocked(ValueError):
    """Invalid or untrusted synthetic transition; no side effects."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ProtocolBlocked(reason)


@dataclass(frozen=True)
class Identity:
    """Full immutable owner binding; PID alone is NEVER sufficient."""

    candidate_name: str
    candidate_id: str
    predecessor_id: str
    owner_token: str
    supervisor_pid: int
    supervisor_start_ticks: int
    systemd_invocation_id: str
    unit: str = UNIT

    def __post_init__(self) -> None:
        require(bool(NAME.fullmatch(self.candidate_name)), "candidate_name_invalid")
        require(bool(HEX64.fullmatch(self.candidate_id)), "candidate_id_invalid")
        require(bool(HEX64.fullmatch(self.predecessor_id)), "predecessor_id_invalid")
        require(self.candidate_id != self.predecessor_id, "predecessor_alias")
        require(bool(HEX32.fullmatch(self.owner_token)), "owner_token_invalid")
        require(bool(HEX32.fullmatch(self.systemd_invocation_id)),
                "invocation_id_invalid")
        require(type(self.supervisor_pid) is int and self.supervisor_pid > 1,
                "supervisor_pid_invalid")
        require(type(self.supervisor_start_ticks) is int
                and self.supervisor_start_ticks > 0, "pid_start_ticks_invalid")
        require(self.unit == UNIT, "unit_name_mismatch")


@dataclass(frozen=True)
class Observation:
    """Injected facts; NEVER treated as actual host attestation."""

    owner: Identity
    journal_token: str
    journal_candidate_id: str
    monitor_candidate_id: str
    monitor_armed: bool
    monitor_alive: bool
    heartbeat_age_seconds: float
    supervisor_alive: bool
    docker_running: bool
    docker_exited_proven: bool
    docker_exit_code: int | None
    docker_oom_killed: bool
    benchmark_lease_free: bool
    monitor_ended_evidence: bool = False
    exact_stop_ack: bool = False
    protective_stop_marker_pinned: bool = False

    def __post_init__(self) -> None:
        for field in (
            "monitor_armed", "monitor_alive", "supervisor_alive",
            "docker_running", "docker_exited_proven", "docker_oom_killed",
            "benchmark_lease_free", "monitor_ended_evidence",
            "exact_stop_ack", "protective_stop_marker_pinned",
        ):
            require(type(getattr(self, field)) is bool, field + "_not_bool")
        require(type(self.heartbeat_age_seconds) in (int, float)
                and math.isfinite(self.heartbeat_age_seconds)
                and self.heartbeat_age_seconds >= 0,
                "invalid_heartbeat_age")


@dataclass(frozen=True)
class Session:
    owner: Identity
    phase: str = "CREATED"
    exit_code: int | None = None
    shutdown_cause: str = "NOT_OBSERVED"

    def __post_init__(self) -> None:
        require(isinstance(self.owner, Identity), "session_owner_invalid")
        require(self.phase in PHASES, "phase_invalid")


def pinned(session: Session, observed: Observation) -> None:
    """Apply to every event, including crash/reconcile after PID reuse."""
    require(isinstance(observed.owner, Identity)
            and observed.owner == session.owner, "owner_identity_drift")
    require(observed.journal_token == session.owner.owner_token,
            "journal_token_drift")
    require(observed.journal_candidate_id == session.owner.candidate_id,
            "journal_candidate_drift")
    require(observed.monitor_candidate_id == session.owner.candidate_id,
            "watchdog_candidate_drift")
    require(observed.monitor_armed, "watchdog_not_armed")


def fresh_monitor(observed: Observation) -> None:
    require(observed.monitor_alive, "watchdog_not_alive")
    require(observed.heartbeat_age_seconds <= 15, "watchdog_heartbeat_stale")


def stopped_proof(observed: Observation) -> None:
    require(not observed.docker_running and observed.docker_exited_proven,
            "candidate_not_proved_exited")
    require(not observed.monitor_alive and observed.monitor_ended_evidence,
            "monitor_end_not_proved")
    require(observed.benchmark_lease_free, "benchmark_lease_held")
    require(type(observed.docker_exit_code) is int
            and 0 <= observed.docker_exit_code <= 255, "docker_exit_code_invalid")


def advance(session: Session, event: str, observed: Observation,
            *, operator_approved: bool = False) -> Session:
    """Pure model of future gates. Does not perform the modeled actions."""
    require(isinstance(session, Session), "session_invalid")
    require(isinstance(observed, Observation), "observation_invalid")
    require(type(operator_approved) is bool, "approval_invalid")
    pinned(session, observed)

    if event == "ARM_OBSERVED":
        require(session.phase == "CREATED", "invalid_arm_phase")
        require(not observed.docker_running and observed.supervisor_alive,
                "unsafe_prestart")
        fresh_monitor(observed)
        return replace(session, phase="ARMED")

    if event == "RUNNING_OBSERVED":
        require(session.phase == "ARMED", "invalid_running_phase")
        require(observed.docker_running and observed.supervisor_alive,
                "candidate_not_supervised_running")
        fresh_monitor(observed)
        return replace(session, phase="RUNNING")

    if event == "REQUEST_STOP":
        require(session.phase == "RUNNING", "invalid_stop_phase")
        require(operator_approved, "explicit_stop_approval_missing")
        require(observed.benchmark_lease_free, "benchmark_lease_held")
        require(observed.docker_running and observed.supervisor_alive,
                "candidate_not_supervised_running")
        fresh_monitor(observed)
        return replace(session, phase="STOP_REQUESTED")

    if event == "STOP_VERIFIED":
        require(session.phase == "STOP_REQUESTED", "invalid_stop_finalize_phase")
        require(observed.exact_stop_ack, "exact_stop_not_acknowledged")
        stopped_proof(observed)
        failure = (observed.docker_oom_killed
                   or observed.docker_exit_code != 0
                   or observed.protective_stop_marker_pinned)
        return replace(session,
                       phase="FAILED_STOPPED" if failure else "STOPPED",
                       exit_code=observed.docker_exit_code,
                       shutdown_cause=("MEMORY_PROTECTION_MARKER"
                                       if observed.protective_stop_marker_pinned
                                       else "EXACT_STOP_ACK_OBSERVED"))

    if event == "SUPERVISOR_LOST":
        require(session.phase in ("ARMED", "RUNNING", "STOP_REQUESTED"),
                "invalid_supervisor_loss_phase")
        require(not observed.supervisor_alive, "supervisor_not_proved_lost")
        # No synthetic attempt to stop a possibly still-running Docker.
        return replace(session, phase="RECOVERY_REQUIRED",
                       shutdown_cause="UNDETERMINED")

    if event == "RECONCILE_STOPPED":
        require(session.phase == "RECOVERY_REQUIRED", "invalid_reconcile_phase")
        require(not observed.supervisor_alive, "supervisor_still_active")
        stopped_proof(observed)
        reason = ("MEMORY_PROTECTION_MARKER"
                  if observed.protective_stop_marker_pinned else "UNDETERMINED")
        failure = (observed.docker_oom_killed
                   or observed.docker_exit_code != 0
                   or observed.protective_stop_marker_pinned)
        return replace(session,
                       phase="FAILED_STOPPED" if failure else "STOPPED",
                       exit_code=observed.docker_exit_code,
                       shutdown_cause=reason)

    raise ProtocolBlocked("unknown_event")


def synthetic_scenario() -> None:
    """Two in-memory paths: explicit stop and lost-supervisor reconciliation."""
    owner = Identity(
        candidate_name="qwen38-mazinb-m1-20261014013811-16ced779",
        candidate_id="a" * 64, predecessor_id="b" * 64,
        owner_token="c" * 32, supervisor_pid=24680,
        supervisor_start_ticks=501, systemd_invocation_id="d" * 32,
    )
    base = Observation(
        owner=owner, journal_token=owner.owner_token,
        journal_candidate_id=owner.candidate_id,
        monitor_candidate_id=owner.candidate_id,
        monitor_armed=True, monitor_alive=True,
        heartbeat_age_seconds=1.0, supervisor_alive=True,
        docker_running=False, docker_exited_proven=False,
        docker_exit_code=None, docker_oom_killed=False,
        benchmark_lease_free=True,
    )
    armed = advance(Session(owner), "ARM_OBSERVED", base)
    running_observation = replace(base, docker_running=True)
    running = advance(armed, "RUNNING_OBSERVED", running_observation)
    stopping = advance(running, "REQUEST_STOP", running_observation,
                       operator_approved=True)
    stopped_observation = replace(
        running_observation, docker_running=False, docker_exited_proven=True,
        docker_exit_code=0, monitor_alive=False, monitor_ended_evidence=True,
        exact_stop_ack=True,
    )
    stopped = advance(stopping, "STOP_VERIFIED", stopped_observation)
    require(stopped.phase == "STOPPED"
            and stopped.shutdown_cause == "EXACT_STOP_ACK_OBSERVED",
            "synthetic_stop_failed")
    lost = advance(running, "SUPERVISOR_LOST",
                   replace(running_observation, supervisor_alive=False))
    recovered = advance(lost, "RECONCILE_STOPPED",
                        replace(stopped_observation, supervisor_alive=False,
                                exact_stop_ack=False))
    require(recovered.phase == "STOPPED"
            and recovered.shutdown_cause == "UNDETERMINED",
            "synthetic_reconciliation_failed")
    try:
        advance(running, "REQUEST_STOP", running_observation)
    except ProtocolBlocked as exc:
        require(str(exc) == "explicit_stop_approval_missing",
                "synthetic_approval_failure")
    else:
        raise ProtocolBlocked("missing_approval_was_not_blocked")
    try:
        drift = replace(owner, supervisor_start_ticks=owner.supervisor_start_ticks + 1)
        advance(running, "REQUEST_STOP",
                replace(running_observation, owner=drift), operator_approved=True)
    except ProtocolBlocked as exc:
        require(str(exc) == "owner_identity_drift",
                "synthetic_pid_reuse_failure")
    else:
        raise ProtocolBlocked("pid_reuse_was_not_blocked")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "simulate"))
    args = parser.parse_args()
    print("M1_P1C_MODE=PURE_SYNTHETIC_PROTOCOL")
    print("M1_P1C_WORKER_IMPLEMENTED=NO")
    print("M1_P1C_HOST_INSPECTION=NONE")
    print("M1_P1C_DOCKER_ACTION=NONE")
    print("M1_P1C_USER_SERVICE_MUTATION=NONE")
    print("M1_P1C_LINGER_CHANGE=NONE")
    if args.action == "plan":
        print("M1_P1C_PROTOCOL=OWNER_TOKEN_PID_START_INVOCATION_EXACT_DOCKER_WATCHDOG")
        print("M1_P1C_TRANSITIONS=ARM_OBSERVED,RUNNING_OBSERVED,REQUEST_STOP,STOP_VERIFIED,SUPERVISOR_LOST,RECONCILE_STOPPED")
        print("M1_P1C_HOST_STABILITY=NOT_QUALIFIED")
        return 0
    try:
        synthetic_scenario()
    except ProtocolBlocked as error:
        print(f"M1_P1C_SIMULATION=BLOCKED reason={error}")
        return 2
    print("M1_P1C_SIMULATION=PASS_IN_MEMORY")
    print("M1_P1C_SIM_STOP=PASS_EXPLICIT_ACK")
    print("M1_P1C_SIM_RECOVERY=PASS_UNDETERMINED")
    print("M1_P1C_SIM_UNAUTHORIZED_STOP=BLOCKED")
    print("M1_P1C_SIM_PID_REUSE=BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
