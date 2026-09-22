#!/usr/bin/env python3
"""Collect and compare H20 NVFP4 MoE conversion diagnostic records."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PREFIX = "QWEN38_H20_MOE_DIAG "
TENSOR_NAMES = (
    "w13",
    "w13_scale",
    "w13_scale_2",
    "a13_scale",
    "w2",
    "w2_scale",
    "w2_scale_2",
    "a2_scale",
)
COMPARE_FIELDS = (
    "shape",
    "dtype",
    "stride",
    "contiguous",
    "numel",
    "nbytes",
    "hash_scope",
    "sha256",
)


def parse_records(lines: list[str]) -> list[dict]:
    records: list[dict] = []
    for raw in lines:
        pos = raw.find(PREFIX)
        if pos < 0:
            continue
        payload = raw[pos + len(PREFIX) :].strip()
        records.append(json.loads(payload))
    return records


def collect(container: str, output: Path) -> int:
    result = subprocess.run(
        ["docker", "logs", container],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode
    records = parse_records((result.stdout + "\n" + result.stderr).splitlines())
    if not records:
        print(f"ERROR: no {PREFIX.strip()} records found in {container}", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in records),
        encoding="utf-8",
    )
    sources = sorted({str(r.get("source")) for r in records})
    phases = sorted({str(r.get("phase")) for r in records})
    calls = sorted({int(r.get("call_index", -1)) for r in records})
    print(
        f"wrote {len(records)} records to {output} "
        f"sources={sources} phases={phases} calls={calls}"
    )
    return 0


def load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def index_records(records: list[dict]) -> dict[tuple[int, str], dict]:
    indexed: dict[tuple[int, str], dict] = {}
    for record in records:
        key = (int(record["call_index"]), str(record["phase"]))
        if key in indexed:
            raise ValueError(f"duplicate record key {key}")
        indexed[key] = record
    return indexed


def compare(ct_path: Path, modelopt_path: Path, output: Path | None) -> int:
    ct = index_records(load_jsonl(ct_path))
    modelopt = index_records(load_jsonl(modelopt_path))
    common = sorted(set(ct) & set(modelopt))
    only_ct = sorted(set(ct) - set(modelopt))
    only_modelopt = sorted(set(modelopt) - set(ct))

    comparisons: list[dict] = []
    mismatch_count = 0
    first_mismatch: dict | None = None
    for key in common:
        ct_record = ct[key]
        mo_record = modelopt[key]
        tensor_results: dict[str, dict] = {}
        state_result: dict | None = None
        if "tensors" in ct_record or "tensors" in mo_record:
            for name in TENSOR_NAMES:
                left = ct_record.get("tensors", {}).get(name)
                right = mo_record.get("tensors", {}).get(name)
                fields: dict[str, dict] = {}
                equal = (left is None and right is None) or (
                    left is not None and right is not None
                )
                for field in COMPARE_FIELDS:
                    lv = None if left is None else left.get(field)
                    rv = None if right is None else right.get(field)
                    field_equal = lv == rv
                    fields[field] = {
                        "equal": field_equal,
                        "ct": lv,
                        "modelopt": rv,
                    }
                    equal = equal and field_equal
                tensor_results[name] = {"equal": equal, "fields": fields}
                if not equal:
                    mismatch_count += 1
                    if first_mismatch is None:
                        first_mismatch = {
                            "call_index": key[0],
                            "phase": key[1],
                            "tensor": name,
                            "fields": fields,
                        }

        if "state" in ct_record or "state" in mo_record:
            left_state = ct_record.get("state")
            right_state = mo_record.get("state")
            state_equal = left_state == right_state
            state_result = {
                "equal": state_equal,
                "ct": left_state,
                "modelopt": right_state,
            }
            if not state_equal:
                mismatch_count += 1
                if first_mismatch is None:
                    first_mismatch = {
                        "call_index": key[0],
                        "phase": key[1],
                        "state": True,
                        "ct": left_state,
                        "modelopt": right_state,
                    }

        comparisons.append(
            {
                "call_index": key[0],
                "phase": key[1],
                "backend_equal": ct_record.get("backend") == mo_record.get("backend"),
                "use_a16_equal": ct_record.get("use_a16") == mo_record.get("use_a16"),
                "tensors": tensor_results,
                "state": state_result,
            }
        )

    report = {
        "schema": 1,
        "ct_file": str(ct_path),
        "modelopt_file": str(modelopt_path),
        "common_records": len(common),
        "only_ct": only_ct,
        "only_modelopt": only_modelopt,
        "tensor_mismatches": mismatch_count,
        "first_mismatch": first_mismatch,
        "comparisons": comparisons,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote comparison report to {output}")

    print(
        f"common_records={len(common)} tensor_mismatches={mismatch_count} "
        f"only_ct={len(only_ct)} only_modelopt={len(only_modelopt)}"
    )
    if first_mismatch is None:
        print("first_mismatch=none")
    else:
        if first_mismatch.get("state"):
            print(
                "first_mismatch="
                f"call={first_mismatch['call_index']} "
                f"phase={first_mismatch['phase']} state"
            )
            print(f"  ct={first_mismatch['ct']!r}")
            print(f"  modelopt={first_mismatch['modelopt']!r}")
        else:
            print(
                "first_mismatch="
                f"call={first_mismatch['call_index']} "
                f"phase={first_mismatch['phase']} "
                f"tensor={first_mismatch['tensor']}"
            )
            for field, values in first_mismatch["fields"].items():
                if not values["equal"]:
                    print(
                        f"  {field}: ct={values['ct']!r} "
                        f"modelopt={values['modelopt']!r}"
                    )

    return 0 if common else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_collect = sub.add_parser("collect")
    p_collect.add_argument("--container", required=True)
    p_collect.add_argument("--output", type=Path, required=True)

    p_compare = sub.add_parser("compare")
    p_compare.add_argument("--ct", type=Path, required=True)
    p_compare.add_argument("--modelopt", type=Path, required=True)
    p_compare.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "collect":
        return collect(args.container, args.output)
    return compare(args.ct, args.modelopt, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
