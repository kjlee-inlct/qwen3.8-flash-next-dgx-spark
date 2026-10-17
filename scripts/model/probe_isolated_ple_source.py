#!/usr/bin/env python3
"""Owner-approved, narrowly scoped source probe using ONE unstarted temporary Docker object.

Research-only, never run/start/exec a container and never change the two
protected existing containers. Default is read-only plan. --execute requires
the exact expected image ID and the literal approval scope; neither is an
authorization to start, rebuild, update the Docker daemon or load a model.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import selectors
import signal
import subprocess
import time

import audit_installed_ple_image as ple

EXPECTED_IMAGE_ID = "sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4"
EXPECTED_IMAGE_SIZE = 20629141958
EXPECTED_MANAGED_ID = "f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24"
EXPECTED_LEGACY_ID = "57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56"
PROBE_LABEL_KEY = "com.qwen38.source-probe"
PROBE_LABEL_VALUE = "ple-read-approved-scope"
APPROVAL_SCOPE = "ONE_UNSTARTED_TEMP_CONTAINER_CREATE_COPY_RM"
MIN_FREE_BYTES = 2 * 1024 * 1024 * 1024
MIN_FREE_INODES = 1024
MAX_SMALL_RESPONSE = ple.MAX_RESPONSE
MAX_DOCKER_META_BYTES = 1024 * 1024
DOCKER_TIMEOUT = 30
HEX64 = re.compile(r"[a-f0-9]{64}\Z")


class ProbeError(Exception):
    """Sanitized error type. Never emit Docker raw stderr or bind source paths."""


class CommandFailed(ProbeError):
    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


def docker(args: list[str], limit: int = MAX_DOCKER_META_BYTES) -> bytes:
    """Execute fixed program with bounded stdout/stderr and per-call deadline.

    Both pipes are consumed incrementally: communicate()/run(capture_output)
    can buffer unlimited tar output before checking its size.
    """
    proc = subprocess.Popen(
        ["docker", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
    )
    data = bytearray()
    errors = bytearray()
    select = selectors.DefaultSelector()
    deadline = time.monotonic() + DOCKER_TIMEOUT
    try:
        for pipe in (proc.stdout, proc.stderr):
            if pipe is None:
                raise ProbeError("Docker pipe unavailable")
            os.set_blocking(pipe.fileno(), False)
            select.register(pipe, selectors.EVENT_READ)
        while select.get_map():
            seconds = deadline - time.monotonic()
            if seconds <= 0:
                raise CommandFailed("DOCKER_TIMEOUT")
            for key, _ in select.select(timeout=min(seconds, 0.5)):
                part = os.read(key.fileobj.fileno(), 65536)
                if not part:
                    select.unregister(key.fileobj)
                    continue
                target = data if key.fileobj is proc.stdout else errors
                target.extend(part)
                if len(data) > limit:
                    raise CommandFailed("DOCKER_STDOUT_BOUNDED_LIMIT")
                if len(errors) > 4096:
                    raise CommandFailed("DOCKER_STDERR_BOUNDED_LIMIT")
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise CommandFailed("DOCKER_TIMEOUT")
        proc.wait(timeout=seconds)
        if proc.returncode:
            if args[:1] == ["cp"]:
                raise CommandFailed(ple.classify_copy_failure(bytes(errors)))
            # For a post-removal missing object, caller must use
            # explicit classification instead of guessing from exit code.
            if args[:2] == ["container", "inspect"] and (
                b"no such object" in errors.lower()
                or b"no such container" in errors.lower()
            ):
                raise CommandFailed("CONTAINER_NOT_FOUND")
            raise CommandFailed("DOCKER_COMMAND_FAILED")
        return bytes(data)
    except subprocess.TimeoutExpired as exc:
        raise CommandFailed("DOCKER_TIMEOUT") from exc
    finally:
        select.close()
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        for pipe in (proc.stdout, proc.stderr):
            if pipe:
                pipe.close()


def exactly_one(value: bytes, name: str) -> dict:
    return ple.one_json(value, name)


def get_preflight() -> tuple[dict, dict, dict]:
    image = exactly_one(
        docker(["image", "inspect", ple.IMAGE_TAG]), "image"
    )
    managed = exactly_one(
        docker(["container", "inspect", ple.MANAGED_CONTAINER]), "managed"
    )
    legacy = exactly_one(
        docker(["container", "inspect", ple.LEGACY_CONTAINER]), "legacy"
    )
    if image.get("Id") != EXPECTED_IMAGE_ID or image.get("Size") != EXPECTED_IMAGE_SIZE:
        raise ProbeError("Installed image SHA256 or size drift")
    if managed.get("Id") != EXPECTED_MANAGED_ID or legacy.get("Id") != EXPECTED_LEGACY_ID:
        raise ProbeError("Protected container ID drift")
    ple.validate_identity(image, managed)
    if (legacy.get("Name") != "/" + ple.LEGACY_CONTAINER
            or legacy.get("Image") != EXPECTED_IMAGE_ID
            or (legacy.get("Config") or {}).get("Image") != ple.IMAGE_TAG):
        raise ProbeError("Historical container image/name drift")
    for obj in (managed, legacy):
        if (obj.get("State") or {}).get("Status") != "exited":
            raise ProbeError("Protected container is no longer stopped")
        if (obj.get("HostConfig") or {}).get("ReadonlyRootfs") is not False:
            raise ProbeError("Protected container rootfs flag drift")
        if ple.model_config_mount_topology(obj) != "MODEL_CONFIG_NESTED_RO_BINDS":
            raise ProbeError("Protected mount topology drift")
    if (image.get("Config") or {}).get("Volumes"):
        raise ProbeError("Image declares volumes; implicit volume side effect possible")
    return image, managed, legacy


def fingerprint_protected(obj: dict) -> str:
    """Compare sensitive metadata privately, not in terminal output."""
    interesting = {
        "Id": obj.get("Id"), "Image": obj.get("Image"),
        "Name": obj.get("Name"), "Mounts": obj.get("Mounts"),
        "State": obj.get("State"), "HostConfig": obj.get("HostConfig"),
    }
    return json.dumps(interesting, sort_keys=True, separators=(",", ":"))


def available_docker_space() -> tuple[int, int]:
    root = docker(["info", "--format", "{{.DockerRootDir}}"], 4096).decode(
        "utf-8", errors="strict"
    ).strip()
    if (not root.startswith("/") or "\n" in root or "\r" in root
            or ".." in Path(root).parts):
        raise ProbeError("Docker storage root metadata unqualified")
    try:
        st = os.statvfs(root)
    except OSError as exc:
        raise ProbeError("Docker storage root free-space check unavailable") from exc
    return st.f_bavail * st.f_frsize, st.f_favail


def verify_temp(info: dict, cid: str, name: str, nonce: str) -> None:
    if not HEX64.fullmatch(cid):
        raise ProbeError("Temporary ID malformed")
    config = info.get("Config")
    labels = config.get("Labels") if isinstance(config, dict) else None
    state = info.get("State")
    hc = info.get("HostConfig")
    if (not isinstance(labels, dict) or not isinstance(state, dict)
            or not isinstance(hc, dict)):
        raise ProbeError("Temporary container inspect metadata incomplete")
    if (cid in (EXPECTED_MANAGED_ID, EXPECTED_LEGACY_ID)
            or info.get("Id") != cid or info.get("Name") != "/" + name
            or info.get("Image") != EXPECTED_IMAGE_ID
            or labels.get(PROBE_LABEL_KEY) != PROBE_LABEL_VALUE
            or labels.get("com.qwen38.source-probe.nonce") != nonce):
        raise ProbeError("Temporary container identity/ownership mismatch")
    if state.get("Status") != "created":
        raise ProbeError("Temporary container no longer in CREATED state")
    policy = hc.get("RestartPolicy")
    if not isinstance(policy, dict):
        raise ProbeError("Temporary restart policy inspect incomplete")
    if (info.get("Mounts") != [] or hc.get("Binds") not in (None, [])
            or hc.get("Privileged") is not False
            or hc.get("NetworkMode") != "none"
            or policy.get("Name") not in ("no", "")
            or hc.get("Devices") not in (None, [])
            or hc.get("Runtime") != "runc"):
        raise ProbeError("Temporary container mount/network/device safety mismatch")


def inspect_temp(cid: str, name: str, nonce: str) -> None:
    value = exactly_one(docker(["container", "inspect", cid]), "temporary")
    verify_temp(value, cid, name, nonce)


def bounded_copy(cid: str, target: str) -> bytes:
    if not HEX64.fullmatch(cid):
        raise ProbeError("Temporary copy requires exact 64-character ID")
    if target != "/etc/group" and target not in ple.PATHS:
        raise ProbeError("Source copy path not allowlisted")
    return docker(["cp", f"{cid}:{target}", "-"], MAX_SMALL_RESPONSE)


def try_probe_source(cid: str) -> tuple[str, dict[str, str]]:
    control = bounded_copy(cid, "/etc/group")
    if not ple._bounded_tar_has_one_file(control, "group"):
        raise ProbeError("Isolated control copy invalid TAR")
    print("PLE_TEMP_COPY_CONTROL=SMALL_REGULAR_TAR_READABLE", flush=True)
    for path in ple.PATHS:
        try:
            raw = bounded_copy(cid, path)
        except CommandFailed as exc:
            if exc.category == "SOURCE_PATH_NOT_FOUND":
                continue
            raise
        source = ple.source_from_cp(raw)
        # Source SHA is recorded only for an actual parsed regular file;
        # AST failure is not conflated with path absence.
        sha = ple.hashlib.sha256(source.encode("utf-8")).hexdigest()
        print(f"PLE_TEMP_SOURCE_PATH={path}", flush=True)
        print(f"PLE_TEMP_SOURCE_SHA256={sha}", flush=True)
        summary = ple.audit_source(source)
        return path, summary
    raise ProbeError("No allowlisted installed PLE source path was readable")


def postcheck_protected(managed: dict, legacy: dict) -> bool:
    try:
        post_m = exactly_one(
            docker(["container", "inspect", EXPECTED_MANAGED_ID]), "managed post"
        )
        post_l = exactly_one(
            docker(["container", "inspect", EXPECTED_LEGACY_ID]), "legacy post"
        )
        post_image = exactly_one(
            docker(["image", "inspect", ple.IMAGE_TAG]), "image post"
        )
        return (
            fingerprint_protected(post_m) == fingerprint_protected(managed)
            and fingerprint_protected(post_l) == fingerprint_protected(legacy)
            and post_image.get("Id") == EXPECTED_IMAGE_ID
            and post_image.get("Size") == EXPECTED_IMAGE_SIZE
        )
    except (ple.AttestationError, ProbeError, OSError, ValueError):
        return False


def execute() -> int:
    image, managed, legacy = get_preflight()
    del image
    free_bytes, free_inodes = available_docker_space()
    print(f"PLE_TEMP_PRE_FREE_BYTES={free_bytes}", flush=True)
    print(f"PLE_TEMP_PRE_FREE_INODES={free_inodes}", flush=True)
    if free_bytes < MIN_FREE_BYTES or free_inodes < MIN_FREE_INODES:
        raise ProbeError("Insufficient Docker storage reserve for temp metadata")
    # Check the original objects again immediately before the sole creation.
    get_preflight()
    nonce = secrets.token_hex(12)
    name = f"qwen38-ple-read-{nonce}"
    cid = None
    copied = False
    cleanup_ok = False
    print(f"PLE_TEMP_PLANNED_NAME={name}", flush=True)
    try:
        raw_id = docker([
            "container", "create", "--name", name,
            "--label", f"{PROBE_LABEL_KEY}={PROBE_LABEL_VALUE}",
            "--label", f"com.qwen38.source-probe.nonce={nonce}",
            "--network", "none", "--restart", "no",
            "--runtime", "runc", "--pull", "never",
            "--entrypoint", "/bin/true",
            EXPECTED_IMAGE_ID,
        ], 256).decode("ascii", errors="strict").strip()
        if not HEX64.fullmatch(raw_id) or raw_id in (
            EXPECTED_MANAGED_ID, EXPECTED_LEGACY_ID
        ):
            raise ProbeError("Created object ID invalid; inspect planned name manually")
        cid = raw_id
        print(f"PLE_TEMP_CREATED_ID={cid}", flush=True)
        inspect_temp(cid, name, nonce)
        print("PLE_TEMP_CREATED_STATE=CREATED_NO_MOUNTS", flush=True)
        _path, summary = try_probe_source(cid)
        copied = True
        for k, v in summary.items():
            print(f"PLE_TEMP_{k.upper()}={v}", flush=True)
    finally:
        if cid is not None:
            try:
                # Identity checked again immediately before the *only* removal.
                inspect_temp(cid, name, nonce)
                docker(["container", "rm", cid], 256)
                try:
                    docker(["container", "inspect", cid], 4096)
                except CommandFailed as exc:
                    if exc.category == "CONTAINER_NOT_FOUND":
                        cleanup_ok = True
                print("PLE_TEMP_CLEANUP=" + (
                    "EXACT_ID_REMOVED_VERIFIED" if cleanup_ok
                    else "UNVERIFIED_LEFT_FOR_REVIEW"
                ), flush=True)
            except (ProbeError, OSError, ValueError) as exc:
                print("PLE_TEMP_CLEANUP=STOP_LEFT_FOR_REVIEW", flush=True)
                print(f"PLE_TEMP_CLEANUP_REASON={type(exc).__name__}", flush=True)
        else:
            print("PLE_TEMP_CLEANUP=NO_CONFIRMED_CREATED_ID_CHECK_PLANNED_NAME", flush=True)
        protected_ok = postcheck_protected(managed, legacy)
        print("PLE_TEMP_PROTECTED_POSTCHECK=" + (
            "MATCH" if protected_ok else "FAIL_REVIEW"
        ), flush=True)
    if not copied or not cleanup_ok or not protected_ok:
        return 2
    print("PLE_TEMP_PROBE=SOURCE_CAPTURED_STATIC_ONLY", flush=True)
    print("PLE_TEMP_LYCHEE888_TP1=NOT_QUALIFIED", flush=True)
    print("GPU_RUN=NOT_PERFORMED", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="create-and-remove one approved unstarted temporary object")
    parser.add_argument("--approved-image-id", default="")
    parser.add_argument("--approved-scope", default="")
    args = parser.parse_args(argv)
    if args.execute and (
        args.approved_image_id != EXPECTED_IMAGE_ID
        or args.approved_scope != APPROVAL_SCOPE
    ):
        print("PLE_TEMP_PROBE=STOP_EXACT_OWNER_SCOPE_REQUIRED")
        return 2
    if not args.execute and (args.approved_image_id or args.approved_scope):
        print("PLE_TEMP_PROBE=STOP_EXECUTION_FLAGS_WITHOUT_EXECUTE")
        return 2
    if not args.execute:
        try:
            image, managed, legacy = get_preflight()
            del image, managed, legacy
            print("PLE_TEMP_PROBE=PLAN_ONLY_PROTECTED_IDENTITIES_MATCH")
            print("PLE_TEMP_CREATE=NOT_PERFORMED")
            print("PLE_TEMP_COPY=NOT_PERFORMED")
            return 0
        except (ProbeError, ple.AttestationError, OSError, ValueError, UnicodeError) as exc:
            print(f"PLE_TEMP_PROBE=STOP_{type(exc).__name__}")
            return 2

    # A termination signal should unwind execute() and its exact-ID cleanup.
    # SIGKILL and power loss cannot be trapped: the preprinted unique name is
    # the recovery handle, never a license for name-wide deletion.
    def stop_on_signal(_signum, _frame):
        raise ProbeError("Operator interruption: exact-ID cleanup required")

    old_sigterm = signal.getsignal(signal.SIGTERM)
    old_sigint = signal.getsignal(signal.SIGINT)
    try:
        signal.signal(signal.SIGTERM, stop_on_signal)
        signal.signal(signal.SIGINT, stop_on_signal)
        try:
            return execute()
        except (ProbeError, ple.AttestationError, OSError, ValueError, UnicodeError) as exc:
            print(f"PLE_TEMP_PROBE=STOP_{type(exc).__name__}")
            print("PLE_TEMP_LYCHEE888_TP1=NOT_QUALIFIED")
            return 2
    finally:
        signal.signal(signal.SIGTERM, old_sigterm)
        signal.signal(signal.SIGINT, old_sigint)


if __name__ == "__main__":
    raise SystemExit(main())
