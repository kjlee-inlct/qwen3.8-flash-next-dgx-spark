#!/usr/bin/env python3
"""Read-only source attestation from an EXISTING managed Docker container.

Uses ONLY Docker image/container inspect, docker cp for unmounted files,
and bounded read-only host-file reads for exactly matching existing bind
mounts. Docker cp does not reliably access user mounts, so host bind contents
are examined separately with no-follow safeguards and explicit provenance.
Never creates/starts/executes a container, builds an image, or touches GPU,
weights, services, host tuning or protected evidence. If identity/provenance
is ambiguous or inaccessible, source remains NOT_CAPTURED (fail closed).
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import os
from pathlib import PurePosixPath
import re
import stat
import subprocess
import sys
import tarfile

IMAGE_TAG = "vllm-skinny-tp1:v1"
MANAGED_CONTAINER = "qwen38-flash-next"
MAX_RESPONSE = 1024 * 1024
MAX_SOURCE = 512 * 1024
IMAGE_ID = re.compile(r"sha256:[a-f0-9]{64}\Z")
SOURCE_RELATIVE = "vllm/models/qwen3_8_flash_next/nvidia/ple_layer.py"
PATHS = tuple(
    f"/usr/local/lib/python{py}/{kind}/{SOURCE_RELATIVE}"
    for py in ("3.12", "3.11", "3.13", "3.10", "3.14", "3.15")
    for kind in ("dist-packages", "site-packages")
)


# Present in the pinned skinny-GEMM Dockerfile's build assertion.
# Its absence is NOT a proof that PLE code is missing; this is a layout
# diagnostic only and never feeds loader/install admission decisions.
SKINNY_GEMM_RELATIVE = "vllm/models/qwen3_8_flash_next/nvidia/low_latency_gemm.py"


def _bounded_tar_has_one_file(raw: bytes, name: str) -> bool:
    try:
        if len(raw) > MAX_RESPONSE:
            return False
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
            members = archive.getmembers()
            return (len(members) == 1 and members[0].isfile()
                    and members[0].size <= MAX_SOURCE
                    and members[0].name.lstrip("./") == name)
    except (tarfile.TarError, OSError):
        return False


def _count_failure(kinds: dict[str, int], exc: AttestationError) -> None:
    reason = exc.reason if isinstance(exc, DockerCopyError) else "COPY_FAILED_UNCLASSIFIED"
    kinds[reason] = kinds.get(reason, 0) + 1


def failure_summary(kinds: dict[str, int]) -> str:
    """Machine-readable category counts only; never output raw Docker errors."""
    return ",".join(f"{reason}:{count}" for reason, count in sorted(kinds.items())) or "NONE"


def probe_copy_transport() -> str:
    """Small generic regular file; distinguishes Docker-copy transport from PLE layout.

    /etc/group is conventional non-model metadata and is NOT copied to disk
    or printed, only one small TAR header is inspected.
    """
    try:
        raw = docker_read("cp", f"{MANAGED_CONTAINER}:/etc/group", "-")
    except DockerCopyError as exc:
        return exc.reason
    except AttestationError:
        return "COPY_FAILED_UNCLASSIFIED"
    if _bounded_tar_has_one_file(raw, "group"):
        return "SMALL_REGULAR_TAR_READABLE"
    return "COPY_TAR_INVALID_OR_UNEXPECTED"


def probe_layout(failures: dict[str, int] | None = None) -> tuple[str, str]:
    """Bounded, explicit Docker-copy checks; no listing, exec or filesystem walk."""
    for path in PATHS:
        reference = path.replace(SOURCE_RELATIVE, SKINNY_GEMM_RELATIVE)
        try:
            raw = docker_read("cp", f"{MANAGED_CONTAINER}:{reference}", "-")
        except AttestationError as exc:
            if failures is not None:
                _count_failure(failures, exc)
            continue
        if _bounded_tar_has_one_file(raw, "low_latency_gemm.py"):
            return "SKINNY_GEMM_REFERENCE_READABLE", reference
        if failures is not None:
            failures["COPY_TAR_INVALID_OR_UNEXPECTED"] = (
                failures.get("COPY_TAR_INVALID_OR_UNEXPECTED", 0) + 1
            )
    return "SKINNY_GEMM_REFERENCE_UNAVAILABLE", "NOT_CAPTURED"


class AttestationError(ValueError):
    """Image identity, read-only extraction or source evidence unqualified."""


class DockerCopyError(AttestationError):
    """Typed, non-sensitive Docker copy outcome. Never show raw Docker stderr."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__("Docker copy unavailable: " + reason)


