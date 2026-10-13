#!/usr/bin/env python3
"""Offline D0 external-evidence completeness review: consistency, NOT trust.

Reviews an untrusted owner/isolation/restore manifest and hashes three
out-of-repository evidence artifacts against a validated D0 receipt chain.
No signatures, provenance, clock time, host ownership, isolation or restoration
can be authenticated by this tool. NEVER authorizes D0 or D1-D5.
No Docker/systemd/Git probes, network, model access or file writes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any

ROOT = Path(__file__).parent
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
ACTOR = re.compile(r"[a-zA-Z][a-zA-Z0-9_.-]{2,63}\Z")
MAX_ARTIFACT_BYTES = 1024 * 1024


class ExternalEvidenceRefusal(ValueError):
    """A stable refusal code without private evidence values."""


def refuse(code: str) -> None:
    raise ExternalEvidenceRefusal(code)


def load_script(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        refuse("required_reviewer_unavailable")
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def shape(value: Any, keys: tuple[str, ...], code: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != set(keys):
        refuse(code)
    return value


def exact_sha(value: Any, code: str) -> str:
    if type(value) is not str or SHA256.fullmatch(value) is None:
        refuse(code)
    return value


def actor(value: Any, code: str) -> str:
    if type(value) is not str or ACTOR.fullmatch(value) is None:
        refuse(code)
    return value


def artifact_sha256(path: Path) -> str:
    """Hash one small untrusted proof blob; never parse or display its contents.

    Open with no-follow and match inode+device so a symlink swap after lstat
    cannot redirect the evidence read. Content remains entirely unauthenticated.
    """
    try:
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or
                not 0 < before.st_size <= MAX_ARTIFACT_BYTES):
            refuse("unsafe_or_empty_external_artifact")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as file:
            info = os.fstat(file.fileno())
            if (not stat.S_ISREG(info.st_mode)
                    or (info.st_dev, info.st_ino) != (before.st_dev, before.st_ino)
                    or not 0 < info.st_size <= MAX_ARTIFACT_BYTES):
                refuse("unsafe_or_empty_external_artifact")
            blob = file.read(MAX_ARTIFACT_BYTES + 1)
        if not 0 < len(blob) <= MAX_ARTIFACT_BYTES:
            refuse("unsafe_or_empty_external_artifact")
    except ExternalEvidenceRefusal:
        raise
    except (OSError, ValueError):
        refuse("unreadable_external_artifact")
    return hashlib.sha256(blob).hexdigest()


def verify(
    manifest: dict[str, Any],
    policy: dict[str, Any],
    inventory: dict[str, Any],
    receipt: dict[str, Any],
    policy_sha: str,
    inventory_sha: str,
    receipt_sha: str,
    evidence_digests: dict[str, str],
) -> None:
    shape(manifest, (
        "schema_version", "source_sha", "policy_sha256",
        "inventory_sha256", "receipt_sha256", "owner",
        "isolation", "restore",
    ), "external_manifest_schema")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        refuse("external_manifest_version")
    if type(manifest["source_sha"]) is not str or manifest["source_sha"] != policy["expected_sha"]:
        refuse("source_sha_mismatch")
    for key, digest in (
        ("policy_sha256", policy_sha),
        ("inventory_sha256", inventory_sha),
        ("receipt_sha256", receipt_sha),
    ):
        if exact_sha(manifest[key], "invalid_manifest_digest") != digest:
            refuse(key + "_mismatch")

    owner = shape(manifest["owner"], (
        "actor", "host_machine_sha256", "docker_daemon_id",
        "disposable", "permitted_scope", "evidence_sha256",
    ), "owner_schema")
    isolation = shape(manifest["isolation"], (
        "actor", "host_machine_sha256", "docker_daemon_id",
        "no_external_users", "no_shared_volumes",
        "no_production_credentials", "evidence_sha256",
    ), "isolation_schema")
    restore = shape(manifest["restore"], (
        "actor", "host_machine_sha256", "restore_point",
        "test_data_only", "drill_result", "evidence_sha256",
    ), "restore_schema")

    actors = [actor(x["actor"], "invalid_actor_id") for x in (owner, isolation, restore)]
    if len(set(actors)) != 3:
        refuse("evidence_roles_not_distinct")
    host = inventory["host"]["machine_id_sha256"]
    daemon = inventory["docker"]["daemon_id"]
    for document in (owner, isolation, restore):
        if type(document["host_machine_sha256"]) is not str or document["host_machine_sha256"] != host:
            refuse("external_host_identity_mismatch")
    for document in (owner, isolation):
        if type(document["docker_daemon_id"]) is not str or document["docker_daemon_id"] != daemon:
            refuse("external_daemon_identity_mismatch")
    if owner["disposable"] is not True or owner["permitted_scope"] != "D0_READ_ONLY_REVIEW":
        refuse("owner_disposable_scope_not_asserted")
    if not all(isolation[field] is True for field in (
        "no_external_users", "no_shared_volumes", "no_production_credentials",
    )):
        refuse("isolation_claim_incomplete")
    if (type(restore["restore_point"]) is not str
            or restore["restore_point"] != inventory["host"]["restore_point"]
            or restore["test_data_only"] is not True
            or restore["drill_result"] != "PASS_ASSERTED"):
        refuse("restore_claim_incomplete_or_mismatched")

    proof_hashes = []
    for name, document in (
        ("owner", owner), ("isolation", isolation), ("restore", restore),
    ):
        actual = exact_sha(document["evidence_sha256"], "invalid_external_artifact_digest")
        if actual != evidence_digests[name]:
            refuse(name + "_artifact_sha256_mismatch")
        proof_hashes.append(actual)
    if len(set(proof_hashes)) != 3:
        refuse("non_distinct_external_artifacts")
    # No role identity authentication, signature, restoration or freshness check.


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "policy", "inventory", "crosscheck", "manifest",
        "owner-evidence", "isolation-evidence", "restore-evidence",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        offline = load_script(ROOT / "disposable-d0-preflight.py", "d0_offline")
        chain = load_script(ROOT / "disposable-d0-receipt-review.py", "d0_chain")
        policy, ph = offline.read_json_with_digest(args.policy)
        inventory, ih = offline.read_json_with_digest(args.inventory)
        receipt, rh = offline.read_json_with_digest(args.crosscheck)
        chain.verify(policy, inventory, receipt, ph, ih, offline)
        manifest = offline.read_json(args.manifest)
        hashes = {
            "owner": artifact_sha256(args.owner_evidence),
            "isolation": artifact_sha256(args.isolation_evidence),
            "restore": artifact_sha256(args.restore_evidence),
        }
        verify(manifest, policy, inventory, receipt, ph, ih, rh, hashes)
    except ExternalEvidenceRefusal as exc:
        print("D0_EXTERNAL_EVIDENCE_REVIEW=REFUSED")
        print("D0_REASON=" + str(exc))
        print("D0_ADMISSION=NOT_GRANTED")
        return 2
    except Exception:
        # Never disclose host identity, private artifact bytes, paths or
        # internal parser errors, including invalid policy/receipt chain.
        print("D0_EXTERNAL_EVIDENCE_REVIEW=REFUSED")
        print("D0_REASON=invalid_or_unreadable_evidence_chain")
        print("D0_ADMISSION=NOT_GRANTED")
        return 2
    print("D0_EXTERNAL_EVIDENCE_REVIEW=STRUCTURALLY_CONSISTENT_UNTRUSTED")
    print("D0_EXTERNAL_ROLES=CLAIMED_DISTINCT_NOT_AUTHENTICATED")
    print("D0_EXTERNAL_ARTIFACTS=BYTE_HASHES_MATCH")
    print("D0_OWNER_AUTHORIZATION=NOT_AUTHENTICATED")
    print("D0_DOCKER_EXCLUSIVITY=NOT_INDEPENDENTLY_VERIFIED")
    print("D0_RESTORE_EXECUTION=NOT_INDEPENDENTLY_VERIFIED")
    print("D0_EVIDENCE_FRESHNESS=NOT_VERIFIED")
    print("D0_ADMISSION=NOT_GRANTED")
    print("D1_D5=NOT_AUTHORIZED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
