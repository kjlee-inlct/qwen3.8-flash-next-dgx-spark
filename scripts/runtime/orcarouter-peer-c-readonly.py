#!/usr/bin/env python3
"""Read-only admission for a proposed *separate* official ARM64 OrcaRouter C.

No Docker pull/create/start/exec/copy/stop/rm, no GPU, no weights,
no model/API requests and no host/file writes. This is not a live launcher.
Do not confuse the registry manifest digest with a local image config ID.
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import shutil
import subprocess

TAG = "vllm/vllm-openai:qwen38-flash-next-arm64-cu130"
DIGEST = "sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e"
PINNED = "vllm/vllm-openai@" + DIGEST
# First physically attested after the approved 2026-10-18 pull.
EXPECTED_IMAGE_ID = "sha256:d464f3b466fa9c45ddbff8a812e80564503b6879a9fd95c1a47514f3f0df5a4a"
# Exact physical guard identities from before/after pull. Do not reinterpret
# "stopped" alone as evidence of unchanged protected resources.
PROTECTED_IDENTITIES = {
    "qwen38-flash-next": (
        "f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24",
        "sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4",
    ),
    "qwen38-ab-legacy": (
        "57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56",
        "sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4",
    ),
    "qwen38-ab-v029": (
        "13abbb81ca92cbf2f8256e96941a19102ce809ff1c9364ce6932b44a88ebf6a1",
        "sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734",
    ),
}
PROTECTED = tuple(PROTECTED_IDENTITIES)
ORCAROUTER_MODEL = "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"


def command(*args: str) -> tuple[int, str]:
    try:
        result = subprocess.run(args, text=True, capture_output=True, check=False,
                                timeout=12)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return 127, ""
    return result.returncode, result.stdout


def metadata(name: str, *, image: bool) -> dict | None:
    args = ("docker", "image", "inspect") if image else ("docker", "container", "inspect")
    rc, stdout = command(*args, "--format", "{{json .}}", name)
    if rc != 0:
        return None
    try:
        obj = json.loads(stdout)
        return obj if isinstance(obj, dict) else None
    except (ValueError, TypeError):
        return None


def image_receipt() -> str:
    exact = metadata(PINNED, image=True)
    tagged = metadata(TAG, image=True)
    if exact is None and tagged is None:
        return "ABSENT_EXACT_AND_TAG"
    for item in (exact, tagged):
        if item is None:
            continue
        if item.get("Os") != "linux" or item.get("Architecture") != "arm64":
            return "WRONG_PLATFORM"
        digests = item.get("RepoDigests")
        if not isinstance(digests, list) or PINNED not in digests:
            return "DIGEST_NOT_ATTESTED"
        if item.get("Id") != EXPECTED_IMAGE_ID:
            return "IMAGE_CONFIG_ID_MISMATCH"
    if exact is not None and tagged is not None and exact.get("Id") != tagged.get("Id"):
        return "TAG_ID_DIFFERS_FROM_PINNED"
    return "PINNED_MATCH" if exact is not None else "TAG_MATCH_PINNED_REPODIGEST"


def image_runtime_receipt() -> str:
    """Verify OCI entrypoint shape; do not confuse this with CLI/wheel proof."""
    image = metadata(PINNED, image=True)
    if image is None:
        return "PINNED_IMAGE_NOT_INSPECTABLE"
    config = image.get("Config")
    if not isinstance(config, dict):
        return "IMAGE_CONFIG_MISSING"
    if config.get("Entrypoint") != ["vllm", "serve"]:
        return "ENTRYPOINT_MISMATCH"
    if config.get("Cmd") not in (None, []):
        return "UNEXPECTED_IMAGE_DEFAULT_CMD"
    if config.get("WorkingDir") != "/vllm-workspace":
        return "WORKDIR_MISMATCH"
    values: dict[str, str] = {}
    for entry in config.get("Env") or []:
        if isinstance(entry, str) and "=" in entry:
            key, value = entry.split("=", 1)
            if key in {"CUDA_VERSION", "VLLM_BUILD_COMMIT", "VLLM_IMAGE_TAG"}:
                values[key] = value
    if values.get("CUDA_VERSION") != "13.0.1":
        return "CUDA_VERSION_MISMATCH"
    # This precise image has VLLM_BUILD_COMMIT=unknown. The OCI envelope
    # establishes argv composition only; never certify CLI flags or the wheel.
    return "ENTRYPOINT_SHAPE_MATCH_WHEEL_SOURCE_UNATTESTED"


def protected_receipt() -> str:
    seen = []
    for name in PROTECTED:
        item = metadata(name, image=False)
        if item is None:
            return "PROTECTED_CONTAINER_MISSING_OR_UNINSPECTABLE"
        state = item.get("State")
        if (not isinstance(state, dict) or state.get("Status") != "exited" or
                state.get("Running") is not False):
            return "PROTECTED_CONTAINER_NOT_STOPPED"
        if name == PROTECTED[0] and state.get("OOMKilled") is not False:
            return "MANAGED_OLD_OOM_STATE_NOT_CLEAN"
        cid = item.get("Id")
        expected_id, expected_image_id = PROTECTED_IDENTITIES[name]
        if cid != expected_id or item.get("Image") != expected_image_id:
            return "PROTECTED_ID_OR_IMAGE_DRIFT"
        seen.append(cid)
    if len(set(seen)) != len(seen):
        return "PROTECTED_IDS_NOT_DISTINCT"
    return "THREE_STOPPED_EXISTING_IDS"


def plan(*, operation: str = "PLAN_ONLY_NO_HOST_INSPECTION") -> None:
    print("PEER_C_OPERATION=" + operation)
    print("PEER_C_REGISTRY_TAG=" + TAG)
    print("PEER_C_REGISTRY_MANIFEST_DIGEST=" + DIGEST)
    print("PEER_C_REGISTRY_PLATFORM=linux/arm64")
    print("PEER_C_EXPECTED_IMAGE_ID=" + EXPECTED_IMAGE_ID)
    print("PEER_C_MODEL=" + ORCAROUTER_MODEL)
    print("PEER_C_RUNTIME=OFFICIAL_ARM64_CPU_PLE_CANDIDATE_NOT_VALIDATED")
    print("PEER_C_EXISTING_AB_PRESERVE=MANDATORY")
    print("PEER_C_DESIRED_PORT=127.0.0.1:18891")
    print("PEER_C_KV_START_GIB=16")
    print("PEER_C_MODEL_START=NOT_IMPLEMENTED_OR_AUTHORIZED")
    print("PEER_C_IMAGE_PULL=NO_ACTION_BY_THIS_READ_ONLY_TOOL")
    print("PEER_C_BENCHMARK=NOT_MEASURED")


def preflight() -> int:
    plan(operation="PREFLIGHT_READ_ONLY_HOST_INSPECTION")
    machine = platform.machine().lower()
    host_ok = machine in ("aarch64", "arm64")
    print("PEER_C_HOST_ARCH=" + ("ARM64" if host_ok else "NOT_ARM64"))
    image = image_receipt()
    print("PEER_C_LOCAL_IMAGE=" + image)
    runtime = image_runtime_receipt()
    print("PEER_C_RUNTIME_CONTRACT=" + runtime)
    print("PEER_C_EMBEDDED_VLLM_COMMIT=NOT_ATTESTED_BY_OCI_METADATA")
    protected = protected_receipt()
    print("PEER_C_PROTECTED_OBJECTS=" + protected)
    service_rc, _ = command("systemctl", "is-active", "--quiet",
                            "qwen38-flash-next.service")
    # systemctl is-active --quiet: 3=inactive, 4=unknown/not-found.
    # Unknown is acceptable for a SOURCE-ONLY inventory receipt, but is
    # explicitly *not* evidence a live trial may safely start.
    service_ok = service_rc in (3, 4)
    service_text = {3: "INACTIVE", 4: "UNKNOWN_NOT_LIVE_APPROVED"}.get(
        service_rc, "ACTIVE_OR_UNCLASSIFIED"
    )
    print("PEER_C_MANAGED_SERVICE=" + service_text)
    try:
        free_gib = shutil.disk_usage("/").free // (1024 ** 3)
        print("PEER_C_ROOT_DISK_FREE_GIB=" + str(free_gib))
    except OSError:
        print("PEER_C_ROOT_DISK_FREE_GIB=UNKNOWN")
    if image == "ABSENT_EXACT_AND_TAG":
        print("PEER_C_ADMISSION=BLOCKED_IMAGE_NOT_INSTALLED")
        return 2
    if (not host_ok or image not in ("PINNED_MATCH", "TAG_MATCH_PINNED_REPODIGEST")
            or runtime != "ENTRYPOINT_SHAPE_MATCH_WHEEL_SOURCE_UNATTESTED"
            or protected != "THREE_STOPPED_EXISTING_IDS" or not service_ok):
        print("PEER_C_ADMISSION=BLOCKED_REVIEW")
        return 2
    print("PEER_C_ADMISSION=SOURCE_READ_ONLY_PREFLIGHT_PASS_NOT_LIVE_APPROVAL")
    return 0


def read_meminfo_kib() -> dict[str, int] | None:
    """Read Linux /proc/meminfo; missing or malformed fields fail closed."""
    try:
        lines = Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
        needed = {"MemFree", "MemAvailable", "CmaFree", "SwapFree"}
        values: dict[str, int] = {}
        for line in lines:
            key, sep, rest = line.partition(":")
            if not sep or key not in needed:
                continue
            parts = rest.strip().split()
            if len(parts) != 2 or parts[1] != "kB":
                return None
            values[key] = int(parts[0])
        if keys_missing := needed - values.keys():
            return None
        if any(value < 0 for value in values.values()):
            return None
        return values
    except (OSError, ValueError, UnicodeError):
        return None


def host_check() -> int:
    """Independent, read-only *snapshot*; never a start permission.

    No Docker create/start/run/exec/copy/stop/rm, no service changes,
    no sockets bound, and no file writes. All resource checks must fail
    closed; dynamic results must be rechecked at any future live start.
    """
    print("PEER_C_OPERATION=HOST_CHECK_READ_ONLY")
    rc, output = command("docker", "ps", "--format", "{{json .}}")
    expected = {
        "open-webui": "ghcr.io/open-webui/open-webui:main",
        "portainer": "portainer/portainer-ce:latest",
    }
    docker_state = "UNKNOWN_BLOCKED"
    if rc == 0:
        try:
            rows = [json.loads(line) for line in output.splitlines() if line.strip()]
            if all(isinstance(row, dict) and
                   isinstance(row.get("Names"), str) and
                   isinstance(row.get("Image"), str) for row in rows):
                names = [row["Names"] for row in rows]
                if (len(names) == len(set(names)) and
                    all(expected.get(row["Names"]) == row["Image"] for row in rows)):
                    docker_state = "ONLY_KNOWN_ADMIN_CONTAINERS"
                else:
                    docker_state = "UNEXPECTED_RUNNING_CONTAINER_BLOCKED"
            else:
                docker_state = "INVALID_DOCKER_PS_BLOCKED"
        except (json.JSONDecodeError, TypeError):
            docker_state = "INVALID_DOCKER_PS_BLOCKED"
    print("PEER_C_RUNNING_DOCKER=" + docker_state)

    rc, listeners = command("ss", "-H", "-ltn", "( sport = :18891 )")
    port_state = ("NO_LISTENER_AT_CHECK" if rc == 0 and not listeners.strip()
                  else "LISTENER_OR_UNKNOWN_BLOCKED")
    print("PEER_C_PORT_18891=" + port_state)

    rc, swap_names = command("swapon", "--show=NAME", "--noheadings")
    swap_state = ("PLE_SWAP_ACTIVE" if rc == 0 and
                  "/swap-ple.img" in swap_names.splitlines()
                  else "PLE_SWAP_MISSING_OR_UNKNOWN_BLOCKED")
    print("PEER_C_PLE_SWAP=" + swap_state)

    mem = read_meminfo_kib()
    memory_state = "UNKNOWN_BLOCKED"
    if mem is not None:
        noncma_free = max(0, mem["MemFree"] - mem["CmaFree"])
        noncma_available = max(0, mem["MemAvailable"] - mem["CmaFree"])
        swap_free = mem["SwapFree"]
        print("PEER_C_NONCMA_FREE_KIB=" + str(noncma_free))
        print("PEER_C_NONCMA_AVAILABLE_KIB=" + str(noncma_available))
        print("PEER_C_SWAP_FREE_KIB=" + str(swap_free))
        if (noncma_free >= 2 * 1048576 and
                noncma_available >= 6 * 1048576 and
                swap_free >= 8 * 1048576):
            memory_state = "MINIMUM_STATIC_MARGIN_MET"
        else:
            memory_state = "LOW_MEMORY_OR_SWAP_BLOCKED"
    print("PEER_C_MEMORY_MARGIN=" + memory_state)

    if (docker_state != "ONLY_KNOWN_ADMIN_CONTAINERS"
            or port_state != "NO_LISTENER_AT_CHECK"
            or swap_state != "PLE_SWAP_ACTIVE"
            or memory_state != "MINIMUM_STATIC_MARGIN_MET"):
        print("PEER_C_HOST_CHECK=BLOCKED_REVIEW")
        return 2
    print("PEER_C_HOST_CHECK=PASS_SNAPSHOT_NOT_LIVE_APPROVAL")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "preflight", "host-check"))
    args = parser.parse_args()
    if args.action == "plan":
        plan()
        return 0
    if args.action == "preflight":
        return preflight()
    return host_check()


if __name__ == "__main__":
    raise SystemExit(main())
