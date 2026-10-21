#!/usr/bin/env python3
"""Fresh, explicitly reauthorized 8-root recovery when both old receipts are lost.

This is NOT the original 29-target uninstall. Exactly eight hard-coded
project-only directory roots are eligible. No Docker, model, PLE swap,
shared cache or Git checkout mutation is implemented.
"""
from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "qwen38_partial_recovery_support",
    Path(__file__).with_name("partial-uninstall-recovery.py"),
)
assert SPEC is not None and SPEC.loader is not None
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)
full = support.full

SCHEMA = 1
MODE = "FRESH_EIGHT_ROOT_PARTIAL_RECOVERY"
CONFIRM = "DELETE_ONLY_EIGHT_FRESHLY_REAUTHORIZED_QWEN38_ROOTS"
RECEIPT_BASENAME = "qwen38-residual-recovery-v2.json"


class Refused(RuntimeError):
    pass


def expected_scope() -> dict[str, str]:
    # This emergency recovery is deliberately restricted to the observed DGX
    # home/repo layout. Different hosts need a separate review, not overrides.
    home = Path("/home/inlc")
    checkout = home / "Workspace/llm/qwen3.8-flash-next-dgx-spark"
    if ROOT != checkout:
        raise Refused("checkout_is_not_the_reviewed_single_dgx_checkout")
    return {
        "home": str(home), "checkout": str(checkout),
        "state": str(home / ".local/state/qwen38-spark"),
        "data": str(home / ".local/share/qwen38-spark"),
        "models": str(checkout / "models"),
        "units": "/etc/systemd/system",
        "swap": "/swap-ple.img",
        "hf": str(home / ".cache/huggingface"),
        "fstab": "/etc/fstab",
    }


def exact_targets(scope: dict[str, str]) -> list[tuple[str, Path]]:
    home, checkout = Path(scope["home"]), Path(scope["checkout"])
    entries = [
        ("project-cache", home / ".cache/flashinfer-v029"),
        ("project-cache", home / ".cache/vllm-qwen38"),
        ("project-cache", home / ".cache/vllm-qwen38-v029"),
        ("forensic", checkout / "docs/model-reports/evidence"),
        ("forensic", checkout / "scripts/benchmark/evidence"),
        ("forensic", home / "Workspace/llm/qwen38-m1-bench-results"),
        ("data-root", Path(scope["data"])),
        ("state-root", Path(scope["state"])),
    ]
    if (len(entries) != 8 or len({str(path) for _, path in entries}) != 8):
        raise Refused("invalid_reviewed_eight_root_set")
    for kind, path in entries:
        # Both whitelist and recursive no-foreign-device/no-symlink checks.
        full.scoped_file(path, kind, scope)
    return entries


def receipt_path(path: Path, scope: dict[str, str]) -> None:
    home = Path(scope["home"])
    if path != home / RECEIPT_BASENAME:
        raise Refused("unapproved_receipt_destination")
    full.require_real_path(home)
    if path.is_symlink():
        raise Refused("receipt_symlink_forbidden")


def guarded_environment(plan: dict) -> None:
    # Read-only, freshly acquired Docker, systemd, model, fstab, foreign
    # references and dedicated PLE absence checks. A partially re-created
    # project installation must be reviewed independently.
    support.missing_other_assets(plan)
    if any(Path(x["id"]).is_symlink() for x in plan["targets"]):
        raise Refused("symlink_at_reviewed_root")
    for item in plan["targets"]:
        path = Path(item["id"])
        if not path.is_dir():
            raise Refused("missing_reviewed_project_root:" + str(path))


def snapshot(scope: dict[str, str]) -> dict:
    entries = exact_targets(scope)
    targets = []
    for kind, path in entries:
        st = path.lstat()
        if not stat.S_ISDIR(st.st_mode):
            raise Refused("non_directory_root:" + str(path))
        targets.append({
            "kind": kind, "id": str(path),
            "fingerprint": {"dev": st.st_dev, "ino": st.st_ino,
                            "mode": st.st_mode},
        })
    body = {
        "schema": SCHEMA, "mode": MODE, "scope": scope,
        "targets": targets, "reason": "MISSING_BOTH_OLD_RECEIPTS",
        "original_29_target_apply": "ALREADY_PARTIAL_NEVER_RERUN",
        "excluded": ["docker", "model", "swap", "shared-cache", "checkout"],
    }
    plan = {**body, "sha256": full.digest(body)}
    support.full_scope = scope
    # Deny if the exact old model, Docker or swap infrastructure reappeared
    # or if an external Docker container uses any of these directories.
    guarded_environment(plan)
    status = support.classify_roots(targets)
    if any(state != "PRESENT_EXACT_ID" for _, state in status):
        raise Refused("residual_root_missing_or_changed_before_snapshot")
    return plan