def classify_copy_failure(raw: bytes) -> str:
    """Classify bounded stderr without emitting paths, mounts, or credentials."""
    text = raw[:4096].lower()
    if any(item in text for item in (
        b"permission denied", b"access denied",
    )):
        return "PERMISSION_DENIED"
    if any(item in text for item in (
        b"cannot connect to the docker daemon",
        b"is the docker daemon running",
        b"error during connect",
    )):
        return "DAEMON_UNAVAILABLE"
    if any(item in text for item in (
        b"no such file or directory", b"could not find the file",
        b"not found in container", b"file does not exist",
    )):
        return "SOURCE_PATH_NOT_FOUND"
    if b"not a directory" in text:
        return "PARENT_NOT_DIRECTORY"
    return "COPY_FAILED_UNCLASSIFIED"


def docker_read(*args: str) -> bytes:
    # Deliberate allowlist: do not add 'run', 'create', 'exec', 'start',
    # 'pull', 'save', 'rm' or service operations here.
    permitted = (
        args[:2] in (("image", "inspect"), ("container", "inspect"))
        and len(args) == 3
    ) or (args[:1] == ("cp",) and len(args) == 3 and args[-1] == "-"
          and args[1].startswith(MANAGED_CONTAINER + ":"))
    if not permitted:
        raise AttestationError("Docker command outside read-only allowlist")
    try:
        response = subprocess.run(
            ["docker", *args], capture_output=True, timeout=15, check=False
        )
    except subprocess.TimeoutExpired as exc:
        if args[0] == "cp":
            raise DockerCopyError("COPY_TIMEOUT") from exc
        raise AttestationError("Docker inspection timed out") from exc
    except OSError as exc:
        if args[0] == "cp":
            raise DockerCopyError("CLIENT_UNAVAILABLE") from exc
        raise AttestationError("Docker read-only command unavailable") from exc
    if response.returncode != 0:
        if args[0] == "cp":
            raise DockerCopyError(classify_copy_failure(response.stderr))
        raise AttestationError("Docker metadata or source unavailable")
    if len(response.stdout) > MAX_RESPONSE:
        if args[0] == "cp":
            raise DockerCopyError("COPY_OUTPUT_OVER_LIMIT")
        raise AttestationError("Docker inspection exceeds bounded output")
    return response.stdout


def one_json(raw: bytes, purpose: str) -> dict:
    try:
        decoded = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise AttestationError(f"Invalid {purpose} JSON") from exc
    if not isinstance(decoded, list) or len(decoded) != 1 or not isinstance(decoded[0], dict):
        raise AttestationError(f"Ambiguous {purpose} identity")
    return decoded[0]


def validate_identity(image: dict, container: dict) -> dict[str, str]:
    iid, cid = image.get("Id"), container.get("Id")
    if not isinstance(iid, str) or not IMAGE_ID.fullmatch(iid):
        raise AttestationError("Invalid local image SHA256")
    if not isinstance(cid, str) or not re.fullmatch(r"[a-f0-9]{64}", cid):
        raise AttestationError("Invalid existing container ID")
    if container.get("Name") != "/" + MANAGED_CONTAINER:
        raise AttestationError("Docker object is not the exact managed container")
    if container.get("Image") != iid or (container.get("Config") or {}).get("Image") != IMAGE_TAG:
        raise AttestationError("Existing managed container/image tag differs from inspected image")
    if not isinstance(container.get("Mounts"), list):
        raise AttestationError("Managed container mount inventory unavailable")
    if not all(isinstance(entry, dict) for entry in container["Mounts"]):
        raise AttestationError("Invalid managed container mount records")
    return {"image_tag": IMAGE_TAG, "image_id": iid, "managed_container_id": cid}


def covering_mounts(container: dict, target: str) -> list[dict]:
    """Select only mounts shadowing THIS source path, never unrelated vLLM files."""
    matches = []
    for item in container["Mounts"]:
        dest = item.get("Destination")
        if not isinstance(dest, str):
            raise AttestationError("Invalid Docker mount destination")
        if not dest.startswith("/") or ".." in PurePosixPath(dest).parts:
            raise AttestationError("Unsafe Docker mount destination")
        dest = dest.rstrip("/") or "/"
        if target == dest or target.startswith(dest + "/"):
            matches.append(item)
    # Docker has a longest-prefix mount resolution rule; reject potentially
    # ambiguous nested or duplicate overlays rather than silently guessing.
    if len(matches) > 1:
        raise AttestationError("Overlapping Docker bind mounts affect PLE source")
    return matches


def host_bind_target(mount: dict, target: str) -> str:
    """Resolve an exact Docker bind mapping lexically, without symlink following."""
    dest, src = mount.get("Destination"), mount.get("Source")
    if mount.get("Type") != "bind":
        raise AttestationError("PLE source is covered by a non-bind mount")
    if not isinstance(src, str) or not src.startswith("/"):
        raise AttestationError("Bind mount source unavailable")
    if ".." in PurePosixPath(src).parts or not isinstance(dest, str):
        raise AttestationError("Unsafe bind mount mapping")
    if target != dest and not target.startswith(dest.rstrip("/") + "/"):
        raise AttestationError("Bind mount does not map PLE source")
    relative = target[len(dest.rstrip("/")):].lstrip("/")
    return src.rstrip("/") + ("/" + relative if relative else "")


