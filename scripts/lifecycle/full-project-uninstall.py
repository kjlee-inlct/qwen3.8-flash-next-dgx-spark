#!/usr/bin/env python3
"""Plan/apply exact, irreversible Qwen3.8 project reset; NEVER a generic Docker prune.

Two-person-style typed approval is required for apply. PLAN/VERIFY are
read-only. The exact saved plan is bound to an independently freshly observed
inventory and Docker identity proofs. Unknown ownership or changes fail closed.
The actual DGX destructive M2 E2E is NOT QUALIFIED.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
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
    "qwen38_full_uninstall_inventory",
    Path(__file__).with_name("uninstall-inventory.py"),
)
assert SPEC is not None and SPEC.loader is not None
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)

APPROVAL = "DELETE_ALL_QWEN38_PROJECT_ASSETS_AND_LOCAL_FORENSICS"
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
TRIGGERS = {
    "runtime-transition.env", "update-transition.env",
    "profile-switch-transition.env", "release-profile-refresh-transition.env",
    "settings-transition.phase", "runtime-adopt.env",
}
FILE_KINDS = {
    "model", "model-cache", "project-cache", "forensic", "state-root", "data-root",
}
EXPECTED_UNIT_MARKERS = {
    "qwen38-flash-next.service": b"Managed qwen38-spark runtime service",
    "qwen38-openwebui-proxy.socket": b"Managed qwen38-spark OpenWebUI proxy",
    "qwen38-openwebui-proxy.service": b"Managed qwen38-spark OpenWebUI proxy",
}
MAX_PLAN = 2 * 1024 * 1024
MAX_OWNER_EXCEPTION = 32768


class Blocked(RuntimeError):
    pass


def run(*argv: str) -> str:
    try:
        proc = subprocess.run(argv, text=True, capture_output=True,
                              timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Blocked("command_unavailable_or_timed_out:" + argv[0]) from exc
    if proc.returncode:
        # Do not leak potentially sensitive subprocess errors into receipts.
        raise Blocked("command_failed:" + "/".join(argv[:2]))
    if len(proc.stdout) > MAX_PLAN:
        raise Blocked("command_output_exceeds_bound")
    return proc.stdout


def json_command(*argv: str) -> object:
    try:
        return json.loads(run(*argv))
    except (ValueError, TypeError) as exc:
        raise Blocked("invalid_docker_inspect_json") from exc


def digest(data: dict) -> str:
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def within(child: Path, parent: Path) -> bool:
    return child != parent and parent in child.parents


def require_real_path(path: Path, *, must_exist: bool = True) -> None:
    if not path.is_absolute() or ".." in path.parts:
        raise Blocked("unsafe_path:" + str(path))
    # Never follow a symlink in any component, including a dangling link.
    for node in (path, *path.parents):
        if node == Path("/"):
            break
        if node.is_symlink():
            raise Blocked("symlink_in_resource_path:" + str(node))
    if must_exist and not path.exists():
        raise Blocked("path_disappeared:" + str(path))


def no_foreign_mounts(path: Path) -> None:
    require_real_path(path)
    if path.is_mount():
        raise Blocked("mount_point_resource:" + str(path))
    try:
        root_dev = path.lstat().st_dev
        # Avoid symlink traversal even within nominally private directories.
        for parent, dirs, files in os.walk(path, topdown=True, followlinks=False):
            for name in dirs + files:
                item = Path(parent) / name
                info = item.lstat()
                # HF snapshots legitimately contain symlinks into blobs.
                # Do not follow them; unlink them as directory entries only.
                if stat.S_ISLNK(info.st_mode):
                    continue
                if info.st_dev != root_dev or item.is_mount():
                    raise Blocked("unsafe_nested_mount:" + str(item))
    except OSError as exc:
        raise Blocked("unreadable_tree:" + str(path)) from exc


def scoped_file(path: Path, kind: str, scope: dict[str, str]) -> None:
    """All file deletion targets must be beneath an explicitly fixed root."""
    require_real_path(path)
    home = Path(scope["home"])
    checkout = Path(scope["checkout"])
    state = Path(scope["state"])
    data = Path(scope["data"])
    hf = Path(scope["hf"])
    model_roots = [Path(scope["models"]), home / "models", checkout / "models"]
    if kind == "state-root":
        if path != state or path.name != "qwen38-spark":
            raise Blocked("unsafe_project_state_root")
    elif kind == "data-root":
        if path != data or path.name != "qwen38-spark":
            raise Blocked("unsafe_project_data_root")
    elif kind == "model":
        valid = (
            (path == checkout / "model")
            or (path.name.startswith(("qwen3.8-", "qwen38-"))
                and any(within(path, root) for root in model_roots))
        )
        if not valid:
            raise Blocked("model_outside_known_scoped_roots:" + str(path))
    elif kind == "project-cache":
        dedicated = {
            home / ".cache/vllm-qwen38",
            home / ".cache/vllm-qwen38-v029",
            home / ".cache/flashinfer-v029",
        }
        if path not in dedicated:
            raise Blocked("unverified_runtime_cache:" + str(path))
    elif kind == "model-cache":
        if not (within(path, hf / "hub")
                and path.name.startswith(inventory.PROJECT_HF_PREFIXES)):
            raise Blocked("unverified_shared_hf_cache:" + str(path))
    elif kind == "forensic":
        allowed = {
            home / "Workspace/llm/qwen38-m1-bench-results",
            state / "retirement-archives",
            checkout / "docs/model-reports/evidence",
            checkout / "scripts" / "benchmark" / "evidence",
        }
        if path not in allowed:
            raise Blocked("forensic_outside_project_scope:" + str(path))
    else:
        raise Blocked("not_a_project_file_kind:" + kind)
    if path == Path("/") or path in (home, checkout, hf, home / "models"):
        raise Blocked("refusing_parent_directory_delete")
    no_foreign_mounts(path)


def legacy_model_link_identity(path: Path, scope: dict[str, str]) -> dict:
    """Only identify the exact checkout/model link; never follow it.

    A live destination must be a separately discoverable project model under
    one of the configured model roots. An orphan link may be unlinked, but an
    external live destination must not be misrepresented as fully removed.
    """
    checkout = Path(scope["checkout"])
    if path != checkout / "model":
        raise Blocked("legacy_model_link_outside_exact_checkout")
    require_real_path(checkout)
    if not path.is_symlink():
        raise Blocked("legacy_model_link_changed_type")
    try:
        st = path.lstat()
        raw = os.readlink(path)
    except OSError as exc:
        raise Blocked("legacy_model_link_unreadable") from exc
    if not raw:
        raise Blocked("legacy_model_link_empty_target")
    destination = Path(os.path.abspath(os.path.join(str(checkout), raw)))
    if destination == path:
        raise Blocked("legacy_model_link_self_reference")
    # Reject intermediate symlinks, including a nested redirected model root.
    require_real_path(destination, must_exist=False)
    if destination.exists():
        roots = {Path(scope["models"]), Path(scope["home"]) / "models",
                 checkout / "models"}
        if not (destination.is_dir()
                and destination.name.startswith(("qwen3.8-", "qwen38-"))
                and any(within(destination, root) for root in roots)):
            raise Blocked("legacy_model_link_target_outside_project_model_scope:"
                          + str(destination))
    return {
        "dev": st.st_dev, "ino": st.st_ino, "mode": st.st_mode,
        "target_text": raw, "resolved_target": str(destination),
    }


def managed_release_link_identity(path: Path, scope: dict[str, str]) -> dict:
    """Identify only managed current/previous links, without following them.

    The linked release must be lexically beneath the project's release
    directory. A missing former release is acceptable; an external or
    redirected target is not proof of a project-local complete reset.
    """
    data = Path(scope["data"])
    if path not in (data / "current", data / "previous"):
        raise Blocked("release_link_not_canonical:" + str(path))
    require_real_path(data)
    if not path.is_symlink():
        raise Blocked("release_link_changed_type:" + str(path))
    try:
        st = path.lstat()
        raw = os.readlink(path)
    except OSError as exc:
        raise Blocked("release_link_unreadable:" + str(path)) from exc
    if not raw:
        raise Blocked("release_link_empty_target:" + str(path))
    dest = Path(os.path.abspath(os.path.join(str(data), raw)))
    if not within(dest, data / "releases"):
        raise Blocked("release_link_points_outside_releases:" + str(path))
    require_real_path(dest, must_exist=False)
    return {
        "dev": st.st_dev, "ino": st.st_ino, "mode": st.st_mode,
        "target_text": raw, "resolved_target": str(dest),
    }


def docker_identity(cid: str) -> dict:
    if not inventory.DOCKER_ID.fullmatch(cid):
        raise Blocked("docker_id_not_full_sha")
    raw = json_command("docker", "inspect", cid)
    if not isinstance(raw, list) or len(raw) != 1:
        raise Blocked("docker_container_inspect_cardinality")
    obj = raw[0]
    if not isinstance(obj, dict) or obj.get("Id") != cid:
        raise Blocked("docker_container_identity_mismatch")
    name = obj.get("Name")
    cfg = obj.get("Config") or {}
    labels = cfg.get("Labels") or {}
    state = obj.get("State") or {}
    mounts = obj.get("Mounts") or []
    image_id = obj.get("Image")
    if (not isinstance(name, str) or not name.startswith("/")
            or not isinstance(labels, dict)
            or not isinstance(state, dict)
            or not isinstance(mounts, list)
            or not isinstance(image_id, str)):
        raise Blocked("docker_container_inspect_incomplete")
    # An experiment needs a project-specific label, not merely a suggestive name.
    if name != "/qwen38-flash-next":
        if not name.startswith(("/qwen38-", "/qwen3.8-")):
            raise Blocked("nonproject_container")
        if not any(isinstance(k, str) and k.startswith("qwen38.")
                   for k in labels):
            raise Blocked("project_container_missing_ownership_label")
    else:
        # Managed legacy containers may predate project labels. In that case
        # require BOTH the exact reserved name and a /model project bind mount.
        sources = [
            mount.get("Source") for mount in mounts
            if isinstance(mount, dict) and mount.get("Destination") == "/model"
        ]
        if not any(isinstance(s, str) and
                   Path(s).name.startswith(("qwen3.8-", "qwen38-"))
                   for s in sources):
            raise Blocked("canonical_container_missing_project_model_mount")
        if any(isinstance(k, str) and k.startswith("foreign.") for k in labels):
            raise Blocked("canonical_container_foreign_label_conflict")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise Blocked("container_missing_exact_image_id")
    # Retain all relevant identities for drift detection, not arbitrary Docker output.
    return {
        "id": cid, "name": name, "labels": labels,
        "image_id": image_id, "mounts": mounts,
        "running": state.get("Running") is True,
        "status": state.get("Status"),
    }


def verify_legacy_canonical_model_mount(container: dict, scope: dict[str, str],
                                        model_rows: list[dict]) -> None:
    """The unlabeled managed predecessor requires exact manifest-bound /model.

    A suggestively named foreign path is not enough to authorize deletion
    of the reserved-name unlabeled Docker container.
    """
    if container["name"] != "/qwen38-flash-next":
        return
    manifest_path = Path(scope["state"]) / "install.env"
    require_real_path(manifest_path)
    try:
        manifest = inventory.parse_install(manifest_path, "install-uninstall")
    except (ValueError, OSError) as exc:
        raise Blocked("canonical_container_manifest_unverifiable") from exc
    expected = manifest["MODEL_DIR"]
    if not isinstance(expected, str) or not expected.startswith("/"):
        raise Blocked("canonical_container_manifest_model_invalid")
    path = Path(expected)
    if not any(row["kind"] == "model" and row["locator"] == expected
               and row["status"] == "PRESENT" for row in model_rows):
        raise Blocked("canonical_container_model_not_in_inventory")
    mounts = [m for m in container["mounts"]
              if isinstance(m, dict) and m.get("Destination") == "/model"]
    if (len(mounts) != 1
            or mounts[0].get("Type") != "bind"
            or mounts[0].get("RW") is not False
            or mounts[0].get("Source") != expected):
        raise Blocked("canonical_container_manifest_model_mount_mismatch")
    require_real_path(path)


def image_identity(tag: str) -> dict:
    raw = json_command("docker", "image", "inspect", tag)
    if not isinstance(raw, list) or len(raw) != 1 or not isinstance(raw[0], dict):
        raise Blocked("image_inspect_cardinality")
    ident = raw[0].get("Id")
    if not isinstance(ident, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", ident):
        raise Blocked("invalid_exact_image_id")
    return {"tag": tag, "id": ident}


def volume_identity(name: str) -> dict:
    raw = json_command("docker", "volume", "inspect", name)
    if not isinstance(raw, list) or len(raw) != 1 or not isinstance(raw[0], dict):
        raise Blocked("volume_inspect_cardinality")
    obj = raw[0]
    if obj.get("Name") != name or not isinstance(obj.get("Labels") or {}, dict):
        raise Blocked("volume_identity_mismatch")
    labels = obj.get("Labels") or {}
    if not any(k.startswith("qwen38.") for k in labels):
        raise Blocked("volume_missing_project_ownership_label:" + name)
    return {"name": name, "labels": labels, "driver": obj.get("Driver")}


def ensure_no_live_transitions(scope: dict[str, str]) -> None:
    state = Path(scope["state"])
    for marker in TRIGGERS:
        path = state / marker
        if path.exists() or path.is_symlink():
            raise Blocked("active_or_stale_transition:" + marker)
    # Dangling transaction artifacts and resumed staged manifest files.
    if state.exists():
        for child in state.iterdir():
            if child.name.startswith((".uninstall-preflight.", "install.env.profile-switch-",
                                      "install.env.release-profile-refresh-",
                                      "install.env.settings-")):
                raise Blocked("stale_transition_artifact:" + child.name)


def check_units(scope: dict[str, str], targets: list[dict]) -> None:
    unit_dir = Path(scope["units"])
    for name, marker in EXPECTED_UNIT_MARKERS.items():
        path = unit_dir / name
        if not path.exists() and not path.is_symlink():
            continue
        require_real_path(path)
        if not path.is_file():
            raise Blocked("unmanaged_systemd_path:" + str(path))
        with path.open("rb") as handle:
            if marker not in handle.read(8192):
                raise Blocked("systemd_not_provably_project_managed:" + name)
        targets.append({"kind": "systemd", "id": name,
                        "fingerprint": hashlib.sha256(path.read_bytes()).hexdigest()})


def inspect_swap(scope: dict[str, str], rows: list[dict], targets: list[dict]) -> None:
    path = Path(scope["swap"])
    row = next((r for r in rows if r["kind"] == "swap"), None)
    fstab = next((r for r in rows if r["kind"] == "swap-fstab"), None)
    if row is None or fstab is None:
        raise Blocked("swap_or_fstab_inventory_incomplete")
    if row["status"] == "ABSENT" and fstab["status"] == "ABSENT":
        return
    if row["ownership"] != "INSTALLER_OWNED":
        raise Blocked("dedicated_swap_ownership_not_confirmed")
    require_real_path(path, must_exist=row["status"] == "PRESENT")
    if path.name != "swap-ple.img":
        raise Blocked("swap_must_be_dedicated_ple_path")
    # Manage-swap helper checks marker and disables the exact swap path.
    targets.append({"kind": "swap", "id": str(path),
                    "status": row["status"], "fstab": fstab["status"]})


def inspect_image_references(containers: list[dict], images: list[dict],
                             volumes: list[dict] | None = None,
                             files: list[dict] | None = None) -> None:
    """Refuse an image that any external container references, even when exited."""
    raw = inventory.run_docker("ps", "-a", "--no-trunc", "--format", "{{json .}}")
    actual_ids = {obj.get("ID") for obj in raw}
    planned_ids = {x["id"] for x in containers}
    volume_names = {x["id"] for x in (volumes or [])}
    file_roots = [Path(x["id"]) for x in (files or [])]
    if len(raw) != len(actual_ids):
        raise Blocked("duplicate_or_missing_docker_ids")
    for info in raw:
        cid = info.get("ID")
        if not isinstance(cid, str) or not inventory.DOCKER_ID.fullmatch(cid):
            raise Blocked("unverifiable_external_container_id")
        if cid not in planned_ids:
            external = json_command("docker", "inspect", cid)
            if not isinstance(external, list) or len(external) != 1:
                raise Blocked("external_container_inspect_failed")
            if external[0].get("Id") != cid:
                raise Blocked("external_container_identity_changed")
            eid = external[0].get("Image")
            if eid in {x["fingerprint"]["id"] for x in images}:
                raise Blocked("candidate_image_used_by_external_container")
            for mount in (external[0].get("Mounts") or []):
                if not isinstance(mount, dict):
                    raise Blocked("external_container_mount_invalid")
                if mount.get("Name") in volume_names:
                    raise Blocked("candidate_volume_used_by_external_container")
                source = mount.get("Source")
                if isinstance(source, str) and source.startswith("/"):
                    candidate = Path(source)
                    if any(candidate == root or within(candidate, root)
                           or within(root, candidate) for root in file_roots):
                        raise Blocked("project_file_mount_used_by_external_container")
    if actual_ids & planned_ids != planned_ids:
        raise Blocked("planned_container_disappeared")


def load_owner_exception(path: Path | None, inventory_path: Path | None,
                         scope: dict[str, str]) -> tuple[dict | None, dict | None]:
    """A SHA-pinned, opt-in exception; never edits registry or manifest ownership."""
    if path is None and inventory_path is None:
        return None, None
    if path is None or inventory_path is None:
        raise Blocked("owner_exception_requires_both_files")
    for item, limit in ((path, MAX_OWNER_EXCEPTION), (inventory_path, MAX_PLAN)):
        require_real_path(item)
        if not item.is_file() or item.stat().st_size > limit:
            raise Blocked("owner_exception_input_invalid")
        if any(item == Path(scope[k]) or within(item, Path(scope[k]))
               for k in ("state", "data", "models", "checkout", "hf")):
            raise Blocked("owner_exception_inside_deletion_scope")
    try:
        owner_bytes = path.read_bytes()
        inventory_bytes = inventory_path.read_bytes()
        owner = json.loads(owner_bytes)
        baseline = json.loads(inventory_bytes)
    except (ValueError, TypeError, OSError) as exc:
        raise Blocked("owner_exception_file_invalid_json") from exc
    if (not isinstance(owner, dict)
            or set(owner) != {"schema", "inventory_sha256", "entries"}
            or type(owner["schema"]) is not int or owner["schema"] != 1
            or not isinstance(owner["inventory_sha256"], str)
            or not DIGEST.fullmatch(owner["inventory_sha256"])
            or owner["inventory_sha256"] != hashlib.sha256(inventory_bytes).hexdigest()):
        raise Blocked("owner_exception_inventory_sha_mismatch")
    if (not isinstance(baseline, dict)
            or baseline.get("schema") != 1
            or baseline.get("mode") != "READ_ONLY_PROJECT_SCOPE"
            or baseline.get("scope") != scope
            or baseline.get("issues") != []
            or not isinstance(baseline.get("resources"), list)):
        raise Blocked("owner_exception_inventory_scope_or_issues")
    entries = owner["entries"]
    if not isinstance(entries, list) or not (1 <= len(entries) <= 64):
        raise Blocked("owner_exception_entries_invalid")
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"kind", "locator", "fingerprint"}:
            raise Blocked("owner_exception_entry_invalid")
        kind, ident, fingerprint = entry["kind"], entry["locator"], entry["fingerprint"]
        if (kind not in ("model", "image") or not isinstance(ident, str)
                or not ident or not isinstance(fingerprint, str)
                or (kind == "model" and not DIGEST.fullmatch(fingerprint))
                or (kind == "image" and not re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint))):
            raise Blocked("owner_exception_identity_invalid")
        if (kind, ident) in seen:
            raise Blocked("owner_exception_duplicate")
        seen.add((kind, ident))
    receipt = {
        "schema": 1, "inventory_sha256": owner["inventory_sha256"],
        "file_sha256": hashlib.sha256(owner_bytes).hexdigest(),
        "entries": sorted(entries, key=lambda e: (e["kind"], e["locator"])),
    }
    return receipt, baseline


def verify_owner_exception_identity(kind: str, ident: str, pinned: str,
                                    image: dict | None = None) -> None:
    if kind == "image":
        if image is None or image["id"] != pinned:
            raise Blocked("owner_exception_image_identity_changed:" + ident)
        return
    marker = Path(ident) / ".qwen38-model-manifest.json"
    if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > 1024 * 1024:
        raise Blocked("owner_exception_model_marker_unverifiable:" + ident)
    if hashlib.sha256(marker.read_bytes()).hexdigest() != pinned:
        raise Blocked("owner_exception_model_marker_changed:" + ident)


def check_recorded_asset_provenance(kind: str, ident: str,
                                    record: dict | None,
                                    identity: dict | None = None,
                                    *, allow_unowned: bool = False) -> None:
    """Honor immutable registry fingerprints when an asset is recorded there.

    The active manifest may be the sole provenance for an older installation;
    never silently override an existing registry entry with weaker evidence.
    """
    if record is None:
        return
    if not record["owned"] and not allow_unowned:
        raise Blocked("registry_manifest_ownership_conflict:" + kind + ":" + ident)
    if record["state"] != "ready" or not record["fingerprint"]:
        raise Blocked("registered_asset_not_fingerprint_ready:" + kind + ":" + ident)
    if kind == "image":
        if identity is None or identity["id"] != record["fingerprint"]:
            raise Blocked("registered_image_id_drift:" + ident)
    elif kind == "model":
        path = Path(ident)
        marker = next(
            (candidate for candidate in (
                path / ".qwen38-model-manifest.json",
                path / ".qwen38-hybrid-manifest.json",
            ) if candidate.is_file() and not candidate.is_symlink()),
            None,
        )
        if marker is None:
            raise Blocked("registered_model_manifest_missing:" + ident)
        sha = hashlib.sha256()
        try:
            with marker.open("rb") as src:
                for chunk in iter(lambda: src.read(1024 * 1024), b""):
                    sha.update(chunk)
        except OSError as exc:
            raise Blocked("registered_model_manifest_unreadable:" + ident) from exc
        if sha.hexdigest() != record["fingerprint"]:
            raise Blocked("registered_model_manifest_drift:" + ident)


def scan(scope: dict[str, str], owner_exception: dict | None = None,
         baseline: dict | None = None) -> dict:
    observed = inventory.gather(
        state=Path(scope["state"]), data=Path(scope["data"]),
        models=Path(scope["models"]), units=Path(scope["units"]),
        swap=Path(scope["swap"]), hf=Path(scope["hf"]),
        fstab=Path(scope["fstab"]), home=Path(scope["home"]),
        checkout=Path(scope["checkout"]),
    )
    if observed["issues"]:
        raise Blocked("inventory_incomplete:" + ";".join(observed["issues"][:5]))
    if owner_exception is not None:
        if (baseline is None or observed["scope"] != baseline["scope"]
                or observed["resources"] != baseline["resources"]):
            raise Blocked("owner_exception_inventory_drift")
        try:
            audit = inventory.reference_audit(observed)
        except (OSError, ValueError, RuntimeError) as exc:
            raise Blocked("owner_exception_reference_audit_incomplete") from exc
        if audit["result"] != "NO_OBSERVED_CONFLICTS":
            raise Blocked("owner_exception_references_not_clear:" + audit["result"])
        try:
            model_audit = inventory.model_provenance_audit(observed)
        except (OSError, ValueError, RuntimeError, inventory.RegistryError) as exc:
            raise Blocked("owner_exception_model_provenance_incomplete") from exc
        if model_audit["result"] != "CONSISTENT_METADATA_NOT_OWNERSHIP":
            raise Blocked("owner_exception_model_metadata_not_consistent:" +
                          model_audit["result"])
    ensure_no_live_transitions(scope)
    try:
        registry = inventory.load_registry(
            Path(scope["state"]) / "asset-ownership.json")
    except (OSError, ValueError, inventory.RegistryError) as exc:
        raise Blocked("ownership_registry_changed_during_scan") from exc
    recorded = {(item["kind"], item["locator"]): item
                for item in registry["assets"]}
    targets: list[dict] = []
    rows = observed["resources"]
    # Report several unresolved candidates at once instead of repeatedly
    # blocking on only the first similarly named, possibly foreign asset.
    # This is still a read-only inspection and grants no deletion authority.
    unverified = [
        item["kind"] + ":" + item["locator"]
        for item in rows
        if (item["kind"] in ("model", "image", "model-cache")
            and item["status"] == "PRESENT"
            and item["ownership"] != "INSTALLER_OWNED")
    ]
    approved: dict[tuple[str, str], str] = {}
    if owner_exception is not None:
        approved = {(e["kind"], e["locator"]): e["fingerprint"]
                    for e in owner_exception["entries"]}
        observed_unowned = {(r["kind"], r["locator"]) for r in rows
                            if r["kind"] in ("model", "image", "model-cache")
                            and r["status"] == "PRESENT"
                            and r["ownership"] != "INSTALLER_OWNED"}
        if set(approved) != observed_unowned:
            raise Blocked("owner_exception_extra_or_missing_unverified_target")
    if unverified and owner_exception is None:
        overflow = len(unverified) - 12
        raise Blocked("candidate_ownership_not_proven:" +
                      ";".join(unverified[:12]) +
                      (";additional_unverified=" + str(overflow)
                       if overflow > 0 else ""))
    for item in rows:
        kind, ident, status = item["kind"], item["locator"], item["status"]
        if (kind == "model" and ident == str(Path(scope["checkout"]) / "model")
                and status == "UNSAFE_SYMLINK"):
            targets.append({
                "kind": "legacy-model-link", "id": ident,
                "fingerprint": legacy_model_link_identity(Path(ident), scope),
            })
            continue
        if kind == "release" and status == "UNSAFE_SYMLINK" and ident in (
                str(Path(scope["data"]) / "current"),
                str(Path(scope["data"]) / "previous")):
            targets.append({
                "kind": "release-link", "id": ident,
                "fingerprint": managed_release_link_identity(Path(ident), scope),
            })
            continue
        if status == "ABSENT" or kind in ("container-name", "hf-cache", "shared-runtime-cache"):
            continue
        if status != "PRESENT":
            raise Blocked("resource_status_not_safely_present:" + kind + ":" + ident + ":" + status)
        # A matching name or project-like cache prefix is discovery evidence,
        # never positive ownership proof. Require manifest/registry attribution
        # before even inspecting an exact ID for a destructive receipt.
        # A project HF cache has no positive attribution in schema 1 and must
        # remain blocked until separate provenance support is implemented.
        if (kind in ("model", "image", "model-cache")
                and item["ownership"] != "INSTALLER_OWNED"
                and (kind, ident) not in approved):
            raise Blocked("candidate_ownership_not_proven:" + kind + ":" + ident
                          + ":ownership=" + item["ownership"])
        if kind in FILE_KINDS:
            path = Path(ident)
            # Nested state/data entries are removed through their exact roots.
            if kind == "forensic" and within(path, Path(scope["state"])):
                continue
            if kind in ("model", "model-cache", "project-cache", "forensic", "state-root", "data-root"):
                scoped_file(path, kind, scope)
                if kind == "model":
                    pinned = approved.get((kind, ident))
                    if pinned is not None:
                        verify_owner_exception_identity(kind, ident, pinned)
                    check_recorded_asset_provenance(
                        kind, ident, recorded.get((kind, ident)),
                        allow_unowned=pinned is not None)
                st = path.lstat()
                targets.append({"kind": kind, "id": ident,
                                "fingerprint": {"dev": st.st_dev, "ino": st.st_ino,
                                                "mode": st.st_mode}})
        elif kind == "container":
            identity = docker_identity(ident)
            verify_legacy_canonical_model_mount(identity, scope, rows)
            targets.append({"kind": kind, "id": ident,
                            "fingerprint": identity})
        elif kind == "image":
            # Inventory candidates can be listed without installer ownership.
            # Exact tags and a consistent image ID are mandatory regardless.
            identity = image_identity(ident)
            pinned = approved.get((kind, ident))
            if pinned is not None:
                verify_owner_exception_identity(kind, ident, pinned, identity)
            check_recorded_asset_provenance(
                kind, ident, recorded.get((kind, ident)), identity,
                allow_unowned=pinned is not None)
            targets.append({"kind": kind, "id": ident,
                            "fingerprint": identity})
        elif kind == "volume":
            targets.append({"kind": kind, "id": ident,
                            "fingerprint": volume_identity(ident)})
        elif kind in ("systemd", "unit-runtime", "swap", "swap-fstab",
                      "state", "release", "manifest", "registry"):
            continue  # validated through exact units, swap and project roots
        else:
            raise Blocked("unhandled_project_resource:" + kind)
    # A live legacy link must lead to a model already included in this exact
    # plan. Removing only the link while leaving live project weights behind
    # would make "complete" uninstall a false claim.
    model_roots = [Path(x["id"]) for x in targets if x["kind"] == "model"]
    for item in targets:
        if item["kind"] == "legacy-model-link":
            destination = Path(item["fingerprint"]["resolved_target"])
            if destination.exists() and not any(
                destination == model or within(destination, model)
                for model in model_roots
            ):
                raise Blocked("legacy_model_link_target_not_selected_as_model:"
                              + str(destination))
    check_units(scope, targets)
    inspect_swap(scope, rows, targets)
    containers = [x for x in targets if x["kind"] == "container"]
    images = [x for x in targets if x["kind"] == "image"]
    inspect_image_references(
        containers, images,
        [x for x in targets if x["kind"] == "volume"],
        [x for x in targets if x["kind"] in FILE_KINDS
         or x["kind"] == "legacy-model-link"],
    )
    # Files that are shared/externally mounted or foreign are never targets.
    roots = [x for x in targets if x["kind"] in ("state-root", "data-root")]
    if len(roots) != 2:
        raise Blocked("both_project_state_and_data_roots_required_for_full_reset")
    # Report any unexpected pending systemd unit without verified managed file.
    unit_ids = {x["id"] for x in targets if x["kind"] == "systemd"}
    for row in rows:
        if row["kind"] == "unit-runtime" and row["status"] == "PRESENT":
            if row["locator"] not in unit_ids:
                raise Blocked("runtime_unit_without_owned_file:" + row["locator"])
    targets.sort(key=lambda x: (x["kind"], x["id"]))
    # Scope and fingerprints jointly commit to precisely what will be changed.
    body = {"schema": 1, "mode": "EXACT_PROJECT_RESET",
            "scope": scope, "targets": targets}
    if owner_exception is not None:
        body["owner_exception"] = owner_exception
    return {**body, "sha256": digest(body)}


def scope_from_args(args: argparse.Namespace) -> dict[str, str]:
    home = args.home.resolve(strict=False)
    checkout = args.checkout.resolve(strict=False)
    roots = {
        "home": home, "checkout": checkout,
        "state": args.state_home.resolve(strict=False) / "qwen38-spark",
        "data": args.data_home.resolve(strict=False) / "qwen38-spark",
        "models": args.model_root.resolve(strict=False),
        "hf": args.hf_home.resolve(strict=False),
        "units": args.unit_dir.resolve(strict=False),
        "fstab": args.fstab.resolve(strict=False),
        "swap": args.swap.resolve(strict=False),
    }
    if (roots["state"].name != "qwen38-spark" or
            roots["data"].name != "qwen38-spark"):
        raise Blocked("unsafe_project_state_or_data_dir")
    if home == Path("/") or checkout == Path("/"):
        raise Blocked("unsafe_home_or_checkout")
    return {k: str(v) for k, v in roots.items()}



def compare_receipts(saved: dict, current: dict) -> list[dict[str, object]]:
    """Bounded, value-free explanation of exact-identity plan drift.

    Never print full Docker inspect values, registry contents or model bytes.
    This function does not alter permissions or relax any preflight.
    """
    changes: list[dict[str, object]] = []
    for key in ("schema", "mode", "scope", "owner_exception"):
        if saved.get(key) != current.get(key):
            changes.append({"change": "plan_field_changed", "field": key})

    def indexed(plan: dict) -> dict[tuple[str, str], dict]:
        entries = {}
        for target in plan["targets"]:
            key = target["kind"], target["id"]
            if key in entries:
                raise Blocked("duplicate_target_in_comparison")
            entries[key] = target
        return entries

    old = indexed(saved)
    fresh = indexed(current)
    for kind, ident in sorted(old.keys() | fresh.keys()):
        key = kind, ident
        if key not in old:
            changes.append({"change": "target_appeared", "kind": kind, "id": ident})
            continue
        if key not in fresh:
            changes.append({"change": "target_disappeared", "kind": kind, "id": ident})
            continue
        if old[key] == fresh[key]:
            continue
        old_target, new_target = old[key], fresh[key]
        fields = []
        for field in sorted(set(old_target) | set(new_target)):
            left, right = old_target.get(field), new_target.get(field)
            if left == right:
                continue
            if isinstance(left, dict) and isinstance(right, dict):
                fields.extend(field + "." + subfield for subfield in
                              sorted(set(left) | set(right))
                              if left.get(subfield) != right.get(subfield))
            else:
                fields.append(field)
        changes.append({"change": "target_identity_changed",
                        "kind": kind, "id": ident, "fields": fields})
    if saved.get("sha256") != current.get("sha256") and not changes:
        changes.append({"change": "receipt_digest_only_changed"})
    return changes


def verify_plan(data: object) -> dict:
    required = {"schema", "mode", "scope", "targets", "sha256"}
    if not isinstance(data, dict) or set(data) not in (required, required | {"owner_exception"}):
        raise Blocked("invalid_saved_plan")
    if data["schema"] != 1 or data["mode"] != "EXACT_PROJECT_RESET":
        raise Blocked("unsupported_plan_schema")
    if not isinstance(data["scope"], dict) or not isinstance(data["targets"], list):
        raise Blocked("invalid_plan_structure")
    actual = digest({k: v for k, v in data.items() if k != "sha256"})
    if actual != data["sha256"] or not DIGEST.fullmatch(actual):
        raise Blocked("saved_plan_integrity_failure")
    return data


def load_plan(path: Path) -> dict:
    require_real_path(path)
    if not path.is_file() or path.stat().st_size > MAX_PLAN:
        raise Blocked("unsafe_or_oversized_plan_file")
    try:
        return verify_plan(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, TypeError) as exc:
        raise Blocked("invalid_plan_json") from exc


def ensure_receipt_outside_scope(plan_path: Path, plan: dict) -> None:
    for root in (Path(plan["scope"][name]) for name in
                 ("state", "data", "models", "hf", "checkout")):
        if plan_path == root or within(plan_path, root):
            raise Blocked("plan_receipt_inside_possible_deletion_scope")


def remove_tree(path: Path, kind: str, scope: dict[str, str]) -> None:
    scoped_file(path, kind, scope)  # revalidate before every actual deletion
    # Avoid recursive shell commands and never follow a symlink across mounts.
    if path.is_dir():
        for parent, dirs, files in os.walk(path, topdown=False, followlinks=False):
            for item in files:
                child = Path(parent) / item
                if not child.is_symlink():
                    require_real_path(child)
                child.unlink()
            for item in dirs:
                child = Path(parent) / item
                if child.is_symlink():
                    child.unlink()  # no traversal outside the subtree
                else:
                    require_real_path(child)
                    child.rmdir()
        path.rmdir()
    else:
        path.unlink()


def execute(plan: dict) -> None:
    """Fail-closed staged deletion. A partial failure requires operator review."""
    scope = plan["scope"]
    targets = plan["targets"]
    checkout = Path(scope["checkout"])
    approved = {(e["kind"], e["locator"]): e["fingerprint"]
                for e in plan.get("owner_exception", {}).get("entries", [])}
    units = {x["id"] for x in targets if x["kind"] == "systemd"}
    # Use existing ownership-marker guarded systemd helpers.
    if "qwen38-flash-next.service" in units:
        # The service helper enforces the *same* project operation.lock.
        # Explicitly inherit this Python process's already-held lock through
        # the sudo environment, exactly as managed uninstall.sh does.
        lock_file = str(Path(scope["state"]) / "operation.lock")
        run(
            "sudo", "env",
            "QWEN38_STATE_HOME=" + str(Path(scope["state"]).parent),
            "QWEN38_OPERATION_LOCK_HELD=1",
            "QWEN38_OPERATION_LOCK_FILE=" + lock_file,
            "QWEN38_OPERATION_LOCK_OWNER_PID=" + str(os.getpid()),
            str(checkout / "scripts/manage-service.sh"), "remove", "--yes",
        )
    if any(x.startswith("qwen38-openwebui-proxy.") for x in units):
        run("sudo", str(checkout / "scripts/manage-proxy.sh"), "remove", "--yes")
    for item in targets:
        if item["kind"] == "container":
            current = docker_identity(item["id"])
            stable = ("id", "name", "labels", "image_id", "mounts")
            if any(current[key] != item["fingerprint"][key] for key in stable):
                raise Blocked("container_identity_changed_during_apply")
            # Runtime status may transition to stopped when managed service
            # removal succeeds; never treat that alone as ID/provenance drift.
            # This is the only Docker deletion target: the verified full ID.
            run("docker", "rm", "-f", item["id"])
    # Refuse image removal until all foreign references were rechecked.
    # Exact owner exceptions get an additional full Docker image/volume/alias
    # pass after project containers have actually been removed.
    if approved:
        current = inventory.gather(
            state=Path(scope["state"]), data=Path(scope["data"]),
            models=Path(scope["models"]), units=Path(scope["units"]),
            swap=Path(scope["swap"]), hf=Path(scope["hf"]),
            fstab=Path(scope["fstab"]), home=Path(scope["home"]),
            checkout=Path(scope["checkout"]),
        )
        if current["issues"]:
            raise Blocked("owner_exception_midapply_inventory_incomplete")
        try:
            extra_audit = inventory.reference_audit(current)
        except (OSError, ValueError, RuntimeError) as exc:
            raise Blocked("owner_exception_midapply_reference_incomplete") from exc
        if extra_audit["result"] != "NO_OBSERVED_CONFLICTS":
            raise Blocked("owner_exception_midapply_references_changed")
    inspect_image_references(
        [], [x for x in targets if x["kind"] == "image"],
        [x for x in targets if x["kind"] == "volume"],
        [x for x in targets if x["kind"] in FILE_KINDS
         or x["kind"] == "legacy-model-link"],
    )
    for item in targets:
        if item["kind"] == "volume":
            if volume_identity(item["id"]) != item["fingerprint"]:
                raise Blocked("volume_identity_changed_during_apply")
            run("docker", "volume", "rm", item["id"])
        if item["kind"] == "image":
            if (item["kind"], item["id"]) in approved:
                verify_owner_exception_identity(
                    "image", item["id"], approved[("image", item["id"])],
                    image_identity(item["id"]))
            if image_identity(item["id"]) != item["fingerprint"]:
                raise Blocked("image_identity_changed_during_apply")
            run("docker", "image", "rm", item["id"])
    for item in targets:
        if item["kind"] == "swap":
            run("sudo", str(checkout / "scripts/manage-swap.sh"),
                "remove", "--file", item["id"], "--yes")
    # Remove the exact legacy symlink *as a link*, before touching model
    # target directories. No dereference and no recursive deletion on links.
    for item in targets:
        if item["kind"] == "legacy-model-link":
            link = Path(item["id"])
            if legacy_model_link_identity(link, scope) != item["fingerprint"]:
                raise Blocked("legacy_model_link_drift_during_apply")
            link.unlink()
    # Release-pointer entries are inside data-root; recursive teardown only
    # unlinks them, never traverses their destinations. Check exact pointer
    # identity again before deleting any filesystem root.
    for item in targets:
        if item["kind"] == "release-link":
            if managed_release_link_identity(Path(item["id"]), scope) != item["fingerprint"]:
                raise Blocked("release_link_drift_during_apply:" + item["id"])
    # Delete separate model and research evidence paths before state/data.
    for kind in ("model", "model-cache", "project-cache", "forensic", "data-root", "state-root"):
        for item in targets:
            if item["kind"] == kind:
                # The snapshot was already compared under lock. Revalidate inode.
                path = Path(item["id"])
                old = item["fingerprint"]
                st = path.lstat()
                if (st.st_dev, st.st_ino, st.st_mode) != (
                        old["dev"], old["ino"], old["mode"]):
                    raise Blocked("file_identity_changed_during_apply:" + str(path))
                if (kind, item["id"]) in approved:
                    verify_owner_exception_identity(
                        kind, item["id"], approved[(kind, item["id"])])
                remove_tree(path, kind, scope)


def verify_removed(plan: dict) -> tuple[bool, list[str]]:
    """Independent read-only postcheck, allowed when state/data roots are gone."""
    scope = plan["scope"]
    current = inventory.gather(
        state=Path(scope["state"]), data=Path(scope["data"]),
        models=Path(scope["models"]), units=Path(scope["units"]),
        swap=Path(scope["swap"]), hf=Path(scope["hf"]),
        fstab=Path(scope["fstab"]), home=Path(scope["home"]),
        checkout=Path(scope["checkout"]),
    )
    issues = list(current["issues"])
    for item in current["resources"]:
        if item["kind"] in ("hf-cache", "shared-runtime-cache", "container-name"):
            continue
        if item["status"] != "ABSENT":
            issues.append(item["kind"] + ":" + item["locator"]
                          + ":" + item["status"])
    # This is project-scoped verification; other Docker/OS state excluded.
    return not issues, issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "apply", "verify", "diagnose"))
    parser.add_argument("--plan-file", type=Path, help="plan receipt outside project tree")
    parser.add_argument("--plan-sha", help="full 64-digit SHA256 of confirmed plan")
    parser.add_argument("--confirm", help="exact irreversible approval phrase")
    parser.add_argument("--owner-exception-file", type=Path,
                        help="reviewed exact-model/image exception; read-only input")
    parser.add_argument("--baseline-inventory", type=Path,
                        help="SHA-pinned saved read-only inventory")
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--checkout", type=Path, default=ROOT)
    parser.add_argument("--state-home", type=Path, default=Path(
        os.getenv("XDG_STATE_HOME", str(Path.home() / ".local/state"))))
    parser.add_argument("--data-home", type=Path, default=Path(
        os.getenv("XDG_DATA_HOME", str(Path.home() / ".local/share"))))
    parser.add_argument("--model-root", type=Path, default=Path(
        os.getenv("QWEN38_MODEL_ROOT", str(Path.home() / "models"))))
    parser.add_argument("--hf-home", type=Path, default=Path(
        os.getenv("HF_HOME", str(Path.home() / ".cache/huggingface"))))
    parser.add_argument("--unit-dir", type=Path, default=Path("/etc/systemd/system"))
    parser.add_argument("--fstab", type=Path, default=Path("/etc/fstab"))
    parser.add_argument("--swap", type=Path, default=Path("/swap-ple.img"))
    args = parser.parse_args()
    try:
        scope = scope_from_args(args)
        if args.action == "verify" and (args.owner_exception_file or args.baseline_inventory):
            raise Blocked("owner_exception_flags_not_valid_for_verify")
        exception, baseline = load_owner_exception(
            args.owner_exception_file, args.baseline_inventory, scope)
        if args.action == "plan":
            if args.confirm or args.plan_sha:
                raise Blocked("approval_flags_not_valid_for_read_only_plan")
            plan = scan(scope, exception, baseline)
            print(json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True))
            print("FULL_UNINSTALL_ACTION=READ_ONLY_PLAN", file=sys.stderr)
            return 0
        if args.plan_file is None:
            raise Blocked("existing_saved_plan_required")
        saved = load_plan(args.plan_file)
        if saved["scope"] != scope:
            raise Blocked("scope_differs_from_saved_plan")
        ensure_receipt_outside_scope(args.plan_file, saved)
        if args.action == "diagnose":
            if saved.get("owner_exception") != exception:
                raise Blocked("owner_exception_changed_since_plan")
            # Open the existing operation lock read-only. Never create/write it.
            lock_path = Path(scope["state"]) / "operation.lock"
            require_real_path(lock_path)
            with lock_path.open("rb") as locked:
                try:
                    fcntl.flock(locked.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise Blocked("concurrent_lifecycle_operation") from exc
                fresh = scan(scope, exception, baseline)
            changes = compare_receipts(saved, fresh)
            print("FULL_UNINSTALL_DIAGNOSIS=" +
                  ("PLAN_MATCHES_CURRENT_INVENTORY" if not changes else "DRIFT_DETECTED"))
            print("SAVED_PLAN_SHA256=" + saved["sha256"])
            print("FRESH_PLAN_SHA256=" + fresh["sha256"])
            print("CHANGED_TARGET_COUNT=" + str(len(changes)))
            for item in changes[:40]:
                print("DRIFT=" + json.dumps(item, sort_keys=True, ensure_ascii=False))
            if len(changes) > 40:
                print("ADDITIONAL_DRIFT_COUNT=" + str(len(changes) - 40))
            print("HOST_DELETION=NOT_PERFORMED")
            return 3 if changes else 0
        if args.action == "verify":
            clean, residuals = verify_removed(saved)
            if clean:
                print("FULL_UNINSTALL_POSTCHECK=PROJECT_SCOPED_EMPTY")
                return 0
            print("FULL_UNINSTALL_POSTCHECK=RESIDUALS_OR_INCOMPLETE")
            for problem in residuals[:40]:
                print("REMAINING=" + problem)
            return 3
        if saved.get("owner_exception") != exception:
            raise Blocked("owner_exception_changed_since_plan")
        if args.confirm != APPROVAL or args.plan_sha != saved["sha256"]:
            raise Blocked("typed_approval_or_full_digest_not_matched")
        state = Path(scope["state"])
        require_real_path(state)
        lock_file = state / "operation.lock"
        require_real_path(lock_file)
        with lock_file.open("a+b") as locked:
            try:
                fcntl.flock(locked.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise Blocked("concurrent_lifecycle_operation") from exc
            fresh = scan(scope, exception, baseline)
            if fresh != saved:
                raise Blocked("inventory_or_asset_identity_drift_before_apply")
            # No host operations before all read-only safety preflights above.
            execute(saved)
        clean, residuals = verify_removed(saved)
        if not clean:
            print("FULL_UNINSTALL_APPLY=PARTIAL_OR_RESIDUAL", file=sys.stderr)
            for problem in residuals[:40]:
                print("REMAINING=" + problem, file=sys.stderr)
            return 3
        print("FULL_UNINSTALL_APPLY=COMPLETE_PROJECT_SCOPE_VERIFIED")
        return 0
    except (Blocked, OSError, ValueError, KeyError, TypeError) as exc:
        print("FULL_UNINSTALL=BLOCKED_OR_PARTIAL_REVIEW_REQUIRED", file=sys.stderr)
        print("REASON=" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
