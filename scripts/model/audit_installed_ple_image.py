#!/usr/bin/env python3
"""Read-only source attestation from an EXISTING managed Docker container.

Uses ONLY 'docker image inspect', 'docker container inspect' and 'docker cp'.
Never creates/starts/executes a container, builds an image, or touches GPU,
weights, services, host tuning or protected evidence. If the managed container
is absent/mismatched, source remains NOT_CAPTURED (fail closed).
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import re
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
    for py in ("3.12", "3.11", "3.13", "3.10")
    for kind in ("dist-packages", "site-packages")
)


class AttestationError(ValueError):
    """Image identity, read-only extraction or source evidence unqualified."""


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
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AttestationError("Docker read-only command unavailable") from exc
    if response.returncode != 0:
        raise AttestationError("Docker metadata or source unavailable")
    if len(response.stdout) > MAX_RESPONSE:
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
    for entry in container["Mounts"]:
        destination = entry.get("Destination") if isinstance(entry, dict) else None
        if isinstance(destination, str) and (
            destination == "/usr/local/lib" or
            destination.startswith("/usr/local/lib/python") or
            "ple_layer.py" in destination or
            destination.endswith("/vllm")
        ):
            raise AttestationError("Mounted vLLM source could differ from image layer")
    return {"image_tag": IMAGE_TAG, "image_id": iid, "managed_container_id": cid}


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


def inspect_existing() -> dict[str, str]:
    image = one_json(docker_read("image", "inspect", IMAGE_TAG), "image")
    container = one_json(docker_read("container", "inspect", MANAGED_CONTAINER), "container")
    result = validate_identity(image, container)
    for path in PATHS:
        try:
            raw = docker_read("cp", f"{MANAGED_CONTAINER}:{path}", "-")
        except AttestationError:
            continue
        result["source_location_in_existing_container"] = path
        result.update(audit_source(source_from_cp(raw)))
        return result
    raise AttestationError("No known PLE loader path in existing matching container")


def main() -> int:
    try:
        result = inspect_existing()
    except AttestationError as exc:
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
