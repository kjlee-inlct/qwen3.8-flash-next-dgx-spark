#!/usr/bin/env python3
"""Read-only, exact-ID postcheck after the 2026-10-18 single PLE source probe.

The historical pre/post mismatch cannot be reconstructed without retained
field-level snapshots. This script only assesses CURRENT metadata safely.
No docker create, cp, rm, start, run, exec, or filesystem writes.
"""
from __future__ import annotations

import json

import audit_installed_ple_image as audit
import probe_isolated_ple_source as probe

TEMP_ID = "eb91d18dd1a1b45a4cba233160165bbe43b7835afa21873686402b505aac9375"
TEMP_NAME = "qwen38-ple-read-e7e7bac84a0b79e85020ff51"

FIELDS = ("Id", "Image", "Name", "Mounts", "State", "HostConfig")


class ReviewError(Exception):
    """Source-free status for read-only postcheck."""


def fetch_one(kind: str, value: str) -> dict:
    if kind not in ("image", "container"):
        raise ReviewError("Unknown inspect type")
    return audit.one_json(probe.docker([kind, "inspect", value]), kind)


def temp_absence() -> str:
    """Verify both exact full ID and unique name are absent, never delete."""
    result = []
    for ref in (TEMP_ID, TEMP_NAME):
        try:
            fetch_one("container", ref)
        except probe.CommandFailed as exc:
            if exc.category == "CONTAINER_NOT_FOUND":
                result.append("ABSENT")
                continue
            return "INCONCLUSIVE_INSPECT_FAILED"
        except (probe.ProbeError, audit.AttestationError, ValueError, OSError):
            return "INCONCLUSIVE_INSPECT_FAILED"
        result.append("PRESENT_STOP")
    if all(value == "ABSENT" for value in result):
        return "ABSENT_ID_AND_NAME"
    if "PRESENT_STOP" in result:
        return "PRESENT_STOP"
    return "INCONCLUSIVE_INSPECT_FAILED"


def compare_mounts(a: object, b: object) -> str:
    """Privacy-safe exact-value comparison, with Docker mount array order ignored.

    Docker mount inventory is semantically a collection: dictionary/iteration
    order is not a stable ownership signal. We still compare ALL mounted
    record values, including Source paths, privately. Never print those values
    or even their hashes: only fixed classification labels are returned.
    """
    def validated(mounts: object) -> list[dict] | None:
        if not isinstance(mounts, list):
            return None
        result: list[dict] = []
        seen: set[str] = set()
        for mount in mounts:
            if not isinstance(mount, dict):
                return None
            dest = mount.get("Destination")
            if (not isinstance(dest, str) or not dest.startswith("/")
                    or ".." in dest.split("/") or dest in seen
                    or not isinstance(mount.get("Type"), str)
                    or not isinstance(mount.get("RW"), bool)):
                return None
            seen.add(dest)
            result.append(mount)
        return result

    one, two = validated(a), validated(b)
    if one is None or two is None:
        return "INVALID_MOUNT_METADATA"
    if one == two:
        return "IDENTICAL_ORDER"
    # Sort the complete records (including sensitive fields) IN MEMORY.
    # No contents or derived digests leave this process.
    serialized_one = [json.dumps(m, sort_keys=True, separators=(",", ":"))
                      for m in one]
    serialized_two = [json.dumps(m, sort_keys=True, separators=(",", ":"))
                      for m in two]
    if sorted(serialized_one) == sorted(serialized_two):
        return "ORDER_ONLY"
    first = {m["Destination"]: m for m in one}
    second = {m["Destination"]: m for m in two}
    if first.keys() != second.keys():
        return "DESTINATION_MEMBERSHIP_CHANGED"
    if any(
        (first[d]["Type"], first[d]["RW"]) !=
        (second[d]["Type"], second[d]["RW"])
        for d in first
    ):
        return "TYPE_OR_RW_CHANGED"
    return "OTHER_MOUNT_METADATA_CHANGED"