def read_host_source_nofollow(path: str) -> str:
    """Open every path component with O_NOFOLLOW; bound bytes and verify stable."""
    parts = PurePosixPath(path).parts
    if not path.startswith("/") or ".." in parts or not parts:
        raise AttestationError("Unsafe bind source path")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = None
    try:
        fd = os.open("/", flags | os.O_DIRECTORY)
        for i, name in enumerate(parts[1:]):
            new_fd = os.open(
                name, flags | (os.O_DIRECTORY if i < len(parts) - 2 else 0),
                dir_fd=fd,
            )
            os.close(fd)
            fd = new_fd
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_SOURCE:
            raise AttestationError("Mounted PLE source is not a bounded regular file")
        raw = bytearray()
        while len(raw) <= MAX_SOURCE:
            piece = os.read(fd, min(65536, MAX_SOURCE + 1 - len(raw)))
            if not piece:
                break
            raw.extend(piece)
        after = os.fstat(fd)
        if (len(raw) != before.st_size or len(raw) > MAX_SOURCE
                or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            raise AttestationError("Mounted PLE source changed during read")
        return raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise AttestationError("Mounted PLE bind source inaccessible or unsafe") from exc
    finally:
        if fd is not None:
            os.close(fd)


def source_from_cp(raw: bytes) -> str:
    if len(raw) > MAX_RESPONSE:
        raise AttestationError("Docker copy stream exceeds source bound")
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
            members = archive.getmembers()
            if len(members) != 1 or not members[0].isfile():
                raise AttestationError("Expected one regular loader source, no links")
            member = members[0]
            if member.name.lstrip("./") != "ple_layer.py" or member.size > MAX_SOURCE:
                raise AttestationError("Docker copy contains unexpected/big source")
            stream = archive.extractfile(member)
            if stream is None:
                raise AttestationError("Cannot read Docker loader source")
            data = stream.read(MAX_SOURCE + 1)
            if len(data) != member.size:
                raise AttestationError("Incomplete loader source from Docker copy")
    except (tarfile.TarError, OSError, UnicodeError) as exc:
        raise AttestationError("Invalid loader source tar stream") from exc
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AttestationError("Loader source is not UTF-8 Python") from exc


def audit_source(source: str) -> dict[str, str]:
    try:
        tree = ast.parse(source, filename="ple_layer.py")
    except SyntaxError as exc:
        raise AttestationError("Extracted loader source has invalid Python syntax") from exc
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    quant = [n for n in funcs if n.name == "_get_ple_embedding_quant_method"]
    fp8cls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef) and n.name == "Qwen3_8FlashNextPLEFp8EmbeddingMethod"
    ]
    if len(quant) != 1 or len(fp8cls) != 1:
        raise AttestationError("Expected PLE quant resolver and FP8 embedding class not both found")
    # Only executable function BODY counts. A ple_embedding_dtype parameter
    # in the signature does not prove dtype-based routing is implemented.
    text = "\n".join(ast.unparse(stmt) for stmt in quant[0].body)
    def returns_fp8(branch: list[ast.stmt]) -> bool:
        return any(
            isinstance(node, ast.Return)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "Qwen3_8FlashNextPLEFp8EmbeddingMethod"
            for stmt in branch for node in ast.walk(stmt)
        )

    def guards_fp8_on(if_node: ast.If, marker: str) -> bool:
        # Enforce an actual IF condition *and* an FP8-method return.
        # Merely mentioning dtype/override in a docstring or unused argument
        # must never be counted as implementation evidence.
        test = if_node.test
        if marker == "PLE_QUANT_OVERRIDE":
            has_marker = any(
                isinstance(node, ast.Constant) and node.value == marker
                for node in ast.walk(test)
            )
        else:
            has_marker = any(
                isinstance(node, ast.Name) and node.id == marker
                for node in ast.walk(test)
            )
        return has_marker and returns_fp8(if_node.body)

    branches = [node for node in ast.walk(quant[0]) if isinstance(node, ast.If)]
    if any(guards_fp8_on(node, "PLE_QUANT_OVERRIDE") for node in branches):
        route = "EXPLICIT_OVERRIDE_SOURCE_PRESENT"
    elif any(guards_fp8_on(node, "ple_embedding_dtype") for node in branches):
        route = "DTYPE_ROUTING_SOURCE_PRESENT"
    elif "isinstance(quant_config, Fp8Config)" in text and returns_fp8(quant[0].body):
        route = "NATIVE_FP8_CONFIG_ONLY_SOURCE"
    else:
        route = "UNKNOWN_STATIC_DISPATCH"
    methods = {n.name: n for n in fp8cls[0].body if isinstance(n, ast.FunctionDef)}
    create_text = ast.unparse(methods["create_weights"]) if "create_weights" in methods else ""
    scale_registered = (
        "register_parameter('weight_scale'" in create_text or
        'register_parameter("weight_scale"' in create_text
    )
    scale_registered = scale_registered and "torch.bfloat16" in create_text
    dequant = [n for n in funcs if n.name == "_dequantize_embeddings"]
    # This is a source signature, NOT a guarantee of runtime entry/scale loading.
    dequant_code = "\n".join(ast.unparse(n) for n in dequant)
    scale_applied = any(
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Mult)
        and any(isinstance(part, ast.Name) and part.id == "weight_scale"
                for part in ast.walk(node))
        for fun in dequant for node in ast.walk(fun)
    )
    return {
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "fp8_ple_selection_source": route,
        "bf16_global_scale_registration_source": "PRESENT" if scale_registered else "NOT_PROVEN",
        "fp8_scale_multiply_source": "PRESENT" if scale_applied else "NOT_PROVEN",
        "source_audit": "STATIC_ONLY_NOT_EXECUTION",
        "lychee888_tp1_loader": "NOT_QUALIFIED",
    }


