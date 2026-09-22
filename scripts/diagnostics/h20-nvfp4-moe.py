#!/usr/bin/env python3
"""Collect and compare H20 NVFP4 MoE conversion diagnostic records."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

PREFIX = "QWEN38_H20_MOE_DIAG "
RUNTIME_PREFIX = "QWEN38_H20C_RUNTIME "
RUNTIME_TENSOR_NAMES = (
    "x",
    "topk_weights",
    "topk_ids",
    "shared_experts_input",
    "output",
)
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


def parse_runtime_records(lines: list[str]) -> list[dict]:
    records: list[dict] = []
    for raw in lines:
        pos = raw.find(RUNTIME_PREFIX)
        if pos < 0:
            continue
        payload = raw[pos + len(RUNTIME_PREFIX) :].strip()
        records.append(json.loads(payload))
    return records


def _docker_exec(container: str, command: str) -> None:
    result = subprocess.run(
        ["docker", "exec", container, "sh", "-lc", command],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def _container_exists(container: str) -> bool:
    result = subprocess.run(
        ["docker", "inspect", container],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def trace_runtime(
    *,
    container: str,
    model: str,
    output: Path,
    repeats: int,
    prompt: str,
    api_base: str,
) -> int:
    if not _container_exists(container):
        print(
            f"ERROR: H20-C container not found: {container}",
            file=sys.stderr,
        )
        print(
            "Start the requested H20 profile successfully and wait for READY before tracing.",
            file=sys.stderr,
        )
        return 2
    trigger = "/tmp/qwen38_h20c_trace.enable"
    request_id_file = "/tmp/qwen38_h20c_request_id"
    try:
        _docker_exec(container, f"rm -f {trigger} {request_id_file}; touch {trigger}")
        for request_id in range(repeats):
            _docker_exec(
                container,
                f"printf '%s' {request_id} > {request_id_file}",
            )
            payload = json.dumps(
                {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "top_p": 1.0,
                    "seed": 0,
                    "max_tokens": 1,
                    "stream": False,
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                api_base.rstrip("/") + "/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=300) as response:
                response.read()
            print(f"trace request {request_id + 1}/{repeats} completed")
    finally:
        try:
            _docker_exec(container, f"rm -f {trigger} {request_id_file}")
        except RuntimeError:
            pass

    result = subprocess.run(
        ["docker", "logs", container],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode
    records = parse_runtime_records((result.stdout + "\n" + result.stderr).splitlines())
    if not records:
        print(
            f"ERROR: no {RUNTIME_PREFIX.strip()} records found in {container}",
            file=sys.stderr,
        )
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in records),
        encoding="utf-8",
    )
    request_ids = sorted({int(r.get("request_id", -1)) for r in records})
    layers = sorted({str(r.get("layer_name", "")) for r in records})
    print(
        f"wrote {len(records)} runtime records to {output} "
        f"requests={request_ids} layers={len(layers)}"
    )
    return 0


def _runtime_index(records: list[dict]) -> dict[tuple[int, int, str], dict]:
    by_request: dict[int, list[dict]] = {}
    for record in records:
        request_id = int(record.get("request_id", -1))
        by_request.setdefault(request_id, []).append(record)

    indexed: dict[tuple[int, int, str], dict] = {}
    for request_id, request_records in by_request.items():
        call_ids = sorted(
            {
                int(record["call_index"])
                for record in request_records
                if str(record.get("phase")) == "pre"
            }
        )
        ordinal_for = {call_id: ordinal for ordinal, call_id in enumerate(call_ids)}
        for record in request_records:
            call_id = int(record["call_index"])
            if call_id not in ordinal_for:
                continue
            key = (request_id, ordinal_for[call_id], str(record["phase"]))
            if key in indexed:
                raise ValueError(f"duplicate runtime record key {key}")
            indexed[key] = record
    return indexed


def _runtime_record_diff(left: dict, right: dict) -> tuple[bool, dict]:
    result: dict = {
        "layer_equal": left.get("layer_name") == right.get("layer_name"),
        "left_layer": left.get("layer_name"),
        "right_layer": right.get("layer_name"),
        "tensors": {},
    }
    equal = result["layer_equal"]
    for name in RUNTIME_TENSOR_NAMES:
        lv = left.get("tensors", {}).get(name)
        rv = right.get("tensors", {}).get(name)
        tensor_equal = lv == rv
        result["tensors"][name] = {
            "equal": tensor_equal,
            "ct": lv,
            "modelopt": rv,
        }
        equal = equal and tensor_equal
    return equal, result


def compare_runtime(
    ct_path: Path,
    modelopt_path: Path,
    output: Path | None,
) -> int:
    ct_records = load_jsonl(ct_path)
    mo_records = load_jsonl(modelopt_path)
    ct = _runtime_index(ct_records)
    mo = _runtime_index(mo_records)
    common = sorted(set(ct) & set(mo))
    only_ct = sorted(set(ct) - set(mo))
    only_modelopt = sorted(set(mo) - set(ct))

    mismatches = 0
    first_mismatch: dict | None = None
    comparisons: list[dict] = []
    for key in common:
        equal, detail = _runtime_record_diff(ct[key], mo[key])
        comparisons.append(
            {
                "request_id": key[0],
                "ordinal": key[1],
                "phase": key[2],
                "equal": equal,
                **detail,
            }
        )
        if not equal:
            mismatches += 1
            if first_mismatch is None:
                first_mismatch = {
                    "request_id": key[0],
                    "ordinal": key[1],
                    "phase": key[2],
                    **detail,
                }

    def repeat_stability(records: list[dict]) -> dict:
        indexed = _runtime_index(records)
        req_ids = sorted({key[0] for key in indexed})
        if len(req_ids) < 2:
            return {"comparable": False}
        left_id, right_id = req_ids[:2]
        left_keys = {(key[1], key[2]): value for key, value in indexed.items() if key[0] == left_id}
        right_keys = {(key[1], key[2]): value for key, value in indexed.items() if key[0] == right_id}
        common_repeat = sorted(set(left_keys) & set(right_keys))
        first = None
        count = 0
        for rkey in common_repeat:
            same = (
                left_keys[rkey].get("layer_name") == right_keys[rkey].get("layer_name")
                and left_keys[rkey].get("tensors") == right_keys[rkey].get("tensors")
            )
            if not same:
                count += 1
                if first is None:
                    first = {
                        "ordinal": rkey[0],
                        "phase": rkey[1],
                        "left_layer": left_keys[rkey].get("layer_name"),
                        "right_layer": right_keys[rkey].get("layer_name"),
                    }
        return {
            "comparable": True,
            "requests": [left_id, right_id],
            "common_records": len(common_repeat),
            "mismatches": count,
            "first_mismatch": first,
        }

    report = {
        "schema": 1,
        "ct_file": str(ct_path),
        "modelopt_file": str(modelopt_path),
        "common_records": len(common),
        "only_ct": only_ct,
        "only_modelopt": only_modelopt,
        "record_mismatches": mismatches,
        "first_mismatch": first_mismatch,
        "ct_repeat_stability": repeat_stability(ct_records),
        "modelopt_repeat_stability": repeat_stability(mo_records),
        "comparisons": comparisons,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote runtime comparison report to {output}")

    print(
        f"common_records={len(common)} record_mismatches={mismatches} "
        f"only_ct={len(only_ct)} only_modelopt={len(only_modelopt)}"
    )
    if first_mismatch is None:
        print("first_mismatch=none")
    else:
        print(
            "first_mismatch="
            f"request={first_mismatch['request_id']} "
            f"ordinal={first_mismatch['ordinal']} "
            f"phase={first_mismatch['phase']} "
            f"ct_layer={first_mismatch['left_layer']!r} "
            f"modelopt_layer={first_mismatch['right_layer']!r}"
        )
        for name, values in first_mismatch["tensors"].items():
            if not values["equal"]:
                left_hash = (
                    None if values["ct"] is None else values["ct"].get("sha256")
                )
                right_hash = (
                    None
                    if values["modelopt"] is None
                    else values["modelopt"].get("sha256")
                )
                print(f"  {name}: ct={left_hash!r} modelopt={right_hash!r}")

    for label, stability in (
        ("ct_repeat", report["ct_repeat_stability"]),
        ("modelopt_repeat", report["modelopt_repeat_stability"]),
    ):
        if stability.get("comparable"):
            print(
                f"{label}: common_records={stability['common_records']} "
                f"mismatches={stability['mismatches']} "
                f"first_mismatch={stability['first_mismatch']}"
            )
    return 0 if common else 2


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"diagnostic JSONL missing: {path}")
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

    p_trace = sub.add_parser("trace")
    p_trace.add_argument("--container", required=True)
    p_trace.add_argument("--model", required=True)
    p_trace.add_argument("--output", type=Path, required=True)
    p_trace.add_argument("--repeats", type=int, default=2)
    p_trace.add_argument(
        "--prompt",
        default="Return exactly the integer 7.",
    )
    p_trace.add_argument("--api-base", default="http://127.0.0.1:8888")

    p_runtime_compare = sub.add_parser("runtime-compare")
    p_runtime_compare.add_argument("--ct", type=Path, required=True)
    p_runtime_compare.add_argument("--modelopt", type=Path, required=True)
    p_runtime_compare.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "collect":
        return collect(args.container, args.output)
    if args.command == "compare":
        return compare(args.ct, args.modelopt, args.output)
    if args.command == "trace":
        return trace_runtime(
            container=args.container,
            model=args.model,
            output=args.output,
            repeats=args.repeats,
            prompt=args.prompt,
            api_base=args.api_base,
        )
    missing = [str(path) for path in (args.ct, args.modelopt) if not path.is_file()]
    if missing:
        print(
            "ERROR: runtime trace file(s) missing: " + ", ".join(missing),
            file=sys.stderr,
        )
        print(
            "Run the H20-C trace command successfully on both profiles before runtime-compare.",
            file=sys.stderr,
        )
        return 2
    return compare_runtime(args.ct, args.modelopt, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
