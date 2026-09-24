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
TWIN_PREFIX = "QWEN38_H20D_TWIN "
SINGLE_PREFIX = "QWEN38_H20D_SINGLE "
UPSTREAM_PREFIX = "QWEN38_H20U_LAYER0 "
LINEAR_PREFIX = "QWEN38_H20L_LINEAR "
QKVZ_PREFIX = "QWEN38_H20P_QKVZ "
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


LINEAR_STAGE_NAMES = (
    "input_hidden",
    "mixed_qkvz",
    "ba",
    "mixed_qkv",
    "z",
    "b",
    "a",
    "core_attn_out",
    "output",
)


def parse_qkvz_records(lines: list[str]) -> list[dict]:
    records: list[dict] = []
    for raw in lines:
        pos = raw.find(QKVZ_PREFIX)
        if pos < 0:
            continue
        records.append(json.loads(raw[pos + len(QKVZ_PREFIX) :].strip()))
    return records


def qkvz_twin_probe(
    *,
    container: str,
    model: str,
    output: Path,
    prompt: str,
    api_base: str,
) -> int:
    if not _container_exists(container):
        print(f"ERROR: H20 QKVZ container not found: {container}", file=sys.stderr)
        return 2

    trigger = "/tmp/qwen38_h20p_qkvz_twin.enable"
    request_id_file = "/tmp/qwen38_h20p_request_id"
    other_paths = (
        "/tmp/qwen38_h20c_trace.enable",
        "/tmp/qwen38_h20d_twin.enable",
        "/tmp/qwen38_h20d_single.enable",
        "/tmp/qwen38_h20u_layer0.enable",
        "/tmp/qwen38_h20l_linear.enable",
    )
    try:
        _docker_exec(
            container,
            "rm -f "
            + " ".join((trigger, request_id_file, *other_paths))
            + f"; touch {trigger}",
        )
        for request_id in (0, 1):
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
            print(f"qkvz-twin request {request_id + 1}/2 completed")
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
    lines = (result.stdout + "\n" + result.stderr).splitlines()
    all_records = parse_qkvz_records(lines)
    by_id = {int(r.get("request_id", -1)): r for r in all_records}
    records = [by_id[rid] for rid in (0, 1) if rid in by_id]
    if len(records) != 2:
        print(
            f"ERROR: expected H20 QKVZ records for request ids 0 and 1; "
            f"found {sorted(by_id)}",
            file=sys.stderr,
        )
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in records),
        encoding="utf-8",
    )
    meta = [line for line in lines if "QWEN38_H20P_META " in line]
    if meta:
        print(meta[-1].strip())
    for record in records:
        print(
            f"qkvz_probe request={record['request_id']} "
            f"compiled_vs_natural_equal="
            f"{record.get('compiled_vs_natural_equal')} "
            f"natural_vs_zeroed_equal="
            f"{record.get('natural_vs_zeroed_equal')} "
            f"zeroed_repeat_equal={record.get('zeroed_repeat_equal')} "
            f"locks_present={record.get('locks_present')} "
            f"scheme={record.get('scheme_cls')} "
            f"kernel={record.get('kernel_cls')}"
        )
        if record.get("locks_present"):
            print(
                f"qkvz_locks request={record['request_id']} "
                f"pre_vs_after_natural="
                f"{record.get('lock_pre') == record.get('lock_after_natural')} "
                f"zero1_pre_vs_post="
                f"{record.get('lock_zero1_pre') == record.get('lock_zero1_post')} "
                f"zero2_pre_vs_post="
                f"{record.get('lock_zero2_pre') == record.get('lock_zero2_post')}"
            )
    left, right = records
    print(
        "qkvz_repeat: "
        f"input_equal={left.get('input') == right.get('input')} "
        f"compiled_output_equal="
        f"{left.get('compiled_output') == right.get('compiled_output')} "
        f"zeroed_eager1_equal="
        f"{left.get('zeroed_eager1') == right.get('zeroed_eager1')}"
    )
    print(f"wrote 2 QKVZ twin records to {output}")
    return 0


