#!/usr/bin/env python3
"""Crash-safe ownership registry for installer-created model and image assets.

The registry records only evidence-backed ownership. Existing assets may be observed
without becoming owned. Destructive callers must preflight before deletion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
KINDS = {"model", "image"}
STATES = {"claimed", "ready"}


class RegistryError(RuntimeError):
    pass


def _safe_text(value: str, label: str) -> str:
    if not value or any(ch in value for ch in ("\x00", "\n", "\r", "\t")):
        raise RegistryError(f"invalid {label}")
    return value


def _canonical_path(value: str) -> str:
    _safe_text(value, "path")
    path = Path(value)
    if not path.is_absolute():
        raise RegistryError(f"path must be absolute: {value}")
    return str(path.resolve(strict=False))


def _marker(path: Path) -> Path | None:
    for name in (".qwen38-model-manifest.json", ".qwen38-hybrid-manifest.json"):
        candidate = path / name
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _docker_image_id(name: str) -> str:
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", name],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _empty_registry() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "assets": []}


def _normalize_entry(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "kind",
        "locator",
        "root",
        "owned",
        "state",
        "fingerprint",
        "depends_on",
    }
    if set(raw) != allowed:
        raise RegistryError(f"unexpected asset fields: {sorted(set(raw) - allowed)}")
    kind = raw["kind"]
    if kind not in KINDS:
        raise RegistryError(f"invalid asset kind: {kind}")
    locator = raw["locator"]
    root = raw["root"]
    if kind == "model":
        locator = _canonical_path(locator)
        root = _canonical_path(root)
        model = Path(locator)
        root_path = Path(root)
        if model == root_path or root_path not in model.parents:
            raise RegistryError(f"model locator is outside its ownership root: {locator}")
    else:
        locator = _safe_text(locator, "image name")
        if root != "":
            raise RegistryError("image ownership root must be empty")
    owned = raw["owned"]
    if not isinstance(owned, bool):
        raise RegistryError("owned must be boolean")
    state = raw["state"]
    if state not in STATES:
        raise RegistryError(f"invalid asset state: {state}")
    fingerprint = raw["fingerprint"]
    if not isinstance(fingerprint, str) or any(ch in fingerprint for ch in ("\x00", "\n", "\r", "\t")):
        raise RegistryError("invalid asset fingerprint")
    dependencies = raw["depends_on"]
    if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
        raise RegistryError("depends_on must be a string list")
    if kind == "model":
        dependencies = sorted({_canonical_path(item) for item in dependencies if item})
    else:
        dependencies = sorted({_safe_text(item, "image dependency") for item in dependencies if item})
    if locator in dependencies:
        raise RegistryError(f"asset cannot depend on itself: {locator}")
    return {
        "kind": kind,
        "locator": locator,
        "root": root,
        "owned": owned,
        "state": state,
        "fingerprint": fingerprint,
        "depends_on": dependencies,
    }


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_registry()
    if path.is_symlink() or not path.is_file():
        raise RegistryError(f"registry path is unsafe: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"schema_version", "assets"}:
        raise RegistryError("invalid ownership registry object")
    if data["schema_version"] != SCHEMA_VERSION:
        raise RegistryError(f"unsupported ownership registry schema: {data['schema_version']}")
    if not isinstance(data["assets"], list):
        raise RegistryError("ownership registry assets must be a list")
    normalized = [_normalize_entry(item) for item in data["assets"]]
    keys = [(item["kind"], item["locator"]) for item in normalized]
    if len(keys) != len(set(keys)):
        raise RegistryError("duplicate ownership registry asset")
    data["assets"] = normalized
    return data


def save_registry(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise RegistryError(f"refusing symlinked registry: {path}")
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "assets": sorted(
            [_normalize_entry(item) for item in data["assets"]],
            key=lambda item: (item["kind"], item["locator"]),
        ),
    }
    fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(normalized, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def find_entry(data: dict[str, Any], kind: str, locator: str) -> dict[str, Any] | None:
    for item in data["assets"]:
        if item["kind"] == kind and item["locator"] == locator:
            return item
    return None


def track_model(
    registry: Path,
    path: str,
    root: str,
    owned: bool,
    dependencies: list[str],
) -> None:
    data = load_registry(registry)
    locator = _canonical_path(path)
    ownership_root = _canonical_path(root)
    dependencies = [_canonical_path(item) for item in dependencies]
    candidate = Path(locator)
    marker = _marker(candidate) if candidate.is_dir() and not candidate.is_symlink() else None
    state = "ready" if marker is not None else "claimed"
    fingerprint = _sha256(marker) if marker is not None else ""
    entry = find_entry(data, "model", locator)
    if entry is None:
        if not owned and marker is None:
            return
        entry = {
            "kind": "model",
            "locator": locator,
            "root": ownership_root,
            "owned": bool(owned),
            "state": state,
            "fingerprint": fingerprint,
            "depends_on": sorted(set(dependencies)),
        }
        data["assets"].append(entry)
    else:
        if entry["root"] != ownership_root:
            raise RegistryError(f"ownership root changed for {locator}")
        entry["owned"] = bool(entry["owned"] or owned)
        entry["depends_on"] = sorted(set(entry["depends_on"]) | set(dependencies))
        if marker is not None:
            entry["state"] = "ready"
            entry["fingerprint"] = fingerprint
        elif entry["state"] != "ready":
            entry["state"] = "claimed"
    save_registry(registry, data)


def track_image(registry: Path, name: str, owned: bool, dependencies: list[str]) -> None:
    data = load_registry(registry)
    locator = _safe_text(name, "image name")
    dependencies = [_safe_text(item, "image dependency") for item in dependencies]
    image_id = _docker_image_id(locator)
    if not owned and not image_id:
        return
    entry = find_entry(data, "image", locator)
    if entry is None:
        entry = {
            "kind": "image",
            "locator": locator,
            "root": "",
            "owned": bool(owned),
            "state": "ready" if image_id else "claimed",
            "fingerprint": image_id,
            "depends_on": sorted(set(dependencies)),
        }
        data["assets"].append(entry)
    else:
        entry["owned"] = bool(entry["owned"] or owned)
        entry["depends_on"] = sorted(set(entry["depends_on"]) | set(dependencies))
        if image_id:
            entry["state"] = "ready"
            entry["fingerprint"] = image_id
        elif entry["state"] != "ready":
            entry["state"] = "claimed"
    save_registry(registry, data)


def _parse_nul_pairs(blob: bytes) -> dict[str, str]:
    parts = blob.split(b"\0")
    if parts and parts[-1] == b"":
        parts.pop()
    if len(parts) % 2:
        raise RegistryError("strict install parser returned incomplete key/value output")
    result: dict[str, str] = {}
    for index in range(0, len(parts), 2):
        result[parts[index].decode()] = parts[index + 1].decode()
    return result


def bootstrap_install(registry: Path, manifest: Path, parser: Path) -> None:
    if not manifest.is_file() or manifest.is_symlink():
        return
    parsed = subprocess.run(
        [sys.executable, str(parser), "install-maintenance", str(manifest)],
        capture_output=True,
        check=False,
        timeout=30,
    )
    if parsed.returncode != 0:
        raise RegistryError("installation manifest failed strict ownership bootstrap parsing")
    values = _parse_nul_pairs(parsed.stdout)
    model = values.get("MODEL_DIR", "")
    if values.get("MODEL_OWNED") == "1" and model:
        track_model(registry, model, str(Path(model).resolve(strict=False).parent), True, [])
    image = values.get("VLLM_IMAGE", "")
    if values.get("IMAGE_OWNED") == "1" and image:
        track_image(registry, image, True, [])


def owns(registry: Path, kind: str, locator: str) -> bool:
    data = load_registry(registry)
    if kind == "model":
        locator = _canonical_path(locator)
    else:
        locator = _safe_text(locator, "image name")
    entry = find_entry(data, kind, locator)
    return bool(entry and entry["owned"])


def _model_present(entry: dict[str, Any]) -> bool:
    return Path(entry["locator"]).exists()


def _asset_present(entry: dict[str, Any]) -> bool:
    if entry["kind"] == "model":
        return _model_present(entry)
    return bool(_docker_image_id(entry["locator"]))


def _verify_model(entry: dict[str, Any]) -> None:
    path = Path(entry["locator"])
    root = Path(entry["root"])
    if path == root or root not in path.parents:
        raise RegistryError(f"unsafe owned model path: {path}")
    if not path.exists():
        return
    if path.is_symlink() or not path.is_dir():
        raise RegistryError(f"owned model path is not a real directory: {path}")
    marker = _marker(path)
    if marker is None:
        if entry["state"] == "claimed" and not any(path.iterdir()):
            return
        raise RegistryError(f"owned model path has no managed manifest: {path}")
    if entry["state"] == "ready":
        if not entry["fingerprint"]:
            raise RegistryError(f"ready model asset has no manifest fingerprint: {path}")
        current = _sha256(marker)
        if current != entry["fingerprint"]:
            raise RegistryError(f"owned model manifest drift detected: {path}")


def _verify_image(entry: dict[str, Any]) -> None:
    current = _docker_image_id(entry["locator"])
    if not current:
        return
    if entry["state"] == "claimed" and not entry["fingerprint"]:
        raise RegistryError(
            f"owned image creation was interrupted before its image ID was recorded: {entry['locator']}"
        )
    if not entry["fingerprint"] or current != entry["fingerprint"]:
        raise RegistryError(f"owned image ID drift detected: {entry['locator']}")


def _selected_owned(data: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [
        item
        for item in data["assets"]
        if item["owned"] and (kind == "all" or item["kind"] == kind)
    ]


def _dependency_blockers(data: dict[str, Any], candidates: list[dict[str, Any]]) -> list[str]:
    candidate_keys = {(item["kind"], item["locator"]) for item in candidates}
    blockers: list[str] = []
    for item in data["assets"]:
        if (item["kind"], item["locator"]) in candidate_keys:
            continue
        if not _asset_present(item):
            continue
        for dependency in item["depends_on"]:
            if (item["kind"], dependency) in candidate_keys:
                blockers.append(f"{item['kind']}:{item['locator']} -> {dependency}")
    return sorted(set(blockers))


def preflight_purge(registry: Path, kind: str) -> None:
    data = load_registry(registry)
    candidates = _selected_owned(data, kind)
    blockers = _dependency_blockers(data, candidates)
    if blockers:
        raise RegistryError(
            "owned asset is required by a retained dependent: " + "; ".join(blockers)
        )
    for item in candidates:
        if item["kind"] == "model":
            _verify_model(item)
        else:
            _verify_image(item)


def preflight_one(registry: Path, kind: str, locator: str) -> None:
    data = load_registry(registry)
    normalized = _canonical_path(locator) if kind == "model" else _safe_text(locator, "image name")
    entry = find_entry(data, kind, normalized)
    if entry is None or not entry["owned"]:
        raise RegistryError(f"asset is not recorded as installer-owned: {kind}:{normalized}")
    blockers = _dependency_blockers(data, [entry])
    if blockers:
        raise RegistryError(
            "owned asset is required by a retained dependent: " + "; ".join(blockers)
        )
    if kind == "model":
        _verify_model(entry)
    else:
        _verify_image(entry)


def _purge_order(data: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    candidates = _selected_owned(data, kind)
    by_key = {(item["kind"], item["locator"]): item for item in candidates}
    visited: set[tuple[str, str]] = set()
    visiting: set[tuple[str, str]] = set()
    ordered: list[dict[str, Any]] = []

    def visit(item: dict[str, Any]) -> None:
        key = (item["kind"], item["locator"])
        if key in visited:
            return
        if key in visiting:
            raise RegistryError(f"asset dependency cycle detected at {item['locator']}")
        visiting.add(key)
        # Append the dependent before its dependencies so deletion is safe.
        ordered.append(item)
        for dependency in item["depends_on"]:
            dep = by_key.get((item["kind"], dependency))
            if dep is not None:
                visit(dep)
        visiting.remove(key)
        visited.add(key)

    # More-dependent entries first makes the plan deterministic for the H3->H6 chain.
    for item in sorted(candidates, key=lambda value: (-len(value["depends_on"]), value["kind"], value["locator"])):
        visit(item)
    return ordered


def print_plan(registry: Path, kind: str) -> None:
    data = load_registry(registry)
    for item in _purge_order(data, kind):
        sys.stdout.write(f"{item['kind']}\t{item['locator']}\n")


def forget(registry: Path, kind: str, locator: str) -> None:
    data = load_registry(registry)
    if kind == "model":
        locator = _canonical_path(locator)
    else:
        locator = _safe_text(locator, "image name")
    data["assets"] = [
        item for item in data["assets"] if not (item["kind"] == kind and item["locator"] == locator)
    ]
    save_registry(registry, data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("registry")

    bootstrap = sub.add_parser("bootstrap-install")
    bootstrap.add_argument("registry")
    bootstrap.add_argument("manifest")
    bootstrap.add_argument("state_parser")

    model = sub.add_parser("track-model")
    model.add_argument("registry")
    model.add_argument("path")
    model.add_argument("root")
    model.add_argument("--owned", choices=("0", "1"), required=True)
    model.add_argument("--depends", action="append", default=[])

    image = sub.add_parser("track-image")
    image.add_argument("registry")
    image.add_argument("name")
    image.add_argument("--owned", choices=("0", "1"), required=True)
    image.add_argument("--depends", action="append", default=[])

    for name in ("owns-model", "owns-image"):
        cmd = sub.add_parser(name)
        cmd.add_argument("registry")
        cmd.add_argument("locator")

    for name in ("preflight-purge", "plan-purge"):
        cmd = sub.add_parser(name)
        cmd.add_argument("registry")
        cmd.add_argument("--kind", choices=("model", "image", "all"), default="all")

    one = sub.add_parser("preflight-one")
    one.add_argument("registry")
    one.add_argument("kind", choices=("model", "image"))
    one.add_argument("locator")

    remove = sub.add_parser("forget")
    remove.add_argument("registry")
    remove.add_argument("kind", choices=("model", "image"))
    remove.add_argument("locator")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    registry = Path(getattr(args, "registry", ""))
    try:
        if args.command == "verify":
            load_registry(registry)
        elif args.command == "bootstrap-install":
            bootstrap_install(registry, Path(args.manifest), Path(args.state_parser))
        elif args.command == "track-model":
            track_model(registry, args.path, args.root, args.owned == "1", args.depends)
        elif args.command == "track-image":
            track_image(registry, args.name, args.owned == "1", args.depends)
        elif args.command == "owns-model":
            return 0 if owns(registry, "model", args.locator) else 1
        elif args.command == "owns-image":
            return 0 if owns(registry, "image", args.locator) else 1
        elif args.command == "preflight-purge":
            preflight_purge(registry, args.kind)
        elif args.command == "preflight-one":
            preflight_one(registry, args.kind, args.locator)
        elif args.command == "plan-purge":
            print_plan(registry, args.kind)
        elif args.command == "forget":
            forget(registry, args.kind, args.locator)
        else:
            raise RegistryError(f"unsupported command: {args.command}")
    except (RegistryError, json.JSONDecodeError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
