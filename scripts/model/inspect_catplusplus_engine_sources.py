#!/usr/bin/env python3
"""Pinned metadata-only vLLM versus SGLang source inventory; never fetch blobs.

ONLY Hub tree JSON under the fixed extra/packages subtree. This cannot prove
that bundled code handles MXFP8 fused qkvz or file-backed FP8 PLE. Do not
run on the DGX while mazinb's large checkpoint restore is active.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import re
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

MODEL = "catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed"
REVISION = "3251fd8afbd08f76368a9bfa71132d9aef364813"
SUBTREE = "extra/packages"
API_PATH = f"/api/models/{MODEL}/tree/{REVISION}/{SUBTREE}"
ROOT_URL = "https://huggingface.co" + API_PATH
BASE_QUERY = "recursive=true&expand=false&limit=1000"
MAX_PAGE_BYTES = 3 * 1024 * 1024
MAX_PAGES = 64
MAX_ITEMS = 64000
MAX_OFFLINE_BYTES = 1024 * 1024
PATH_PATTERN = re.compile(r"^[A-Za-z0-9_./+-]+$")
SCRIPT_CLASSES = ("vllm", "sglang")


class EngineMetadataBlocked(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EngineMetadataBlocked("REDIRECT_REFUSED")


def check_url(url: str) -> None:
    """No external host/repo/revision, path traversal or arbitrary endpoints."""
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "huggingface.co"
            or parsed.path != API_PATH or parsed.fragment or parsed.username):
        raise EngineMetadataBlocked("TREE_PAGINATION_SCOPE_DRIFT")
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if not query.keys() <= {"recursive", "expand", "limit", "cursor"}:
        raise EngineMetadataBlocked("TREE_UNEXPECTED_QUERY")
    for key, val in (("recursive", "true"), ("expand", "false"), ("limit", "1000")):
        if query.get(key) != [val]:
            raise EngineMetadataBlocked("TREE_REQUIRED_QUERY_DRIFT")
    if "cursor" in query:
        cursors = query["cursor"]
        if len(cursors) != 1 or not cursors[0] or len(cursors[0]) > 4096:
            raise EngineMetadataBlocked("TREE_CURSOR_UNTRUSTED")


def _next(link: str) -> str | None:
    links = re.findall(r'<([^>]+)>;\s*rel="([^"]+)"', link)
    matches = [url for url, relationship in links if relationship == "next"]
    if len(matches) > 1:
        raise EngineMetadataBlocked("TREE_MULTIPLE_NEXT_LINKS")
    return matches[0] if matches else None


def get_page(url: str) -> tuple[list[dict], str | None]:
    check_url(url)
    handler = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(
        url, headers={"Accept": "application/json",
                      "User-Agent": "qwen38-spark-pinned-engine-tree/1"},
        method="GET")
    try:
        with handler.open(request, timeout=30) as response:
            if response.status != 200:
                raise EngineMetadataBlocked("TREE_HTTP_NOT_200")
            length = response.headers.get("Content-Length")
            if length is not None and int(length) > MAX_PAGE_BYTES:
                raise EngineMetadataBlocked("TREE_PAGE_CONTENT_LENGTH_OVERSIZED")
            data = response.read(MAX_PAGE_BYTES + 1)
            link = response.headers.get("Link", "")
    except urllib.error.HTTPError as exc:
        raise EngineMetadataBlocked("TREE_HTTP_" + str(exc.code)) from exc
    if not data or len(data) > MAX_PAGE_BYTES:
        raise EngineMetadataBlocked("TREE_PAGE_EMPTY_OR_OVERSIZED")
    try:
        items = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise EngineMetadataBlocked("TREE_JSON_INVALID") from exc
    if not isinstance(items, list) or not items or len(items) > 1000:
        raise EngineMetadataBlocked("TREE_PAGE_SHAPE_INVALID")
    next_url = _next(link)
    if next_url:
        check_url(next_url)
    return items, next_url


def tree() -> list[dict]:
    url = ROOT_URL + "?" + BASE_QUERY
    seen_urls: set[str] = set()
    paths: set[str] = set()
    all_items: list[dict] = []
    for _ in range(MAX_PAGES):
        if url in seen_urls:
            raise EngineMetadataBlocked("TREE_PAGINATION_CYCLE")
        seen_urls.add(url)
        batch, next_url = get_page(url)
        for row in batch:
            if not isinstance(row, dict):
                raise EngineMetadataBlocked("TREE_ROW_NOT_OBJECT")
            name = row.get("path")
            if (not isinstance(name, str)
                    or not name.startswith(SUBTREE + "/")
                    or len(name) > 1024 or not PATH_PATTERN.fullmatch(name)
                    or ".." in Path(name).parts or name in paths):
                raise EngineMetadataBlocked("TREE_PATH_INVALID_OR_DUPLICATE")
            paths.add(name)
        all_items.extend(batch)
        if len(all_items) > MAX_ITEMS:
            raise EngineMetadataBlocked("TREE_ITEM_LIMIT")
        if next_url is None:
            return all_items
        url = next_url
    raise EngineMetadataBlocked("TREE_PAGE_LIMIT_REACHED")


def audit(rows: list[dict]) -> dict:
    seen = set()
    counts = Counter()
    sizes = Counter()
    bundle_names = {"vllm": "vllm-qwen4_exp_sm110.bundle",
                    "sglang": "sglang-qwen4_exp_sm110.bundle"}
    bundles = {key: False for key in SCRIPT_CLASSES}
    source_candidates = {key: [] for key in SCRIPT_CLASSES}
    for obj in rows:
        if not isinstance(obj, dict):
            raise EngineMetadataBlocked("INVALID_ROW")
        path = obj.get("path")
        kind = obj.get("type")
        if (not isinstance(path, str) or
                not path.startswith(SUBTREE + "/") or
                len(path) > 1024 or not PATH_PATTERN.fullmatch(path)
                or ".." in Path(path).parts or path in seen):
            raise EngineMetadataBlocked("PATH_UNSAFE_OR_DUPLICATED")
        seen.add(path)
        if kind not in ("file", "directory"):
            raise EngineMetadataBlocked("INVALID_TREE_ENTRY_TYPE")
        if kind == "directory":
            continue
        sz = obj.get("size", obj.get("lfs", {}).get("size")
                     if isinstance(obj.get("lfs"), dict) else None)
        if sz is not None and (not isinstance(sz, int) or isinstance(sz, bool) or sz < 0):
            raise EngineMetadataBlocked("INVALID_FILE_SIZE")
        # Files from other package families are never conflated with vllm/sglang.
        parts = path.split("/")
        for engine in SCRIPT_CLASSES:
            if path.endswith("/" + bundle_names[engine]):
                bundles[engine] = True
                counts[engine + "_bundle"] += 1
            # A similarly named directory is not proof of executable functionality.
            if parts[2:3] == [engine]:
                counts[engine + "_files"] += 1
                if sz is not None:
                    sizes[engine] += sz
                if (path.endswith(".py") and len(source_candidates[engine]) < 8):
                    source_candidates[engine].append(path)
    return {
        "checkpoint": MODEL,
        "revision": REVISION,
        "inventory_scope": "PINNED_EXTRA_PACKAGES_METADATA_ONLY",
        "files_total": sum(obj["type"] == "file" for obj in rows),
        "vllm_files": counts["vllm_files"],
        "sglang_files": counts["sglang_files"],
        "vllm_bundle_file_claim_matched": bundles["vllm"],
        "sglang_bundle_file_claim_matched": bundles["sglang"],
        "vllm_known_subtree_size_bytes": sizes["vllm"],
        "sglang_known_subtree_size_bytes": sizes["sglang"],
        "vllm_python_file_examples": sorted(source_candidates["vllm"]),
        "sglang_python_file_examples": sorted(source_candidates["sglang"]),
        "content_integrity": "NOT_READ_OR_HASHED",
        "engine_impl": "NOT_AUDITED",
        "mx_qkvz_scale_consumed": "NOT_ATTESTED",
        "nvfp4_experts": "NOT_ATTESTED",
        "fp8_ple_offload": "NOT_ATTESTED",
        "gb10_sm121": "NOT_ATTESTED",
        "checkpoint_download": False,
        "docker_or_gpu": False,
        "engine_preference": "VLLM_FIRST_TO_COMPARE_NOT_QUALIFIED",
        "live_admission": "BLOCKED"
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inventory",))
    parser.add_argument("--offline-json", type=Path)
    args = parser.parse_args()
    try:
        if args.offline_json:
            if (args.offline_json.is_symlink() or not args.offline_json.is_file()
                    or args.offline_json.stat().st_size > MAX_OFFLINE_BYTES):
                raise EngineMetadataBlocked("OFFLINE_FIXTURE_UNSAFE")
            rows = json.loads(args.offline_json.read_text(encoding="utf-8"))
            if not isinstance(rows, list):
                raise EngineMetadataBlocked("OFFLINE_ROWS_NOT_LIST")
        else:
            rows = tree()
        report = audit(rows)
        for key, value in report.items():
            if key.endswith("_examples"):
                # Bound output to a small, source-path-only sample, not 1000s of paths.
                print("CATPLUSPLUS_ENGINES_" + key.upper() + "=" +
                      json.dumps(value, ensure_ascii=True))
            else:
                print("CATPLUSPLUS_ENGINES_" + key.upper() + "=" + str(value))
        print("CATPLUSPLUS_ENGINES_SOURCE_CONTENT=NOT_READ")
        print("CATPLUSPLUS_ENGINES_LIVE_GPU_BENCH_ADMISSION=BLOCKED")
        return 0
    except (EngineMetadataBlocked, OSError, ValueError, UnicodeError) as exc:
        print("CATPLUSPLUS_ENGINES_INVENTORY=BLOCKED_" + str(exc),
              file=sys.stderr)
        print("CATPLUSPLUS_ENGINES_DOCKER_GPU_WEIGHTS=NOT_PERFORMED")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