def parse_linear_records(lines: list[str]) -> list[dict]:
    records: list[dict] = []
    for raw in lines:
        pos = raw.find(LINEAR_PREFIX)
        if pos < 0:
            continue
        payload = raw[pos + len(LINEAR_PREFIX) :].strip()
        records.append(json.loads(payload))
    return records


def _linear_repeat_summary(records: list[dict]) -> dict:
    by_id = {int(record["request_id"]): record for record in records}
    if 0 not in by_id or 1 not in by_id:
        return {"comparable": False, "request_ids": sorted(by_id)}
    left = by_id[0].get("tensors", {})
    right = by_id[1].get("tensors", {})
    present = [
        name for name in LINEAR_STAGE_NAMES if name in left and name in right
    ]
    fields = {name: left[name] == right[name] for name in present}
    first = next((name for name in present if not fields[name]), None)
    return {
        "comparable": True,
        "present_stages": present,
        "missing_left": [name for name in LINEAR_STAGE_NAMES if name not in left],
        "missing_right": [name for name in LINEAR_STAGE_NAMES if name not in right],
        "fields": fields,
        "first_mismatch": first,
        "all_equal": bool(present) and all(fields.values()),
    }


def linear_probe(
    *,
    container: str,
    model: str,
    output: Path,
    prompt: str,
    api_base: str,
) -> int:
    if not _container_exists(container):
        print(f"ERROR: H20 linear-attn container not found: {container}", file=sys.stderr)
        return 2

    trigger = "/tmp/qwen38_h20l_linear.enable"
    request_id_file = "/tmp/qwen38_h20l_request_id"
    other_paths = (
        "/tmp/qwen38_h20c_trace.enable",
        "/tmp/qwen38_h20d_twin.enable",
        "/tmp/qwen38_h20d_single.enable",
        "/tmp/qwen38_h20u_layer0.enable",
    )
    try:
        _docker_exec(
            container,
            "rm -f "
            + " ".join((trigger, request_id_file, *other_paths))
            + f"; touch {trigger}",
        )
        for request_id in (0, 1):
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
            print(f"linear-attn request {request_id + 1}/2 completed")
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

    all_records = parse_linear_records(
        (result.stdout + "\n" + result.stderr).splitlines()
    )
    by_id = {int(record.get("request_id", -1)): record for record in all_records}
    records = [by_id[rid] for rid in (0, 1) if rid in by_id]
    if len(records) != 2:
        print(
            f"ERROR: expected H20 linear-attn records for request ids 0 and 1; "
            f"found {sorted(by_id)}",
            file=sys.stderr,
        )
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    summary = _linear_repeat_summary(records)
    print(f"wrote 2 linear-attn records to {output}")
    print(
        f"linear_repeat: all_equal={summary.get('all_equal')} "
        f"first_mismatch={summary.get('first_mismatch')} "
        f"fields={summary.get('fields')}"
    )
    if summary.get("missing_left") or summary.get("missing_right"):
        print(
            "linear_path_missing: "
            f"request0={summary.get('missing_left')} "
            f"request1={summary.get('missing_right')}"
        )
    return 0


