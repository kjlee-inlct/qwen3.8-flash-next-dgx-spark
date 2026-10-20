#!/usr/bin/env python3
"""Recover only exact original project-file roots after a partially failed uninstall.

NOT a replacement for plan/apply. Never remove Docker containers, images, models,
swaps, shared cache roots or the Git checkout. Require the unchanged ORIGINAL
full-project reset receipt, scoped path identity and a typed second approval.
Both audit and apply refuse an unexpected active project runtime or mountpoint.
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
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "qwen38_recovery_full_uninstall",
    Path(__file__).with_name("full-project-uninstall.py"),
)
assert SPEC and SPEC.loader
full = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(full)

CONFIRM = "DELETE_ONLY_VERIFIED_REMAINING_QWEN38_LOCAL_ROOTS"
RESIDUAL_COUNTS = {
    "project-cache": 3, "forensic": 3, "data-root": 1, "state-root": 1,
}
# Host-wide caches and unrelated paths are deliberately absent.
REMOVE_ORDER = ("project-cache", "forensic", "data-root", "state-root")


class RecoveryBlocked(RuntimeError):
    pass


def check_scope(plan: dict, requested_sha: str) -> list[dict]:
    if not re.fullmatch(r"[0-9a-f]{64}", requested_sha):
        raise RecoveryBlocked("invalid_plan_sha")
    if plan["sha256"] != requested_sha:
        raise RecoveryBlocked("original_receipt_sha_mismatch")
    scope = plan["scope"]
    home = Path(scope["home"])
    checkout = Path(scope["checkout"])
    if (checkout != ROOT or
            checkout != home / "Workspace/llm/qwen3.8-flash-next-dgx-spark" or
            Path(scope["state"]) != home / ".local/state/qwen38-spark" or
            Path(scope["data"]) != home / ".local/share/qwen38-spark" or
            Path(scope["swap"]) != Path("/swap-ple.img")):
        raise RecoveryBlocked("unexpected_exact_project_scope")
    if len(plan.get("owner_exception", {}).get("entries", [])) != 9:
        raise RecoveryBlocked("original_owner_exception_not_bound")
    counts: dict[str, int] = {}
    for t in plan["targets"]:
        counts[t["kind"]] = counts.get(t["kind"], 0) + 1
    if any(counts.get(k) != n for k, n in RESIDUAL_COUNTS.items()):
        raise RecoveryBlocked("original_receipt_residual_target_count_drift")
    expected_total = {
        **RESIDUAL_COUNTS, "container": 8, "image": 7,
        "model": 2, "legacy-model-link": 1,
        "release-link": 2, "swap": 1,
    }
    if counts != expected_total:
        raise RecoveryBlocked("original_receipt_target_set_unexpected")
    targets = [t for t in plan["targets"] if t["kind"] in RESIDUAL_COUNTS]
    seen = set()
    for t in targets:
        key = t["kind"], t["id"]
        if key in seen:
            raise RecoveryBlocked("duplicate_original_root")
        seen.add(key)
        if (not isinstance(t.get("fingerprint"), dict) or
                set(("dev", "ino", "mode")) -
                set(t["fingerprint"])):
            raise RecoveryBlocked("original_root_fingerprint_missing")
        # This validates the ONLY accepted exact project-local paths.
        full.scoped_file(Path(t["id"]), t["kind"], scope)
    return sorted(targets, key=lambda t: (REMOVE_ORDER.index(t["kind"]), t["id"]))


def missing_other_assets(plan: dict) -> None:
    """Refuse clean-up if old Docker/models/PLE resources reappeared."""
    scope = plan["scope"]
    observed = full.inventory.gather(
        state=Path(scope["state"]), data=Path(scope["data"]),
        models=Path(scope["models"]), units=Path(scope["units"]),
        swap=Path(scope["swap"]), hf=Path(scope["hf"]),
        fstab=Path(scope["fstab"]), home=Path(scope["home"]),
        checkout=Path(scope["checkout"]),
    )
    if observed["issues"]:
        raise RecoveryBlocked("current_inventory_incomplete:" +
                              ";".join(observed["issues"][:4]))
    roots = [Path(t["id"]) for t in plan["targets"]
             if t["kind"] in RESIDUAL_COUNTS]
    for row in observed["resources"]:
        kind, status, ident = row["kind"], row["status"], row["locator"]
        if status == "ABSENT" or row["ownership"] == "EXCLUDED_SHARED":
            continue
        if kind == "container-name":
            continue  # An informational unresolved Docker name, not an ID.
        path = Path(ident)
        if (kind in ("state", "registry", "manifest", "release",
                     "swap-fstab", "forensic", "project-cache",
                     "state-root", "data-root") and
                kind != "swap-fstab" and
                any(path == root or full.within(path, root) for root in roots)):
            continue
        raise RecoveryBlocked("nonresidual_project_asset_present:" +
                              kind + ":" + ident + ":" + status)

    current_containers = {
        x.get("ID") for x in full.inventory.run_docker(
            "ps", "-a", "--no-trunc", "--format", "{{json .}}")
    }
    if current_containers.intersection({
        x["id"] for x in plan["targets"] if x["kind"] == "container"
    }):
        raise RecoveryBlocked("previously_deleted_project_container_reappeared")
    images = {
        (x.get("Repository"), x.get("Tag"))
        for x in full.inventory.run_docker(
            "image", "ls", "--no-trunc", "--format", "{{json .}}")
    }
    if images.intersection({
        tuple(x["id"].rsplit(":", 1)) for x in plan["targets"]
        if x["kind"] == "image"
    }):
        raise RecoveryBlocked("previously_deleted_project_image_reappeared")
    if (Path(scope["swap"]).exists() or Path(scope["swap"]).is_symlink()):
        raise RecoveryBlocked("dedicated_ple_swap_reappeared")
    fstab = Path(scope["fstab"])
    if "# qwen38-ple-swap" in fstab.read_text(encoding="utf-8"):
        raise RecoveryBlocked("dedicated_ple_fstab_marker_reappeared")


def mounted_paths() -> set[Path]:
    """Discover same-device bind mounts as well as separate-device mounts."""
    result = set()
    for raw in Path("/proc/self/mountinfo").read_text().splitlines():
        fields = raw.split(" - ", 1)[0].split()
        if len(fields) < 5:
            raise RecoveryBlocked("mount_table_incomplete")
        location = re.sub(
            r"\\([0-7]{3})",
            lambda m: chr(int(m.group(1), 8)),
            fields[4],
        )
        result.add(Path(location))
    return result


def classify_roots(targets: list[dict]) -> list[tuple[dict, str]]:
    mounts = mounted_paths()
    states = []
    for t in targets:
        path = Path(t["id"])
        full.require_real_path(path, must_exist=False)
        if not path.exists():
            states.append((t, "ABSENT"))
            continue
        full.scoped_file(path, t["kind"], full_scope)
        st = path.lstat()
        expected = t["fingerprint"]
        if not stat.S_ISDIR(st.st_mode):
            raise RecoveryBlocked("target_is_not_directory:" + str(path))
        if (st.st_dev, st.st_ino, st.st_mode) != (
                expected["dev"], expected["ino"], expected["mode"]):
            raise RecoveryBlocked("residual_root_identity_changed:" + str(path))
        if any(p == path or full.within(p, path) for p in mounts):
            raise RecoveryBlocked("nested_mount_inside_deletion_root:" + str(path))
        states.append((t, "PRESENT_EXACT_ID"))
    return states


def erase_directory_at(fd: int, device: int) -> None:
    """fd-relative no-follow recursive removal; never traverse a symlink."""
    for name in os.listdir(fd):
        if name in ("", ".", "..", "/", "\\"):
            raise RecoveryBlocked("invalid_directory_entry")
        st = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISDIR(st.st_mode):
            if st.st_dev != device:
                raise RecoveryBlocked("foreign_device_inside_project_root")
            child = os.open(
                name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=fd,
            )
            try:
                live = os.fstat(child)
                if (live.st_dev, live.st_ino) != (st.st_dev, st.st_ino):
                    raise RecoveryBlocked("directory_identity_changed")
                erase_directory_at(child, device)
            finally:
                os.close(child)
            confirm = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if (confirm.st_dev, confirm.st_ino) != (st.st_dev, st.st_ino):
                raise RecoveryBlocked("directory_changed_before_rmdir")
            os.rmdir(name, dir_fd=fd)
        else:
            if (not stat.S_ISLNK(st.st_mode) and st.st_dev != device):
                raise RecoveryBlocked("foreign_file_device_inside_project_root")
            os.unlink(name, dir_fd=fd)


def delete_one(t: dict) -> None:
    path = Path(t["id"])
    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        current = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        expected = t["fingerprint"]
        if (current.st_dev, current.st_ino, current.st_mode) != (
                expected["dev"], expected["ino"], expected["mode"]):
            raise RecoveryBlocked("root_changed_before_deletion:" + str(path))
        fd = os.open(
            path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
        try:
            if os.fstat(fd).st_ino != current.st_ino:
                raise RecoveryBlocked("root_replaced_after_open")
            erase_directory_at(fd, current.st_dev)
        finally:
            os.close(fd)
        check = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        if (check.st_dev, check.st_ino) != (current.st_dev, current.st_ino):
            raise RecoveryBlocked("root_changed_before_rmdir")
        os.rmdir(path.name, dir_fd=parent_fd)
    finally:
        os.close(parent_fd)


def main() -> int:
    global full_scope
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("audit", "apply"))
    parser.add_argument("--plan-file", type=Path, required=True)
    parser.add_argument("--plan-sha", required=True)
    parser.add_argument("--confirm")
    args = parser.parse_args()
    if args.action == "audit" and args.confirm is not None:
        raise RecoveryBlocked("approval_forbidden_for_audit")
    if args.action == "apply":
        if args.confirm != CONFIRM:
            raise RecoveryBlocked("typed_recovery_approval_missing")
        if os.geteuid() != 0:
            raise RecoveryBlocked("root_required_for_root_owned_cache_descendants")
    receipt = full.load_plan(args.plan_file)
    full.ensure_receipt_outside_scope(args.plan_file, receipt)
    full_scope = receipt["scope"]
    targets = check_scope(receipt, args.plan_sha)
    state = Path(full_scope["state"])
    lock = state / "operation.lock"
    full.require_real_path(lock)
    fd = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        missing_other_assets(receipt)
        statuses = classify_roots(targets)
        for item, status in statuses:
            print("RESIDUAL=" + item["kind"] + "|" + status + "|" + item["id"],
                  flush=True)
        print("ORIGINAL_PLAN_SHA256=" + args.plan_sha, flush=True)
        print("PENDING_EXACT_ROOTS=" +
              str(sum(status == "PRESENT_EXACT_ID" for _, status in statuses)),
              flush=True)
        if args.action == "audit":
            print("RECOVERY_AUDIT=READ_ONLY_COMPLETE")
            return 0
        for item, status in statuses:
            if status == "PRESENT_EXACT_ID":
                print("REMOVING_EXACT_PROJECT_ROOT=" + item["id"], flush=True)
                delete_one(item)
        clean, residuals = full.verify_removed(receipt)
        if not clean:
            print("RECOVERY_POSTCHECK=RESIDUALS_OR_INCOMPLETE")
            for problem in residuals[:40]:
                print("REMAINING=" + problem)
            return 3
        print("RECOVERY_POSTCHECK=PROJECT_SCOPED_EMPTY")
        return 0
    finally:
        os.close(fd)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RecoveryBlocked, full.Blocked, OSError, KeyError, ValueError,
            TypeError, subprocess.SubprocessError) as exc:
        print("PARTIAL_UNINSTALL_RECOVERY=STOP_OR_PARTIAL", file=sys.stderr)
        print("REASON=" + str(exc), file=sys.stderr)
        raise SystemExit(2)