def inspect_existing(diagnostics: dict[str, str] | None = None) -> dict[str, str]:
    image = one_json(docker_read("image", "inspect", IMAGE_TAG), "image")
    container = one_json(docker_read("container", "inspect", MANAGED_CONTAINER), "container")
    result = validate_identity(image, container)
    if diagnostics is not None:
        diagnostics["image_id"] = result["image_id"]
        diagnostics["managed_container_id"] = result["managed_container_id"]
    # A bound PLE module obscures the image-layer file. Its host file, not
    # docker cp's view of the stopped container, is the effective source.
    mapped = [
        (path, matches[0])
        for path in PATHS
        if (matches := covering_mounts(container, path))
    ]
    if mapped:
        if len(mapped) != 1:
            raise AttestationError("Ambiguous multiple Python PLE mount locations")
        path, mount = mapped[0]
        host_source = host_bind_target(mount, path)
        result["source_location_in_existing_container"] = path
        result["source_origin"] = "HOST_BIND_MOUNT_FILE_NOT_IMAGE_LAYER"
        result["source_mount_destination"] = mount["Destination"]
        result["source_mount_mode"] = "rw" if mount.get("RW") else "ro_or_unknown"
        result.update(audit_source(read_host_source_nofollow(host_source)))
        return result
    ple_failures: dict[str, int] = {}
    for path in PATHS:
        try:
            raw = docker_read("cp", f"{MANAGED_CONTAINER}:{path}", "-")
        except AttestationError as exc:
            _count_failure(ple_failures, exc)
            continue
        result["source_location_in_existing_container"] = path
        result["source_origin"] = "EXISTING_CONTAINER_FILESYSTEM_NOT_PROVEN_RUNTIME"
        result.update(audit_source(source_from_cp(raw)))
        return result
    if diagnostics is not None:
        reference_failures: dict[str, int] = {}
        state, reference = probe_layout(reference_failures)
        diagnostics["ple_candidates_checked"] = str(len(PATHS))
        diagnostics["docker_cp_ple_failure_kinds"] = failure_summary(ple_failures)
        diagnostics["docker_cp_reference_state"] = state
        diagnostics["docker_cp_reference_failure_kinds"] = failure_summary(reference_failures)
        diagnostics["docker_cp_reference_path"] = reference
        diagnostics["docker_cp_small_file_state"] = probe_copy_transport()
        diagnostics["ple_source_file"] = "NOT_CAPTURED"
    raise AttestationError("No known PLE loader path in existing matching container")


def main() -> int:
    diagnostics: dict[str, str] = {}
    try:
        result = inspect_existing(diagnostics)
    except AttestationError as exc:
        # Only already validated resource identifiers and our fixed probe
        # reference paths are emitted. No environment secrets, bind Source
        # paths, model data, or live container stdout is exposed.
        for key, value in diagnostics.items():
            print(f"PLE_DIAGNOSTIC_{key.upper()}={value}")
        print(f"PLE_IMAGE_AUDIT=INCONCLUSIVE: {exc}", file=sys.stderr)
        print("DOCKER_MUTATION=NONE")
        print("GPU_RUN=NOT_PERFORMED")
        return 2
    for key, value in result.items():
        print(f"{key}={value}")
    print("DOCKER_MUTATION=NONE")
    print("GPU_RUN=NOT_PERFORMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
