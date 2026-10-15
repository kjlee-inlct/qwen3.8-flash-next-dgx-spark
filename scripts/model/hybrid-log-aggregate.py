#!/usr/bin/env python3
"""Read-only Git-safe aggregate of checked Hybrid research logs; no raw log lines."""
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/model/hybrid-archive-git-summary.py"
spec = importlib.util.spec_from_file_location("hybrid_archive_summary", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

PATTERNS = {
    "traceback_markers": re.compile(rb"Traceback \(most recent call last\):"),
    "oom_markers": re.compile(rb"(?i)out.of.memory|CUDA out of memory|OOMKilled"),
    "keyboard_interrupt_markers": re.compile(rb"KeyboardInterrupt"),
    "safetensors_markers": re.compile(rb"(?i)safetensors"),
    "model_loading_markers": re.compile(rb"(?i)loading model weights|loading safetensors"),
}
MAX_BYTES = 16 * 1024 * 1024


def aggregate(root: Path):
    checked = module.summarize(root)
    results = []
    for cid in checked["container_ids"]:
        path = root / (cid + ".log")
        if path.stat().st_size > MAX_BYTES:
            raise ValueError("oversize archived log")
        payload = path.read_bytes()
        record = {"id": cid, "log_sha256": module.sha256(path),
                  "log_bytes": len(payload)}
        record.update({name: len(pattern.findall(payload))
                       for name, pattern in PATTERNS.items()})
        results.append(record)
    return {"schema_version": 1, "source_archive_manifest_sha256": checked["sha256_manifest"],
            "record_type": "hybrid_docker_log_aggregate",
            "containers": results, "raw_lines_in_output": False,
            "marker_counts_are_not_error_diagnoses": True,
            "docker_delete_performed": False, "model_delete_performed": False}


def main():
    if len(sys.argv) != 1:
        print("usage: python3 scripts/model/hybrid-log-aggregate.py", file=sys.stderr)
        return 2
    try:
        print(json.dumps(aggregate(module.ARCHIVE), sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as err:
        print("HYBRID_LOG_AGGREGATE=BLOCKED_" + type(err).__name__, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