def compare_fields(a: dict, b: dict) -> str:
    mounts = compare_mounts(a.get("Mounts"), b.get("Mounts"))
    changed = [
        field for field in FIELDS if field != "Mounts"
        and json.dumps(a.get(field), sort_keys=True, separators=(",", ":"))
        != json.dumps(b.get(field), sort_keys=True, separators=(",", ":"))
    ]
    if mounts not in ("IDENTICAL_ORDER", "ORDER_ONLY"):
        changed.append("Mounts")
    # Field NAMES only: never emit the values of HostConfig, mount sources,
    # labels, environment, checkpoint paths, or State.Error.
    return "MATCH" if not changed else "DIFFERENT_" + "_".join(changed)


def check_protected(name: str, cid: str) -> dict[str, str]:
    by_name = fetch_one("container", name)
    by_id = fetch_one("container", cid)
    for item in (by_name, by_id):
        config, state, hc = item.get("Config"), item.get("State"), item.get("HostConfig")
        if (item.get("Id") != cid or item.get("Name") != "/" + name
                or item.get("Image") != probe.EXPECTED_IMAGE_ID
                or not isinstance(config, dict)
                or config.get("Image") != audit.IMAGE_TAG):
            raise ReviewError("Protected immutable identity mismatch")
        if not isinstance(state, dict) or not isinstance(hc, dict):
            raise ReviewError("Protected state or HostConfig unavailable")
        if state.get("Status") != "exited" or hc.get("ReadonlyRootfs") is not False:
            raise ReviewError("Protected stopped/rootfs metadata mismatch")
        if audit.model_config_mount_topology(item) != "MODEL_CONFIG_NESTED_RO_BINDS":
            raise ReviewError("Protected original nested bind topology mismatch")
    return {
        "identity": "MATCH_EXACT_ID_IMAGE_NAME",
        "state": "EXITED",
        "rootfs": "READONLY_FALSE",
        "mount_topology": "MODEL_CONFIG_NESTED_RO_BINDS",
        "name_vs_id_mounts": compare_mounts(
            by_name.get("Mounts"), by_id.get("Mounts")
        ),
        "name_vs_id_fields": compare_fields(by_name, by_id),
    }


def inspect_now() -> tuple[dict[str, str], bool]:
    result: dict[str, str] = {
        "result_kind": "CURRENT_READ_ONLY_NOT_HISTORICAL_REPLAY",
        "temp_absence": temp_absence(),
        "historical_failure_cause": "UNRECOVERABLE_WITHOUT_PRE_POST_FIELD_SNAPSHOTS",
        "docker_mutation": "NONE",
        "docker_copy": "NOT_PERFORMED",
        "gpu_run": "NOT_PERFORMED",
    }
    ok = result["temp_absence"] == "ABSENT_ID_AND_NAME"
    try:
        image = fetch_one("image", audit.IMAGE_TAG)
        if (image.get("Id") != probe.EXPECTED_IMAGE_ID
                or image.get("Size") != probe.EXPECTED_IMAGE_SIZE):
            raise ReviewError("Pinned image identity/size mismatch")
        result["image"] = "MATCH_PINNED_ID_AND_SIZE"
    except (ReviewError, probe.ProbeError, audit.AttestationError, ValueError, OSError):
        result["image"] = "INCONCLUSIVE_OR_CHANGED"
        ok = False
    for alias, name, cid in (
        ("managed", audit.MANAGED_CONTAINER, probe.EXPECTED_MANAGED_ID),
        ("legacy", audit.LEGACY_CONTAINER, probe.EXPECTED_LEGACY_ID),
    ):
        try:
            values = check_protected(name, cid)
            for key, value in values.items():
                result[f"{alias}_{key}"] = value
            if values["name_vs_id_fields"] != "MATCH":
                ok = False
        except (ReviewError, probe.ProbeError, audit.AttestationError, ValueError, OSError):
            result[f"{alias}_review"] = "INCONCLUSIVE_OR_CHANGED"
            ok = False
    result["current_static_postcheck"] = (
        "PASS_CURRENT_ONLY" if ok else "STOP_REVIEW_REQUIRED"
    )
    return result, ok


def main() -> int:
    try:
        result, ok = inspect_now()
    except Exception:
        # Avoid printing any raw Docker object or sensitive exception string.
        print("PLE_POSTCHECK=INCONCLUSIVE_READ_ONLY")
        print("DOCKER_MUTATION=NONE")
        return 2
    for key, value in result.items():
        print(f"PLE_POSTCHECK_{key.upper()}={value}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
