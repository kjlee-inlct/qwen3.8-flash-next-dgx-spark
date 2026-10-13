#!/usr/bin/env python3
"""Offline D0 receipt-chain consistency review; never grants host admission.

Checks an on-host crosscheck JSON against the exact policy/inventory bytes.
All inputs remain unauthenticated. A complete receipt can be replayed with
unchanged input: no freshness, host ownership, signature or restore proof.
No host commands, remote access, service changes or files are written.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re
import sys
from typing import Any

SOURCE = Path(__file__).with_name("disposable-d0-preflight.py")
HASH64 = re.compile(r"[0-9a-f]{64}\Z")
EXPECTED_REPORT = (
    "schema_version", "scope", "git_sha", "host_identity",
    "docker_daemon", "docker_containers", "configured_service_unit",
    "candidate_root_mounts", "independence", "d0_admission",
    "d1_d5", "live_host_e2e", "policy_sha256", "inventory_sha256",
)
EXPECTED_CONSTANTS = {
    "scope": "ON_HOST_READ_ONLY_ASSERTION_CROSSCHECK",
    "host_identity": "MATCHED_SUPPLIED_INVENTORY_NOT_ATTESTED",
    "docker_daemon": "MATCHED_SUPPLIED_INVENTORY_NOT_ATTESTED",
    "docker_containers": "NONE_REPORTED",
    "configured_service_unit": "NOT_FOUND",
    "candidate_root_mounts": "NONE_DETECTED_IN_SELECTED_ROOTS",
    "independence": "NOT_ATTESTED",
    "d0_admission": "NOT_GRANTED",
    "d1_d5": "NOT_AUTHORIZED",
    "live_host_e2e": "NOT_QUALIFIED",
}


class EvidenceRefusal(Exception):
    """Constant error codes only; do not emit host or policy secrets."""


def fail(code: str) -> None:
    raise EvidenceRefusal(code)


def parser_module() -> Any:
    spec = importlib.util.spec_from_file_location("d0_offline", SOURCE)
    if spec is None or spec.loader is None:
        fail("offline_policy_module_missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(
    policy: dict[str, Any],
    inventory: dict[str, Any],
    receipt: dict[str, Any],
    policy_hash: str,
    inventory_hash: str,
    offline: Any,
) -> None:
    # First reject mismatched policy and declared inventory without trusting
    # any unverified receipt claims.
    offline.validate(policy, inventory)
    if set(receipt) != set(EXPECTED_REPORT):
        fail("unexpected_receipt_schema")
    if type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1:
        fail("unexpected_receipt_schema_version")
    for key, expected in EXPECTED_CONSTANTS.items():
        if type(receipt[key]) is not str or receipt[key] != expected:
            fail("unexpected_receipt_claim")
    if type(receipt["git_sha"]) is not str or receipt["git_sha"] != policy["expected_sha"]:
        fail("receipt_git_sha_mismatch")
    for key, expected in (
        ("policy_sha256", policy_hash),
        ("inventory_sha256", inventory_hash),
    ):
        actual = receipt[key]
        if type(actual) is not str or HASH64.fullmatch(actual) is None:
            fail("invalid_receipt_digest")
        if actual != expected:
            fail(key + "_mismatch")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--crosscheck", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        offline = parser_module()
        policy, policy_hash = offline.read_json_with_digest(args.policy)
        inventory, inventory_hash = offline.read_json_with_digest(args.inventory)
        receipt = offline.read_json(args.crosscheck)
        verify(policy, inventory, receipt, policy_hash, inventory_hash, offline)
    except EvidenceRefusal as exc:
        print("D0_RECEIPT_REVIEW=REFUSED")
        print("D0_REASON=" + str(exc))
        print("D0_ADMISSION=NOT_GRANTED")
        return 2
    except Exception:
        # Includes PreflightRefusal from the dynamic policy import.
        # Never expose paths, IDs, host data or parser error messages.
        print("D0_RECEIPT_REVIEW=REFUSED")
        print("D0_REASON=invalid_or_incomplete_evidence")
        print("D0_ADMISSION=NOT_GRANTED")
        return 2
    print("D0_RECEIPT_REVIEW=CONSISTENT_UNTRUSTED")
    print("D0_RECEIPT_INPUT_DIGESTS=MATCH")
    print("D0_EXTERNAL_ATTESTATION=NOT_VERIFIED")
    print("D0_RECEIPT_FRESHNESS=NOT_VERIFIED")
    print("D0_ADMISSION=NOT_GRANTED")
    print("D1_D5=NOT_AUTHORIZED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