def compare_linear(
    ct_path: Path,
    modelopt_path: Path,
    output: Path | None,
) -> int:
    ct_records = load_jsonl(ct_path)
    mo_records = load_jsonl(modelopt_path)
    ct_repeat = _linear_repeat_summary(ct_records)
    mo_repeat = _linear_repeat_summary(mo_records)
    ct = {int(record["request_id"]): record for record in ct_records}
    mo = {int(record["request_id"]): record for record in mo_records}
    common = sorted(set(ct) & set(mo))
    cross = []
    for request_id in common:
        ct_t = ct[request_id].get("tensors", {})
        mo_t = mo[request_id].get("tensors", {})
        present = [
            name
            for name in LINEAR_STAGE_NAMES
            if name in ct_t and name in mo_t
        ]
        fields = {name: ct_t[name] == mo_t[name] for name in present}
        cross.append(
            {
                "request_id": request_id,
                "present_stages": present,
                "fields": fields,
                "first_mismatch": next(
                    (name for name in present if not fields[name]), None
                ),
                "all_equal": bool(present) and all(fields.values()),
            }
        )

    report = {
        "schema": 1,
        "ct_file": str(ct_path),
        "modelopt_file": str(modelopt_path),
        "ct_repeat": ct_repeat,
        "modelopt_repeat": mo_repeat,
        "cross": cross,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote linear-attn comparison report to {output}")

    for label, row in (("ct_repeat", ct_repeat), ("modelopt_repeat", mo_repeat)):
        if row.get("comparable"):
            print(
                f"{label}: all_equal={row['all_equal']} "
                f"first_mismatch={row['first_mismatch']} "
                f"fields={row['fields']}"
            )
    for row in cross:
        print(
            f"cross request={row['request_id']} "
            f"all_equal={row['all_equal']} "
            f"first_mismatch={row['first_mismatch']} "
            f"fields={row['fields']}"
        )
    return 0 if common else 2


def parse_upstream_records(lines: list[str]) -> list[dict]:
    records: list[dict] = []
    for raw in lines:
        pos = raw.find(UPSTREAM_PREFIX)
        if pos < 0:
            continue
        payload = raw[pos + len(UPSTREAM_PREFIX) :].strip()
        records.append(json.loads(payload))
    return records


def upstream_probe(
    *,
    container: str,
    model: str,
    output: Path,
    prompt: str,
    api_base: str,
) -> int:
    if not _container_exists(container):
        print(f"ERROR: H20 upstream container not found: {container}", file=sys.stderr)
        return 2

    trigger = "/tmp/qwen38_h20u_layer0.enable"
    request_id_file = "/tmp/qwen38_h20u_request_id"
    h20c_trigger = "/tmp/qwen38_h20c_trace.enable"
    twin_trigger = "/tmp/qwen38_h20d_twin.enable"
    single_trigger = "/tmp/qwen38_h20d_single.enable"
    try:
        _docker_exec(
            container,
            f"rm -f {trigger} {request_id_file} {h20c_trigger} "
            f"{twin_trigger} {single_trigger}; touch {trigger}",
        )
        for request_id in (0, 1):
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
            print(f"upstream request {request_id + 1}/2 completed")
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

    records = parse_upstream_records(
        (result.stdout + "\n" + result.stderr).splitlines()
    )
    keyed = {
        (int(record.get("layer_idx", 0)), int(record.get("request_id", -1))): record
        for record in records
    }
    layers = sorted({layer for layer, _ in keyed})
    wanted = [
        keyed[(layer, rid)]
        for layer in layers
        for rid in (0, 1)
        if (layer, rid) in keyed
    ]
    missing = [
        (layer, rid)
        for layer in layers
        for rid in (0, 1)
        if (layer, rid) not in keyed
    ]
    if not layers or missing:
        print(
            f"ERROR: incomplete H20 upstream records; layers={layers} missing={missing}",
            file=sys.stderr,
        )
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in wanted),
        encoding="utf-8",
    )
    print(f"wrote {len(wanted)} upstream records to {output}")
    base_names = (
        "entry_hidden",
        "attn_block_input",
        "attn_out",
        "mlp_block_input",
        "mlp_out",
    )
    layer15_extra_names = (
        "prev_block_output",
        "prev_injection",
        "pre_attn_hc_hidden",
        "post_attn_hc_hidden",
        "attn_injection",
    )
    layer15_causal_names = (
        "entry_hidden",
        "prev_block_output",
        "prev_injection",
        "pre_attn_hc_hidden",
        "post_attn_hc_hidden",
        "attn_injection",
        "attn_block_input",
        "attn_out",
        "mlp_block_input",
        "mlp_out",
    )
    layer14_causal_names = (
        "entry_hidden",
        "prev_block_output",
        "prev_injection",
        "pre_attn_hc_hidden",
        "post_attn_hc_hidden",
        "attn_injection",
        "attn_block_input",
        "attn_out",
        "post_mlp_hc_hidden",
        "post_mlp_hc_injection",
        "mlp_block_input",
        "mlp_out",
    )
    layer14_extra_names = (
        "prev_block_output",
        "prev_injection",
        "pre_attn_hc_hidden",
        "post_attn_hc_hidden",
        "attn_injection",
        "post_mlp_hc_hidden",
        "post_mlp_hc_injection",
    )

    def names_for(layer: int, a: dict, b: dict) -> tuple[str, ...]:
        if layer == 14 and any(name in a or name in b for name in layer14_extra_names):
            return layer14_causal_names
        if layer == 15 and any(
            name in a or name in b for name in layer15_extra_names
        ):
            return layer15_causal_names
        return base_names
    for layer in layers:
        a = keyed[(layer, 0)].get("tensors", {})
        b = keyed[(layer, 1)].get("tensors", {})
        names = names_for(layer, a, b)
        fields = {name: a.get(name) == b.get(name) for name in names}
        first = next((name for name in names if not fields[name]), None)
        print(
            f"upstream_repeat layer={layer} all_equal={all(fields.values())} "
            f"first_mismatch={first} fields={fields}"
        )
    return 0


