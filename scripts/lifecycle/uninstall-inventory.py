#!/usr/bin/env python3
"""Project uninstall coverage inventory: READ ONLY, not a deletion authorizer.

Reports known project resources and uncertain ownership before any uninstall.
'verify' compares a previous plan JSON to a fresh scan, but does not certify
the entire operating system. No docker create/stop/rm, systemctl, swapoff,
file deletion, checkpoint read, or output file write is performed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import stat
import sys

# A read-only inventory must not generate __pycache__ in the repository.
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))
from asset_ownership import RegistryError, load_registry  # noqa: E402
from state_file import parse_install  # noqa: E402

DOCKER_ID = re.compile(r"[a-f0-9]{64}\Z")
UNITS = (
    "qwen38-flash-next.service",
    "qwen38-openwebui-proxy.socket",
    "qwen38-openwebui-proxy.service",
)
KNOWN_STATES = (
    "mazinb-m1-reinstall", "mazinb-m1", "orcarouter-ab",
    "hybrid-h6-m1", "runtime-stop.env",
)
PROJECT_EVIDENCE_PATHS = (
    "Workspace/llm/qwen38-m1-bench-results",
)
REPO_EVIDENCE_PATHS = (
    "docs/model-reports/evidence",
    str(Path("scripts") / "benchmark" / "evidence"),
)
PROJECT_CACHE_DIRS = (
    ".cache/vllm-qwen38",
    ".cache/vllm-qwen38-v029",
    ".cache/flashinfer-v029",
)
PROJECT_HF_PREFIXES = (
    "models--orcarouter--Qwen3.8-Flash-Next",
    "models--mazinb--Qwen3.8-Flash-Next",
    "models--nvidia--Qwen3.8-Flash-Next",
)
MAX_ENTRIES = 500
MAX_CAPTURE = 2 * 1024 * 1024


def entry(kind: str, locator: str, status: str, ownership: str, note: str = "") -> dict:
    return {"kind": kind, "locator": locator, "status": status,
            "ownership": ownership, "note": note}


def path_status(path: Path) -> str:
    if path.is_symlink():
        return "UNSAFE_SYMLINK"
    try:
        path.lstat()
        return "PRESENT"
    except FileNotFoundError:
        return "ABSENT"
    except OSError:
        return "UNKNOWN"


def bounded_children(path: Path, issues: list[str]) -> list[Path]:
    if path_status(path) == "ABSENT":
        return []
    if path_status(path) != "PRESENT" or not path.is_dir():
        issues.append("unsafe_or_non_directory:" + str(path))
        return []
    try:
        with os.scandir(path) as scan:
            children = []
            for child in scan:
                if len(children) >= MAX_ENTRIES:
                    issues.append("inventory_directory_limit:" + str(path))
                    break
                children.append(Path(child.path))
        return sorted(children)
    except OSError:
        issues.append("inventory_directory_unreadable:" + str(path))
        return []


def run_docker(*cmd: str) -> list[dict]:
    try:
        proc = subprocess.run(
            ["docker", *cmd], text=True, capture_output=True,
            timeout=25, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("docker_unavailable_or_timeout") from exc
    if proc.returncode or len(proc.stdout) > MAX_CAPTURE:
        raise RuntimeError("docker_query_failed_or_oversized")
    out = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        if len(out) >= MAX_ENTRIES:
            raise RuntimeError("docker_inventory_limit")
        val = json.loads(line)
        if not isinstance(val, dict):
            raise RuntimeError("docker_invalid_row")
        out.append(val)
    return out


def run_unit_status(name: str) -> dict[str, str]:
    try:
        proc = subprocess.run(
            ["systemctl", "show", name, "--property=LoadState,ActiveState,UnitFileState",
             "--no-pager"],
            text=True, capture_output=True, timeout=12, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("systemctl_unavailable_or_timeout") from exc
    if proc.returncode or len(proc.stdout) > 8192:
        raise RuntimeError("systemctl_query_failed")
    values = dict(line.split("=", 1) for line in proc.stdout.splitlines()
                  if "=" in line)
    if "LoadState" not in values or "ActiveState" not in values:
        raise RuntimeError("systemctl_result_incomplete")
    return values


def gather(*, state: Path, data: Path, models: Path,
           units: Path, swap: Path, hf: Path, fstab: Path = Path("/etc/fstab"),
           home: Path | None = None, checkout: Path | None = None) -> dict:
    home = home if home is not None else Path.home()
    checkout = checkout if checkout is not None else ROOT
    issues: list[str] = []
    rows: dict[tuple[str, str], dict] = {}

    def add(kind: str, locator: str, status: str, ownership: str, note: str = "") -> None:
        key = (kind, locator)
        previous = rows.get(key)
        # Retain strongest known attribution; never downgrade owner to inferred.
        rank = {"INSTALLER_OWNED": 3, "PROJECT_ASSOCIATED": 2,
                "UNVERIFIED": 1, "EXCLUDED_SHARED": 0}
        new = entry(kind, locator, status, ownership, note)
        if previous is None or rank[ownership] > rank[previous["ownership"]]:
            rows[key] = new

    manifest_path = state / "install.env"
    manifest = {}
    if path_status(manifest_path) == "PRESENT":
        try:
            if not manifest_path.is_file() or manifest_path.stat().st_size > 65536:
                raise ValueError("unsafe_manifest")
            manifest = parse_install(manifest_path, "install-uninstall")
        except (OSError, ValueError) as exc:
            issues.append("manifest_invalid:" + type(exc).__name__)
    elif path_status(manifest_path) != "ABSENT":
        issues.append("manifest_path_unsafe")
    add("manifest", str(manifest_path), path_status(manifest_path), "PROJECT_ASSOCIATED")
    add("state-root", str(state), path_status(state), "PROJECT_ASSOCIATED")
    add("data-root", str(data), path_status(data), "PROJECT_ASSOCIATED")

    registry_path = state / "asset-ownership.json"
    registry = {"assets": []}
    try:
        if registry_path.is_symlink():
            raise RegistryError("unsafe_symlink_registry")
        registry = load_registry(registry_path)
    except (OSError, ValueError, RegistryError, json.JSONDecodeError) as exc:
        issues.append("asset_registry_invalid:" + type(exc).__name__)
    add("registry", str(registry_path), path_status(registry_path), "PROJECT_ASSOCIATED")
    known_images: set[str] = set()
    owned_images: set[str] = set()
    if manifest:
        for kind, field, flag in (
            ("model", "MODEL_DIR", "MODEL_OWNED"),
            ("image", "VLLM_IMAGE", "IMAGE_OWNED"),
        ):
            locator = manifest[field]
            owner = "INSTALLER_OWNED" if manifest[flag] == "1" else "UNVERIFIED"
            if kind == "model":
                add(kind, locator, path_status(Path(locator)), owner, "active_manifest_only")
            else:
                known_images.add(locator)
                if owner == "INSTALLER_OWNED":
                    owned_images.add(locator)
        add("container-name", manifest["CONTAINER_NAME"], "UNKNOWN",
            "PROJECT_ASSOCIATED", "lookup_against_docker_inventory")
        swap = Path(manifest["SWAP_FILE"])
    for asset in registry["assets"]:
        kind = asset["kind"]
        locator = asset["locator"]
        owner = "INSTALLER_OWNED" if asset["owned"] else "UNVERIFIED"
        if kind == "model":
            add(kind, locator, path_status(Path(locator)), owner,
                "cumulative_ownership_registry")
        else:
            known_images.add(locator)
            if asset["owned"]:
                owned_images.add(locator)

    for model_root in dict.fromkeys((models, home / "models", checkout / "models")):
        for item in bounded_children(model_root, issues):
            if item.name.startswith(("qwen3.8-", "qwen38-")):
                add("model", str(item), path_status(item), "UNVERIFIED",
                    "all_project_profiles_including_OrcaRouter_NVIDIA_Hybrid_mazinb")
    legacy = checkout / "model"
    if path_status(legacy) != "ABSENT":
        add("model", str(legacy), path_status(legacy), "UNVERIFIED",
            "legacy_orcarouter_checkpoint_candidate_verify_checkpoint_contents")
    # Forensics are project-scoped deletion targets in a complete reset.
    for relative in PROJECT_EVIDENCE_PATHS:
        path = home / relative
        add("forensic", str(path), path_status(path),
            "PROJECT_ASSOCIATED", "local_experiment_archive_full_purge_target")
    add("forensic", str(state / "retirement-archives"),
        path_status(state / "retirement-archives"),
        "PROJECT_ASSOCIATED", "local_retirement_archive_full_purge_target")
    for relative in REPO_EVIDENCE_PATHS:
        path = checkout / relative
        add("forensic", str(path), path_status(path),
            "PROJECT_ASSOCIATED", "checkout_evidence_requires_explicit_repo_local_cleanup")
    for rel in PROJECT_CACHE_DIRS:
        location = home / rel
        add("project-cache", str(location), path_status(location),
            "PROJECT_ASSOCIATED", "dedicated_project_runtime_cache")
    add("shared-runtime-cache", str(home / ".cache/flashinfer"),
        path_status(home / ".cache/flashinfer"), "EXCLUDED_SHARED",
        "no_automatic_deletion_of_possible_foreign_shared_cache")
    for item in bounded_children(hf / "hub", issues):
        if item.name.startswith(PROJECT_HF_PREFIXES):
            add("model-cache", str(item), path_status(item), "UNVERIFIED",
                "project_checkpoint_cache_candidate_not_entire_shared_HF_root")
    for item in bounded_children(state, issues):
        add("state", str(item), path_status(item), "PROJECT_ASSOCIATED",
            "includes_experimental_journals_or_retained_evidence")
    for item in bounded_children(data, issues):
        add("release", str(item), path_status(item), "PROJECT_ASSOCIATED")

    for name in KNOWN_STATES:
        path = state / name
        add("state", str(path), path_status(path), "PROJECT_ASSOCIATED")
    for name in UNITS:
        path = units / name
        present = path_status(path)
        owner = "UNVERIFIED"
        if present == "PRESENT":
            try:
                # Unit ownership must be verified by exact managed marker
                # before removal, not inferred from unit name.
                with path.open("rb") as src:
                    marker = src.read(4096)
                if b"Managed qwen38-spark" in marker:
                    owner = "INSTALLER_OWNED"
            except OSError:
                issues.append("unit_unreadable:" + name)
        add("systemd", str(path), present, owner)
        try:
            unit_state = run_unit_status(name)
            active = unit_state["ActiveState"]
            loaded = unit_state["LoadState"]
            state_note = "load=" + loaded + ";active=" + active
            if active != "inactive" or loaded != "not-found":
                add("unit-runtime", name, "PRESENT", "PROJECT_ASSOCIATED", state_note)
            else:
                add("unit-runtime", name, "ABSENT", "PROJECT_ASSOCIATED", state_note)
        except RuntimeError as exc:
            issues.append("systemd_status_incomplete:" + name + ":" + str(exc))
            add("unit-runtime", name, "UNKNOWN", "UNVERIFIED")

    fstab_id = str(fstab) + "#qwen38-ple-swap"
    if path_status(fstab) == "PRESENT" and fstab.is_file():
        try:
            if fstab.stat().st_size > 1024 * 1024:
                raise ValueError("fstab_oversized")
            lines = fstab.read_text(encoding="utf-8").splitlines()
            matched = [line for line in lines
                       if line.startswith(str(swap) + " ")
                       and "# qwen38-ple-swap" in line]
            add("swap-fstab", fstab_id, "PRESENT" if matched else "ABSENT",
                "PROJECT_ASSOCIATED", "dedicated_swap_persistence_marker")
        except (OSError, ValueError):
            issues.append("fstab_inspection_failed")
    else:
        issues.append("fstab_unavailable_or_unsafe")

    add("swap", str(swap), path_status(swap),
        "INSTALLER_OWNED" if manifest.get("SWAP_OWNED") == "1" else "UNVERIFIED",
        "system_swap_elsewhere_is_excluded;fstab_marker_not_probed")
    add("hf-cache", str(hf), path_status(hf), "EXCLUDED_SHARED",
        "shared_HF_root_excluded_but_project-specific_cache_entries_must_be_resolved")

    try:
        docker_containers = run_docker("ps", "-a", "--no-trunc", "--format", "{{json .}}")
        for item in docker_containers:
            cid = item.get("ID", "")
            names = item.get("Names", "")
            labels = item.get("Labels", "")
            if not isinstance(cid, str) or not isinstance(names, str) or not isinstance(labels, str):
                raise RuntimeError("docker_container_bad_types")
            if not DOCKER_ID.fullmatch(cid):
                raise RuntimeError("docker_container_nonexact_id")
            relevant = (any(n.startswith(("qwen38-", "qwen3.8-")) for n in names.split(","))
                        or "qwen38." in labels or names == manifest.get("CONTAINER_NAME"))
            if relevant:
                add("container", cid, "PRESENT", "PROJECT_ASSOCIATED",
                    "name=" + names[:130] + ";labels=" + labels[:180])
        docker_images = run_docker("image", "ls", "--no-trunc", "--format", "{{json .}}")
        found_images: set[str] = set()
        for item in docker_images:
            repo = item.get("Repository", "")
            tag = item.get("Tag", "")
            if not isinstance(repo, str) or not isinstance(tag, str):
                raise RuntimeError("docker_image_bad_types")
            name = repo + ":" + tag
            if name in known_images or repo.startswith(("vllm-", "qwen38-")):
                found_images.add(name)
                add("image", name, "PRESENT",
                    "INSTALLER_OWNED" if name in owned_images else "UNVERIFIED",
                    "docker_image_inventory")
        for name in sorted(known_images - found_images):
            add("image", name, "ABSENT",
                "INSTALLER_OWNED" if name in owned_images else "UNVERIFIED")

        for item in run_docker("volume", "ls", "--format", "{{json .}}"):
            name = item.get("Name", "")
            labels = item.get("Labels", "")
            if not isinstance(name, str) or not isinstance(labels, str):
                raise RuntimeError("docker_volume_bad_types")
            if name.startswith(("qwen38-", "qwen3.8-")) or "qwen38." in labels:
                add("volume", name, "PRESENT", "UNVERIFIED",
                    "docker_volume_project_candidate;no_automatic_removal")
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        issues.append("docker_inventory_incomplete:" + str(exc))
        for name in known_images:
            add("image", name, "UNKNOWN",
                "INSTALLER_OWNED" if name in owned_images else "UNVERIFIED")

    return {
        "schema": 1,
        "mode": "READ_ONLY_PROJECT_SCOPE",
        "scope": {key: str(value) for key, value in
                  (("state", state), ("data", data), ("models", models),
                   ("units", units), ("swap", swap), ("hf", hf),
                   ("fstab", fstab), ("home", home), ("checkout", checkout))},
        "resources": sorted(rows.values(), key=lambda v: (v["kind"], v["locator"])),
        "issues": sorted(set(issues)),
        "exclusions": [
            "system_Docker_engine_and_NVIDIA_driver",
            "unrelated_system_swap",
            "unowned_HF_cache_and_other_apps",
            "remote_GitHub_history_not_removed_by_local_project_uninstall",
            "unknown_nonproject_images_volumes_or_external_paths",
        ],
    }


def model_provenance_audit(observed: dict) -> dict:
    """Read only bounded manifest/registry/file-size evidence, not model weights.

    An identical model marker is project association, never ownership proof.
    File-size checks use lstat and reject symlink traversal; SHA256 of model
    content is deliberately NOT calculated by this lightweight audit.
    """
    if observed["issues"]:
        raise RuntimeError("project_inventory_incomplete")
    state = Path(observed["scope"]["state"])
    registry = load_registry(state / "asset-ownership.json")
    records: dict[str, list[dict]] = {}
    for item in registry["assets"]:
        if item["kind"] == "model":
            records.setdefault(item["locator"], []).append(item)
    models = [r for r in observed["resources"]
              if r["kind"] == "model" and r["status"] == "PRESENT"]
    if len(models) > MAX_ENTRIES:
        raise RuntimeError("model_provenance_candidate_limit")
    summaries = []
    for candidate in models:
        path = Path(candidate["locator"])
        problems: list[str] = []
        matches = records.get(str(path), [])
        if len(matches) != 1:
            problems.append("registry_record_cardinality")
        record = matches[0] if len(matches) == 1 else None
        marker = path / ".qwen38-model-manifest.json"
        summary = {
            "model_path": str(path),
            "inventory_ownership": candidate["ownership"],
            "registry_matches": len(matches),
            "registry_owned": record["owned"] if record else None,
            "registry_state": record["state"] if record else None,
            "marker_sha256": None,
            "recorded_sha256_matches": False,
            "marker_repository": None,
            "marker_revision": None,
            "marker_status": None,
            "listed_files": 0,
            "present_regular_files": 0,
            "unknown_size_entries": 0,
            "provided_content_sha256_entries": 0,
            "content_sha256_verified": 0,
            "issues": problems,
        }
        try:
            if path.is_symlink() or not path.is_dir():
                raise ValueError("model_root_not_real_directory")
            if marker.is_symlink() or not marker.is_file():
                raise ValueError("model_marker_missing_or_symlink")
            if marker.stat().st_size > 1024 * 1024:
                raise ValueError("model_marker_oversized")
            raw = marker.read_bytes()
            marker_sha = hashlib.sha256(raw).hexdigest()
            summary["marker_sha256"] = marker_sha
            summary["recorded_sha256_matches"] = bool(
                record and record["fingerprint"] == marker_sha
                and record["state"] == "ready")
            if not summary["recorded_sha256_matches"]:
                problems.append("marker_registry_fingerprint_mismatch")
            obj = json.loads(raw)
            if not isinstance(obj, dict) or set(obj) != {
                    "schema_version", "repository", "revision", "status", "files"}:
                raise ValueError("model_marker_schema_unexpected")
            summary["marker_repository"] = obj["repository"]
            summary["marker_revision"] = obj["revision"]
            summary["marker_status"] = obj["status"]
            if obj["schema_version"] != 1:
                problems.append("model_marker_schema_version")
            if (not isinstance(obj["repository"], str)
                    or not obj["repository"]
                    or any(ch in obj["repository"] for ch in ("\\0", "\\n", "\\r"))):
                problems.append("model_marker_repository_invalid")
            if (not isinstance(obj["revision"], str)
                    or not re.fullmatch(r"[a-f0-9]{40}", obj["revision"])):
                problems.append("model_marker_revision_not_pinned")
            if obj["status"] != "complete":
                problems.append("model_marker_not_complete")
            files = obj["files"]
            if not isinstance(files, list) or not files or len(files) > 5000:
                raise ValueError("model_marker_file_list_invalid")
            summary["listed_files"] = len(files)
            visited: set[str] = set()
            for entry in files:
                if not isinstance(entry, dict) or set(entry) != {
                        "path", "size", "sha256"}:
                    raise ValueError("model_marker_file_entry_invalid")
                name, size, sha = entry["path"], entry["size"], entry["sha256"]
                if (not isinstance(name, str) or not name
                        or name.startswith("/")
                        or any(part in ("", ".", "..") for part in name.split("/"))
                        or "\\0" in name or "\\\\" in name or name in visited):
                    raise ValueError("model_marker_file_path_invalid")
                visited.add(name)
                if type(size) is not int or size < 0:
                    raise ValueError("model_marker_file_size_invalid")
                if sha is not None:
                    if not isinstance(sha, str) or not re.fullmatch(
                            r"[a-f0-9]{64}", sha):
                        raise ValueError("model_marker_file_hash_invalid")
                    summary["provided_content_sha256_entries"] += 1
                target = path
                try:
                    for component in name.split("/"):
                        target = target / component
                        mode = target.lstat().st_mode
                        if stat.S_ISLNK(mode):
                            raise ValueError("symlinked_model_file_or_parent")
                    if not stat.S_ISREG(mode):
                        raise ValueError("nonregular_model_file")
                    actual_size = target.stat().st_size
                    if size and size != actual_size:
                        raise ValueError("model_file_size_mismatch")
                    if not size:
                        summary["unknown_size_entries"] += 1
                    summary["present_regular_files"] += 1
                except (OSError, ValueError) as exc:
                    if len(problems) < 12:
                        problems.append(type(exc).__name__ + ":" +
                                        (str(exc) if isinstance(exc, ValueError)
                                         else "missing_or_unreadable_model_file"))
            if record and record["owned"] is False:
                # Registry ownership is deliberately unchanged.
                pass
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            problems.append("model_provenance_unreadable_or_invalid:" +
                            type(exc).__name__)
        summaries.append(summary)
    result = ("NO_MODEL_CANDIDATES" if not summaries else
              "REVIEW_REQUIRED" if any(item["issues"] for item in summaries)
              else "CONSISTENT_METADATA_NOT_OWNERSHIP")
    return {
        "result": result, "models": summaries,
        "limitations": [
            "marker_sha256_only_no_model_content_hashing",
            "size_zero_is_unknown_expected_size",
            "owned_false_not_promoted_or_authorized",
            "file_metadata_is_not_exclusive_ownership_proof",
            "point_in_time_read_only_probe",
        ],
    }


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def reference_audit(observed: dict) -> dict:
    """Independently check foreign Docker references; never authorize deletion.

    Unlike the destructive engine's exact-target preflight, this uses read-only
    discovery candidates, even when their ownership is explicitly UNVERIFIED.
    Both project bind paths and scoped parent roots are checked. A zero-conflict
    result does not attest ownership or non-Docker filesystem users.
    """
    if observed["issues"]:
        raise RuntimeError("project_inventory_incomplete")
    rows = observed["resources"]
    project = {r["locator"] for r in rows
               if r["kind"] == "container" and r["status"] == "PRESENT"}
    images = {r["locator"] for r in rows
              if r["kind"] == "image" and r["status"] == "PRESENT"}
    volumes = {r["locator"] for r in rows
               if r["kind"] == "volume" and r["status"] == "PRESENT"}
    file_kinds = {"model", "model-cache", "project-cache", "forensic",
                  "state-root", "data-root"}
    paths = [Path(r["locator"]) for r in rows
             if (r["kind"] in file_kinds
                 and r["status"] in ("PRESENT", "UNSAFE_SYMLINK")
                 and r["ownership"] != "EXCLUDED_SHARED")]
    # The exact legacy checkout/model link has a dedicated link-only policy.
    for row in rows:
        if (row["kind"] == "model" and row["status"] == "UNSAFE_SYMLINK"
                and row["locator"] != str(Path(observed["scope"]["checkout"]) / "model")):
            raise RuntimeError("unexpected_symlinked_model_in_reference_scope")
    if (len(project) > MAX_ENTRIES or len(images) > MAX_ENTRIES
            or len(paths) > MAX_ENTRIES or len(volumes) > MAX_ENTRIES):
        raise RuntimeError("reference_audit_candidate_limit")
    if not all(DOCKER_ID.fullmatch(i) for i in project):
        raise RuntimeError("reference_audit_invalid_project_id")

    image_ids: set[str] = set()
    for tag in sorted(images):
        reply = run_docker("image", "inspect", tag, "--format", "{{json .}}")
        if len(reply) != 1 or not isinstance(reply[0].get("Id"), str):
            raise RuntimeError("reference_image_identity_incomplete")
        identity = reply[0]["Id"]
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", identity):
            raise RuntimeError("reference_image_id_invalid")
        image_ids.add(identity)

    containers = run_docker("ps", "-a", "--no-trunc", "--format", "{{json .}}")
    all_ids = [x.get("ID") for x in containers]
    if (len(all_ids) != len(set(all_ids))
            or any(not isinstance(x, str) or not DOCKER_ID.fullmatch(x)
                   for x in all_ids)
            or not project.issubset(all_ids)):
        raise RuntimeError("reference_container_inventory_drift")
    conflicts: list[dict] = []
    external = 0
    for cid in sorted(set(all_ids) - project):
        external += 1
        reply = run_docker("inspect", cid, "--format", "{{json .}}")
        if len(reply) != 1 or reply[0].get("Id") != cid:
            raise RuntimeError("reference_external_identity_changed")
        obj = reply[0]
        matched: list[str] = []
        if obj.get("Image") in image_ids:
            matched.append("project_image_id")
        mounts = obj.get("Mounts")
        if not isinstance(mounts, list):
            raise RuntimeError("reference_external_mounts_incomplete")
        for mount in mounts:
            if not isinstance(mount, dict):
                raise RuntimeError("reference_external_mount_invalid")
            volume_name = mount.get("Name")
            if volume_name is not None and not isinstance(volume_name, str):
                raise RuntimeError("reference_external_mount_volume_invalid")
            if isinstance(volume_name, str) and volume_name in volumes:
                matched.append("project_docker_volume:" + volume_name)
            source = mount.get("Source")
            if source is None:
                continue
            if not isinstance(source, str):
                raise RuntimeError("reference_external_mount_source_invalid")
            if not source.startswith("/"):
                continue
            candidate = Path(os.path.abspath(source))
            # Also compare canonical destinations; a foreign symlink must
            # never be used to hide a selected project file reference.
            resolved = candidate.resolve(strict=False)
            for path in paths:
                if (_paths_overlap(candidate, path)
                        or _paths_overlap(resolved, path.resolve(strict=False))):
                    matched.append("project_file_mount:" + source)
                    break
        if matched:
            conflicts.append({"container_id": cid,
                              "references": sorted(set(matched))})
    aliases: list[str] = []
    for obj in run_docker("image", "ls", "--no-trunc", "--format", "{{json .}}"):
        image_id = obj.get("ID")
        repo, tag = obj.get("Repository"), obj.get("Tag")
        if not all(isinstance(x, str) for x in (image_id, repo, tag)):
            raise RuntimeError("reference_image_list_invalid")
        if image_id in image_ids and (repo + ":" + tag) not in images:
            aliases.append(repo + ":" + tag)
    return {
        "result": "CONFLICTS" if conflicts or aliases else "NO_OBSERVED_CONFLICTS",
        "project_container_count": len(project),
        "total_docker_containers": len(all_ids),
        "external_container_count": external,
        "project_image_count": len(images),
        "candidate_volume_count": len(volumes),
        "external_reference_conflicts": conflicts,
        "other_image_tag_aliases": sorted(set(aliases)),
        "limitations": [
            "not_an_ownership_proof",
            "does_not_detect_nonDocker_file_users",
            "restricted_to_bounded_inventory_candidate_roots",
            "point_in_time_not_an_apply_authorization",
        ],
    }


def verification(baseline: dict, current: dict) -> tuple[str, list[str]]:
    if (baseline.get("schema") != 1
            or baseline.get("mode") != "READ_ONLY_PROJECT_SCOPE"
            or baseline.get("scope") != current["scope"]
            or not isinstance(baseline.get("resources"), list)):
        return "INVALID_BASELINE", ["baseline_scope_or_schema_mismatch"]
    expected = set()
    for item in baseline["resources"]:
        if not isinstance(item, dict) or not all(
            isinstance(item.get(k), str) for k in
            ("kind", "locator", "status", "ownership")
        ):
            return "INVALID_BASELINE", ["baseline_resource_invalid"]
        expected.add((item["kind"], item["locator"]))
    observed = {(v["kind"], v["locator"]): v for v in current["resources"]}
    leftovers = []
    for key in expected | set(observed):
        item = observed.get(key)
        if item is None:
            continue  # absent from bounded current enumeration
        if item["ownership"] == "EXCLUDED_SHARED":
            continue
        if item["status"] != "ABSENT" and item["kind"] != "container-name":
            leftovers.append(item["kind"] + ":" + item["locator"] + ":" + item["status"])
    if current["issues"]:
        return "INCOMPLETE", sorted(current["issues"] + leftovers)
    if leftovers:
        return "RESIDUALS_PRESENT", sorted(leftovers)
    return "PROJECT_SCOPE_NO_RESIDUALS", []


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("plan", "verify", "references", "provenance"))
    p.add_argument("--json", action="store_true", help="emit bounded JSON plan to stdout")
    p.add_argument("--baseline", type=Path, help="saved plan JSON (read only; verify only)")
    p.add_argument("--state-home", type=Path,
                   default=Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))))
    p.add_argument("--data-home", type=Path,
                   default=Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))))
    p.add_argument("--model-root", type=Path,
                   default=Path(os.environ.get("QWEN38_MODEL_ROOT", str(ROOT / "models"))))
    p.add_argument("--unit-dir", type=Path, default=Path("/etc/systemd/system"))
    p.add_argument("--swap-file", type=Path, default=Path("/swap-ple.img"))
    p.add_argument("--fstab-path", type=Path, default=Path("/etc/fstab"))
    p.add_argument("--home-path", type=Path, default=Path.home())
    p.add_argument("--checkout-path", type=Path, default=ROOT)
    p.add_argument("--hf-home", type=Path,
                   default=Path(os.environ.get("HF_HOME", str(Path.home() / ".cache/huggingface"))))
    args = p.parse_args()
    if (args.action == "verify") != (args.baseline is not None):
        p.error("--baseline required for verify and forbidden for plan")
    result = gather(
        state=args.state_home / "qwen38-spark",
        data=args.data_home / "qwen38-spark",
        models=args.model_root, units=args.unit_dir,
        swap=args.swap_file, hf=args.hf_home, fstab=args.fstab_path,
        home=args.home_path, checkout=args.checkout_path,
    )
    if args.action == "provenance":
        try:
            audit = model_provenance_audit(result)
        except (OSError, ValueError, RuntimeError, RegistryError) as exc:
            audit = {"result": "INCOMPLETE", "reason": str(exc)}
        if args.json:
            print(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print("MODEL_PROVENANCE=READ_ONLY_METADATA_NO_MODEL_CONTENT_HASH")
            print("MODEL_PROVENANCE_RESULT=" + audit["result"])
            if audit["result"] == "INCOMPLETE":
                print("MODEL_PROVENANCE_ISSUE=" + audit["reason"])
            else:
                for model in audit["models"]:
                    print("MODEL=" + model["model_path"])
                    for key in (
                            "inventory_ownership", "registry_matches",
                            "registry_owned", "registry_state", "marker_sha256",
                            "recorded_sha256_matches", "marker_repository",
                            "marker_revision", "marker_status", "listed_files",
                            "present_regular_files", "unknown_size_entries",
                            "provided_content_sha256_entries",
                            "content_sha256_verified"):
                        print(key.upper() + "=" + str(model[key]))
                    for issue in model["issues"]:
                        print("MODEL_PROVENANCE_ISSUE=" + issue)
                print("PROVENANCE_IS_NOT_DELETION_AUTHORIZATION=1")
        return 2 if audit["result"] in ("INCOMPLETE", "REVIEW_REQUIRED") else 0
    if args.action == "references":
        try:
            audit = reference_audit(result)
        except (OSError, ValueError, RuntimeError) as exc:
            audit = {"result": "INCOMPLETE", "reason": str(exc)}
        if args.json:
            print(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print("UNINSTALL_REFERENCES=READ_ONLY_NO_DELETION")
            print("REFERENCE_AUDIT_RESULT=" + audit["result"])
            if audit["result"] == "INCOMPLETE":
                print("REFERENCE_AUDIT_ISSUE=" + audit["reason"])
            else:
                for field in ("project_container_count", "total_docker_containers",
                              "external_container_count", "project_image_count",
                              "candidate_volume_count"):
                    print(field.upper() + "=" + str(audit[field]))
                print("EXTERNAL_REFERENCE_CONFLICTS=" +
                      str(len(audit["external_reference_conflicts"])))
                for item in audit["external_reference_conflicts"]:
                    print("EXTERNAL_REFERENCE=" + json.dumps(item, sort_keys=True))
                print("OTHER_IMAGE_TAG_ALIASES=" +
                      str(len(audit["other_image_tag_aliases"])))
                for tag in audit["other_image_tag_aliases"]:
                    print("OTHER_TAG_SAME_IMAGE_ID=" + tag)
                print("REFERENCE_AUDIT_IS_NOT_OWNERSHIP_AUTHORIZATION=1")
        return 2 if audit["result"] == "INCOMPLETE" else (
            3 if audit["result"] == "CONFLICTS" else 0)
    if args.action == "verify":
        try:
            assert args.baseline is not None
            if args.baseline.is_symlink() or args.baseline.stat().st_size > MAX_CAPTURE:
                raise ValueError("unsafe_baseline")
            baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
            outcome, details = verification(baseline, result)
        except (OSError, ValueError, TypeError) as exc:
            outcome, details = "INVALID_BASELINE", [type(exc).__name__]
        result["verification"] = {"result": outcome, "details": details}
    else:
        result["verification"] = {"result": "NOT_PERFORMED", "details": []}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("UNINSTALL_AUDIT=READ_ONLY_NO_DELETION")
        print("ACTION=" + args.action)
        for item in result["resources"]:
            if item["status"] == "ABSENT":
                continue
            print(f'{item["kind"]}: {item["status"]} '
                  f'ownership={item["ownership"]} locator={item["locator"]}')
        for issue in result["issues"]:
            print("INVENTORY_ISSUE=" + issue)
        for exclusion in result["exclusions"]:
            print("NOT_IN_SCOPE=" + exclusion)
        print("UNINSTALL_AUDIT_VERIFICATION=" + result["verification"]["result"])
        for detail in result["verification"]["details"][:40]:
            print("VERIFY_DETAIL=" + detail)
        print("UNINSTALL_APPLY=NOT_IMPLEMENTED_IN_AUDITOR")
    if result["issues"] or result["verification"]["result"] in ("INVALID_BASELINE", "INCOMPLETE"):
        return 2
    if args.action == "verify" and result["verification"]["result"] != "PROJECT_SCOPE_NO_RESIDUALS":
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