def validate(plan: dict, sha: str) -> list[dict]:
    if (not re.fullmatch(r"[0-9a-f]{64}", sha)
            or not isinstance(plan, dict)
            or set(plan) != {
                "schema", "mode", "scope", "targets", "reason",
                "original_29_target_apply", "excluded", "sha256",
            }
            or plan.get("schema") != SCHEMA or plan.get("mode") != MODE
            or plan.get("reason") != "MISSING_BOTH_OLD_RECEIPTS"
            or plan.get("original_29_target_apply") != "ALREADY_PARTIAL_NEVER_RERUN"
            or plan.get("excluded") != [
                "docker", "model", "swap", "shared-cache", "checkout"
            ]
            or plan.get("scope") != expected_scope()
            or plan.get("sha256") != sha
            or full.digest({k: v for k, v in plan.items() if k != "sha256"}) != sha):
        raise Refused("new_residual_receipt_integrity_or_scope_invalid")

    expected = exact_targets(plan["scope"])
    observed = plan["targets"]
    if (len(observed) != len(expected) or
            [(item.get("kind"), item.get("id")) for item in observed]
            != [(kind, str(path)) for kind, path in expected]):
        raise Refused("new_residual_receipt_target_mismatch")
    for item in observed:
        fp = item.get("fingerprint")
        if (not isinstance(fp, dict) or set(fp) != {"dev", "ino", "mode"}
                or any(type(fp[k]) is not int or fp[k] < 0 for k in fp)
                or not stat.S_ISDIR(fp["mode"])):
            raise Refused("new_residual_receipt_fingerprint_invalid")
    return observed


def save_new_receipt(path: Path, plan: dict, scope: dict[str, str]) -> None:
    receipt_path(path, scope)
    if path.exists() or path.is_symlink():
        raise Refused("no_overwrite_existing_receipt")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as dest:
            json.dump(plan, dest, ensure_ascii=False, sort_keys=True,
                      indent=2)
            dest.write("\n")
            dest.flush()
            os.fsync(dest.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def get_saved(path: Path, scope: dict[str, str]) -> dict:
    receipt_path(path, scope)
    full.require_real_path(path)
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_size > 131072:
        raise Refused("receipt_not_safe_regular_file")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run(action: str, path: Path, sha: str | None, approval: str | None) -> int:
    scope = expected_scope()
    receipt_path(path, scope)
    if os.geteuid() != 0:
        raise Refused("root_required_for_nested_generated_cache_files")
    if action == "snapshot":
        if sha is not None or approval is not None:
            raise Refused("snapshot_must_not_take_prior_approval_or_sha")
    elif (not sha or (action == "audit" and approval is not None)
          or (action == "apply" and approval != CONFIRM)):
        raise Refused("explicit_sha_and_exact_approval_required")

    state = Path(scope["state"])
    lock = state / "operation.lock"
    full.require_real_path(lock)
    if lock.is_symlink() or not lock.is_file():
        raise Refused("project_operation_lock_missing")
    fd = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if action == "snapshot":
            if path.exists() or path.is_symlink():
                raise Refused("receipt_already_present")
            plan = snapshot(scope)
            save_new_receipt(path, plan, scope)
            print("NEW_RESIDUAL_RECEIPT=CREATED", flush=True)
            print("NEW_RESIDUAL_SHA256=" + plan["sha256"], flush=True)
            print("APPROVED_CANDIDATE_ROOTS=8", flush=True)
            print("HOST_DELETION=NOT_PERFORMED", flush=True)
            return 0

        plan = get_saved(path, scope)
        targets = validate(plan, sha or "")
        support.full_scope = scope
        guarded_environment(plan)
        statuses = support.classify_roots(targets)
        for t, status in statuses:
            print(f'RESIDUAL={t["kind"]}|{status}|{t["id"]}', flush=True)
        if any(status != "PRESENT_EXACT_ID" for _, status in statuses):
            raise Refused("not_all_original_eight_roots_still_present")
        print("RESIDUAL_ROOTS_EXACT=8", flush=True)
        if action == "audit":
            print("FRESH_RECOVERY_AUDIT=READ_ONLY_PASS", flush=True)
            print("HOST_DELETION=NOT_PERFORMED", flush=True)
            return 0

        # Recheck all roots/mounts immediately before the first irreversible
        # operation; do not retry after partial failure.
        for item in targets:
            print("DELETE_EXACT_RESIDUAL=" + item["id"], flush=True)
            support.delete_one(item)
        clean, remains = full.verify_removed(plan)
        if not clean:
            print("FRESH_RECOVERY_POSTCHECK=RESIDUALS_OR_INCOMPLETE", flush=True)
            for issue in remains[:40]:
                print("REMAINING=" + issue, flush=True)
            return 3
        print("FRESH_RECOVERY_POSTCHECK=PROJECT_SCOPED_EMPTY", flush=True)
        return 0
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("snapshot", "audit", "apply"))
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--sha")
    parser.add_argument("--confirm")
    args = parser.parse_args()
    return run(args.action, args.receipt, args.sha, args.confirm)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Refused, support.RecoveryBlocked, full.Blocked, OSError,
            ValueError, KeyError, TypeError) as exc:
        print("FRESH_RECOVERY=BLOCKED_OR_PARTIAL", file=sys.stderr)
        print("REASON=" + str(exc), file=sys.stderr)
        sys.exit(2)