def compare_upstream(
    ct_path: Path,
    modelopt_path: Path,
    output: Path | None,
) -> int:
    base_names = (
        "entry_hidden",
        "attn_block_input",
        "attn_out",
        "mlp_block_input",
        "mlp_out",
    )
    layer15_extra_names = (
        "prev_block_output",
        "prev_injection",
        "pre_attn_hc_hidden",
        "post_attn_hc_hidden",
        "attn_injection",
    )
    layer15_causal_names = (
        "entry_hidden",
        "prev_block_output",
        "prev_injection",
        "pre_attn_hc_hidden",
        "post_attn_hc_hidden",
        "attn_injection",
        "attn_block_input",
        "attn_out",
        "mlp_block_input",
        "mlp_out",
    )
    layer14_compare_extra_names = (
        "prev_block_output",
        "prev_injection",
        "pre_attn_hc_hidden",
        "post_attn_hc_hidden",
        "attn_injection",
        "post_mlp_hc_hidden",
        "post_mlp_hc_injection",
    )
    layer14_causal_names = (
        "entry_hidden",
        "prev_block_output",
        "prev_injection",
        "pre_attn_hc_hidden",
        "post_attn_hc_hidden",
        "attn_injection",
        "attn_block_input",
        "attn_out",
        "post_mlp_hc_hidden",
        "post_mlp_hc_injection",
        "mlp_block_input",
        "mlp_out",
    )

    def names_for(layer: int, a: dict, b: dict) -> tuple[str, ...]:
        if layer == 14 and any(name in a or name in b for name in layer14_compare_extra_names):
            return layer14_causal_names
        if layer == 15 and any(
            name in a or name in b for name in layer15_extra_names
        ):
            return layer15_causal_names
        return base_names
    def key_records(path: Path) -> dict[tuple[int, int], dict]:
        return {
            (int(r.get("layer_idx", 0)), int(r["request_id"])): r
            for r in load_jsonl(path)
        }

    ct_records = key_records(ct_path)
    mo_records = key_records(modelopt_path)
    common = sorted(set(ct_records) & set(mo_records))

    def repeat_fields(records: dict[tuple[int, int], dict]) -> dict[int, dict]:
        layers = sorted({layer for layer, _ in records})
        result = {}
        for layer in layers:
            if (layer, 0) not in records or (layer, 1) not in records:
                result[layer] = {"comparable": False}
                continue
            a = records[(layer, 0)].get("tensors", {})
            b = records[(layer, 1)].get("tensors", {})
            names = names_for(layer, a, b)
            fields = {name: a.get(name) == b.get(name) for name in names}
            first = next((name for name in names if not fields[name]), None)
            result[layer] = {
                "comparable": True,
                "fields": fields,
                "first_mismatch": first,
                "all_equal": all(fields.values()),
            }
        return result

    cross = []
    for layer_idx, request_id in common:
        ct_t = ct_records[(layer_idx, request_id)].get("tensors", {})
        mo_t = mo_records[(layer_idx, request_id)].get("tensors", {})
        names = names_for(layer_idx, ct_t, mo_t)
        fields = {name: ct_t.get(name) == mo_t.get(name) for name in names}
        cross.append(
            {
                "layer_idx": layer_idx,
                "request_id": request_id,
                "fields": fields,
                "first_mismatch": next(
                    (name for name in names if not fields[name]),
                    None,
                ),
                "all_equal": all(fields.values()),
            }
        )

    report = {
        "schema": 1,
        "ct_file": str(ct_path),
        "modelopt_file": str(modelopt_path),
        "ct_repeat": repeat_fields(ct_records),
        "modelopt_repeat": repeat_fields(mo_records),
        "cross": cross,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote upstream comparison report to {output}")

    for label in ("ct_repeat", "modelopt_repeat"):
        for layer_idx, row in sorted(report[label].items()):
            if row.get("comparable"):
                print(
                    f"{label} layer={layer_idx}: all_equal={row['all_equal']} "
                    f"first_mismatch={row['first_mismatch']} fields={row['fields']}"
                )
    for row in cross:
        print(
            f"cross layer={row['layer_idx']} request={row['request_id']} all_equal={row['all_equal']} "
            f"first_mismatch={row['first_mismatch']} fields={row['fields']}"
        )
    return 0 if common else 2


def parse_single_records(lines: list[str]) -> list[dict]:
    records: list[dict] = []
    for raw in lines:
        pos = raw.find(SINGLE_PREFIX)
        if pos < 0:
            continue
        payload = raw[pos + len(SINGLE_PREFIX) :].strip()
        records.append(json.loads(payload))
    return records


def single_probe(
    *,
    container: str,
    model: str,
    output: Path,
    repeats: int,
    prompt: str,
    api_base: str,
) -> int:
    if not _container_exists(container):
        print(f"ERROR: H20-D container not found: {container}", file=sys.stderr)
        return 2

    existing = subprocess.run(
        ["docker", "logs", container],
        text=True,
        capture_output=True,
        check=False,
    )
    if existing.returncode != 0:
        print(existing.stderr, file=sys.stderr)
        return existing.returncode
    prior = parse_single_records(
        (existing.stdout + "\n" + existing.stderr).splitlines()
    )
    start_id = 0
    if prior:
        start_id = max(int(record.get("request_id", -1)) for record in prior) + 1

    trigger = "/tmp/qwen38_h20d_single.enable"
    request_id_file = "/tmp/qwen38_h20d_single_request_id"
    twin_trigger = "/tmp/qwen38_h20d_twin.enable"
    h20c_trigger = "/tmp/qwen38_h20c_trace.enable"
    try:
        _docker_exec(
            container,
            f"rm -f {trigger} {request_id_file} {twin_trigger} {h20c_trigger}; touch {trigger}",
        )
        for offset in range(repeats):
            request_id = start_id + offset
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
            print(f"single request {offset + 1}/{repeats} completed id={request_id}")
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
    all_records = parse_single_records(
        (result.stdout + "\n" + result.stderr).splitlines()
    )
    wanted_ids = set(range(start_id, start_id + repeats))
    records = [
        record
        for record in all_records
        if int(record.get("request_id", -1)) in wanted_ids
    ]
    if len(records) != repeats:
        print(
            f"ERROR: expected {repeats} {SINGLE_PREFIX.strip()} records, "
            f"found {len(records)} for request ids {sorted(wanted_ids)}",
            file=sys.stderr,
        )
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    for record in records:
        print(
            f"single request={record.get('request_id')} "
            f"layer={record.get('layer_name')!r}"
        )
    print(f"wrote {len(records)} single-pass records to {output}")
    return 0


def compare_single(
    ct_path: Path,
    modelopt_path: Path,
    output: Path | None,
) -> int:
    ct_records = load_jsonl(ct_path)
    mo_records = load_jsonl(modelopt_path)
    ct = {int(record["request_id"]): record for record in ct_records}
    mo = {int(record["request_id"]): record for record in mo_records}
    common = sorted(set(ct) & set(mo))
    names = ("x", "topk_weights", "topk_ids", "shared_experts_input", "output")

    def repeat_summary(records: dict[int, dict]) -> dict:
        ids = sorted(records)
        if len(ids) < 2:
            return {"comparable": False}
        a, b = ids[:2]
        ta = records[a].get("tensors", {})
        tb = records[b].get("tensors", {})
        fields = {name: ta.get(name) == tb.get(name) for name in names}
        return {
            "comparable": True,
            "requests": [a, b],
            "fields": fields,
            "all_equal": all(fields.values()),
        }

    cross = []
    for request_id in common:
        ct_t = ct[request_id].get("tensors", {})
        mo_t = mo[request_id].get("tensors", {})
        fields = {name: ct_t.get(name) == mo_t.get(name) for name in names}
        cross.append(
            {
                "request_id": request_id,
                "fields": fields,
                "input_equal": all(
                    fields[name]
                    for name in (
                        "x",
                        "topk_weights",
                        "topk_ids",
                        "shared_experts_input",
                    )
                ),
                "output_equal": fields["output"],
            }
        )

    report = {
        "schema": 1,
        "ct_file": str(ct_path),
        "modelopt_file": str(modelopt_path),
        "common_requests": common,
        "ct_repeat": repeat_summary(ct),
        "modelopt_repeat": repeat_summary(mo),
        "cross": cross,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote single-pass comparison report to {output}")

    for label in ("ct_repeat", "modelopt_repeat"):
        row = report[label]
        if row.get("comparable"):
            print(
                f"{label}: all_equal={row['all_equal']} "
                f"fields={row['fields']}"
            )
    for row in cross:
        print(
            f"cross request={row['request_id']} "
            f"input_equal={row['input_equal']} output_equal={row['output_equal']} "
            f"fields={row['fields']}"
        )
    return 0 if common else 2


def parse_twin_records(lines: list[str]) -> list[dict]:
    records: list[dict] = []
    for raw in lines:
        pos = raw.find(TWIN_PREFIX)
        if pos < 0:
            continue
        payload = raw[pos + len(TWIN_PREFIX) :].strip()
        records.append(json.loads(payload))
    return records


def twin_probe(
    *,
    container: str,
    model: str,
    output: Path,
    repeats: int,
    prompt: str,
    api_base: str,
) -> int:
    if not _container_exists(container):
        print(f"ERROR: H20-D container not found: {container}", file=sys.stderr)
        print(
            "Start the requested H20 profile successfully and wait for READY before probing.",
            file=sys.stderr,
        )
        return 2

    existing = subprocess.run(
        ["docker", "logs", container],
        text=True,
        capture_output=True,
        check=False,
    )
    if existing.returncode != 0:
        print(existing.stderr, file=sys.stderr)
        return existing.returncode
    prior = parse_twin_records((existing.stdout + "\n" + existing.stderr).splitlines())
    start_id = 0
    if prior:
        start_id = max(int(record.get("request_id", -1)) for record in prior) + 1

    trigger = "/tmp/qwen38_h20d_twin.enable"
    request_id_file = "/tmp/qwen38_h20d_request_id"
    h20c_trigger = "/tmp/qwen38_h20c_trace.enable"
    try:
        _docker_exec(
            container,
            f"rm -f {trigger} {request_id_file} {h20c_trigger}; touch {trigger}",
        )
        for offset in range(repeats):
            request_id = start_id + offset
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
            print(f"twin request {offset + 1}/{repeats} completed id={request_id}")
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
    all_records = parse_twin_records(
        (result.stdout + "\n" + result.stderr).splitlines()
    )
    wanted_ids = set(range(start_id, start_id + repeats))
    records = [
        record
        for record in all_records
        if int(record.get("request_id", -1)) in wanted_ids
    ]
    if len(records) != repeats:
        print(
            f"ERROR: expected {repeats} {TWIN_PREFIX.strip()} records, "
            f"found {len(records)} for request ids {sorted(wanted_ids)}",
            file=sys.stderr,
        )
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    for record in records:
        tensors = record.get("tensors", {})
        same = tensors.get("output1") == tensors.get("output2")
        print(
            f"twin request={record.get('request_id')} "
            f"layer={record.get('layer_name')!r} output_equal={same}"
        )
    print(f"wrote {len(records)} twin records to {output}")
    return 0


def compare_twin(
    ct_path: Path,
    modelopt_path: Path,
    output: Path | None,
) -> int:
    ct_records = load_jsonl(ct_path)
    mo_records = load_jsonl(modelopt_path)
    ct = {int(record["request_id"]): record for record in ct_records}
    mo = {int(record["request_id"]): record for record in mo_records}
    common = sorted(set(ct) & set(mo))

    def summarize(records: dict[int, dict]) -> list[dict]:
        result: list[dict] = []
        for request_id in sorted(records):
            record = records[request_id]
            tensors = record.get("tensors", {})
            result.append(
                {
                    "request_id": request_id,
                    "layer_name": record.get("layer_name"),
                    "output_equal": tensors.get("output1") == tensors.get("output2"),
                    "output1": tensors.get("output1"),
                    "output2": tensors.get("output2"),
                }
            )
        return result

    cross: list[dict] = []
    for request_id in common:
        ct_t = ct[request_id].get("tensors", {})
        mo_t = mo[request_id].get("tensors", {})
        input_names = ("x", "topk_weights", "topk_ids", "shared_experts_input")
        input_equal = all(ct_t.get(name) == mo_t.get(name) for name in input_names)
        input_fields = {
            name: {
                "equal": ct_t.get(name) == mo_t.get(name),
                "ct": ct_t.get(name),
                "modelopt": mo_t.get(name),
            }
            for name in input_names
        }
        output1_equal = ct_t.get("output1") == mo_t.get("output1")
        cross.append(
            {
                "request_id": request_id,
                "input_equal": input_equal,
                "inputs": input_fields,
                "output1_equal": output1_equal,
            }
        )

    report = {
        "schema": 1,
        "ct_file": str(ct_path),
        "modelopt_file": str(modelopt_path),
        "ct": summarize(ct),
        "modelopt": summarize(mo),
        "common_requests": common,
        "cross": cross,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote twin comparison report to {output}")

    for label, rows in (("ct", report["ct"]), ("modelopt", report["modelopt"])):
        for row in rows:
            print(
                f"{label}_twin request={row['request_id']} "
                f"output_equal={row['output_equal']} "
                f"layer={row['layer_name']!r}"
            )
    for row in cross:
        print(
            f"cross request={row['request_id']} "
            f"input_equal={row['input_equal']} "
            f"output1_equal={row['output1_equal']}"
        )
        if not row["input_equal"]:
            for name, detail in row["inputs"].items():
                if detail["equal"]:
                    continue
                ct_hash = None if detail["ct"] is None else detail["ct"].get("sha256")
                mo_hash = (
                    None
                    if detail["modelopt"] is None
                    else detail["modelopt"].get("sha256")
                )
                print(f"  input {name}: ct={ct_hash!r} modelopt={mo_hash!r}")
    return 0 if common else 2


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

    p_qkvz = sub.add_parser("qkvz-twin-probe")
    p_qkvz.add_argument("--container", required=True)
    p_qkvz.add_argument("--model", required=True)
    p_qkvz.add_argument("--output", type=Path, required=True)
    p_qkvz.add_argument("--prompt", default="Return exactly the integer 7.")
    p_qkvz.add_argument("--api-base", default="http://127.0.0.1:8888")

    p_linear = sub.add_parser("linear-probe")
    p_linear.add_argument("--container", required=True)
    p_linear.add_argument("--model", required=True)
    p_linear.add_argument("--output", type=Path, required=True)
    p_linear.add_argument("--prompt", default="Return exactly the integer 7.")
    p_linear.add_argument("--api-base", default="http://127.0.0.1:8888")

    p_linear_compare = sub.add_parser("linear-compare")
    p_linear_compare.add_argument("--ct", type=Path, required=True)
    p_linear_compare.add_argument("--modelopt", type=Path, required=True)
    p_linear_compare.add_argument("--output", type=Path)

    p_upstream = sub.add_parser("upstream-probe")
    p_upstream.add_argument("--container", required=True)
    p_upstream.add_argument("--model", required=True)
    p_upstream.add_argument("--output", type=Path, required=True)
    p_upstream.add_argument("--prompt", default="Return exactly the integer 7.")
    p_upstream.add_argument("--api-base", default="http://127.0.0.1:8888")

    p_upstream_compare = sub.add_parser("upstream-compare")
    p_upstream_compare.add_argument("--ct", type=Path, required=True)
    p_upstream_compare.add_argument("--modelopt", type=Path, required=True)
    p_upstream_compare.add_argument("--output", type=Path)

    p_single = sub.add_parser("single-probe")
    p_single.add_argument("--container", required=True)
    p_single.add_argument("--model", required=True)
    p_single.add_argument("--output", type=Path, required=True)
    p_single.add_argument("--repeats", type=int, default=2)
    p_single.add_argument("--prompt", default="Return exactly the integer 7.")
    p_single.add_argument("--api-base", default="http://127.0.0.1:8888")

    p_single_compare = sub.add_parser("single-compare")
    p_single_compare.add_argument("--ct", type=Path, required=True)
    p_single_compare.add_argument("--modelopt", type=Path, required=True)
    p_single_compare.add_argument("--output", type=Path)

    p_twin = sub.add_parser("twin-probe")
    p_twin.add_argument("--container", required=True)
    p_twin.add_argument("--model", required=True)
    p_twin.add_argument("--output", type=Path, required=True)
    p_twin.add_argument("--repeats", type=int, default=2)
    p_twin.add_argument("--prompt", default="Return exactly the integer 7.")
    p_twin.add_argument("--api-base", default="http://127.0.0.1:8888")

    p_twin_compare = sub.add_parser("twin-compare")
    p_twin_compare.add_argument("--ct", type=Path, required=True)
    p_twin_compare.add_argument("--modelopt", type=Path, required=True)
    p_twin_compare.add_argument("--output", type=Path)
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
    if args.command == "qkvz-twin-probe":
        return qkvz_twin_probe(
            container=args.container,
            model=args.model,
            output=args.output,
            prompt=args.prompt,
            api_base=args.api_base,
        )
    if args.command == "linear-probe":
        return linear_probe(
            container=args.container,
            model=args.model,
            output=args.output,
            prompt=args.prompt,
            api_base=args.api_base,
        )
    if args.command == "linear-compare":
        missing = [str(path) for path in (args.ct, args.modelopt) if not path.is_file()]
        if missing:
            print(
                "ERROR: linear-attn probe file(s) missing: " + ", ".join(missing),
                file=sys.stderr,
            )
            return 2
        return compare_linear(args.ct, args.modelopt, args.output)
    if args.command == "upstream-probe":
        return upstream_probe(
            container=args.container,
            model=args.model,
            output=args.output,
            prompt=args.prompt,
            api_base=args.api_base,
        )
    if args.command == "upstream-compare":
        missing = [str(path) for path in (args.ct, args.modelopt) if not path.is_file()]
        if missing:
            print(
                "ERROR: upstream probe file(s) missing: " + ", ".join(missing),
                file=sys.stderr,
            )
            return 2
        return compare_upstream(args.ct, args.modelopt, args.output)
    if args.command == "single-probe":
        return single_probe(
            container=args.container,
            model=args.model,
            output=args.output,
            repeats=args.repeats,
            prompt=args.prompt,
            api_base=args.api_base,
        )
    if args.command == "single-compare":
        missing = [str(path) for path in (args.ct, args.modelopt) if not path.is_file()]
        if missing:
            print(
                "ERROR: single-pass probe file(s) missing: " + ", ".join(missing),
                file=sys.stderr,
            )
            return 2
        return compare_single(args.ct, args.modelopt, args.output)
    if args.command == "twin-probe":
        return twin_probe(
            container=args.container,
            model=args.model,
            output=args.output,
            repeats=args.repeats,
            prompt=args.prompt,
            api_base=args.api_base,
        )
    if args.command == "twin-compare":
        missing = [str(path) for path in (args.ct, args.modelopt) if not path.is_file()]
        if missing:
            print(
                "ERROR: twin probe file(s) missing: " + ", ".join(missing),
                file=sys.stderr,
            )
            return 2
        return compare_twin(args.ct, args.modelopt, args.output)
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
