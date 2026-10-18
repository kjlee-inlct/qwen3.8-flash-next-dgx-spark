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


def plan() -> None:
    print("PEER_C_OPERATION=PLAN_ONLY_NO_HOST_INSPECTION")
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
    plan()
    machine = platform.machine().lower()
    host_ok = machine in ("aarch64", "arm64")
    print("PEER_C_HOST_ARCH=" + ("ARM64" if host_ok else "NOT_ARM64"))
    image = image_receipt()
    print("PEER_C_LOCAL_IMAGE=" + image)
    protected = protected_receipt()
    print("PEER_C_PROTECTED_OBJECTS=" + protected)
    service_rc, _ = command("systemctl", "is-active", "--quiet",
                            "qwen38-flash-next.service")
    service_ok = service_rc in (3, 4)  # inactive or unknown; no start attempted
    print("PEER_C_MANAGED_SERVICE=" + ("INACTIVE_OR_UNKNOWN" if service_ok else
                                      "ACTIVE_OR_UNCLASSIFIED"))
    try:
        free_gib = shutil.disk_usage("/").free // (1024 ** 3)
        print("PEER_C_ROOT_DISK_FREE_GIB=" + str(free_gib))
    except OSError:
        print("PEER_C_ROOT_DISK_FREE_GIB=UNKNOWN")
    if image == "ABSENT_EXACT_AND_TAG":
        print("PEER_C_ADMISSION=BLOCKED_IMAGE_NOT_INSTALLED")
        return 2
    if (not host_ok or image not in ("PINNED_MATCH", "TAG_MATCH_PINNED_REPODIGEST")
            or protected != "THREE_STOPPED_EXISTING_IDS" or not service_ok):
        print("PEER_C_ADMISSION=BLOCKED_REVIEW")
        return 2
    print("PEER_C_ADMISSION=SOURCE_READ_ONLY_PREFLIGHT_PASS_NOT_LIVE_APPROVAL")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "preflight"))
    args = parser.parse_args()
    if args.action == "plan":
        plan()
        return 0
    return preflight()


if __name__ == "__main__":
    raise SystemExit(main())
