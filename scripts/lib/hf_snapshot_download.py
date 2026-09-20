#!/usr/bin/env python3
"""Download a selected set of Hugging Face repo files into a local directory."""

from __future__ import annotations

import os
import pathlib
import sys

from huggingface_hub import snapshot_download


def main() -> int:
    if len(sys.argv) != 5:
        print(
            f"usage: {sys.argv[0]} REPO REVISION DEST MISSING_LIST",
            file=sys.stderr,
        )
        return 2

    repo, revision, dest, missing_list = sys.argv[1:]
    patterns = [
        line.strip()
        for line in pathlib.Path(missing_list).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not patterns:
        print("No missing files; nothing to download.")
        return 0

    workers = int(os.environ.get("HF_DOWNLOAD_MAX_WORKERS", "8"))
    token = os.environ.get("HF_TOKEN") or None
    print(
        f"snapshot_download: repo={repo} revision={revision} "
        f"files={len(patterns)} workers={workers} dest={dest}",
        flush=True,
    )
    try:
        import hf_xet  # noqa: F401
    except ImportError:
        print("hf_xet: unavailable in downloader image", flush=True)
    else:
        print(
            "hf_xet: available"
            + (
                " (high-performance mode)"
                if os.environ.get("HF_XET_HIGH_PERFORMANCE") == "1"
                else ""
            ),
            flush=True,
        )

    snapshot_download(
        repo_id=repo,
        revision=revision,
        token=token,
        local_dir=dest,
        allow_patterns=patterns,
        max_workers=workers,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
