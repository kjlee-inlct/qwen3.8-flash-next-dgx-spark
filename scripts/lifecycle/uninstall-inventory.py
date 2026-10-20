#!/usr/bin/env python3
"""Project uninstall coverage inventory: READ ONLY, not a deletion authorizer.

Reports known project resources and uncertain ownership before any uninstall.
'verify' compares a previous plan JSON to a fresh scan, but does not certify
the entire operating system. No docker create/stop/rm, systemctl, swapoff,
file deletion, checkpoint read, or output file write is performed here.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
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
           units: Path, swap: Path, hf: Path, fstab: Path = Path("/etc/fstab")) -> dict:
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

    for item in bounded_children(models, issues):
        if item.name.startswith(("qwen3.8-", "qwen38-")):
            add("model", str(item), path_status(item), "UNVERIFIED",
                "discovered_not_proof_of_installer_ownership")
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
            if active not in ("inactive", "failed") or loaded not in ("not-found", "masked"):
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
        "never_autodelete_HF_cache_without_separate_provenance")

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
                   ("fstab", fstab))},
        "resources": sorted(rows.values(), key=lambda v: (v["kind"], v["locator"])),
        "issues": sorted(set(issues)),
        "exclusions": [
            "system_Docker_engine_and_NVIDIA_driver",
            "unrelated_system_swap",
            "unowned_HF_cache_and_other_apps",
            "external_Git_checkout",
            "unknown_nonproject_images_volumes_or_external_paths",
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
    p.add_argument("action", choices=("plan", "verify"))
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
    )
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
