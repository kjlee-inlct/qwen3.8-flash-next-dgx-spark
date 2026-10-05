#!/usr/bin/env python3
"""Post-hoc R28 per-call RM-pattern analysis.

Reads only preserved R28 evidence. It does not launch a model, change the managed
service, add probes, or mutate kernel/runtime state.

RM bytes are logical direct-RM allocation activity volume, not exact resident
ownership. Unquantized payload bytes are nominal torch.empty weight payload.
Temporal overlap does not prove causal ownership.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import pathlib
import re
import sys
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
BASE_PATH = HERE / "analyze-orcarouter-r28-unquant-linear-overlap.py"

spec = importlib.util.spec_from_file_location("r28_overlap_base", BASE_PATH)
if spec is None or spec.loader is None:
    raise SystemExit(f"cannot import R28 analyzer: {BASE_PATH}")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)

LAYER_INDEX_RE = re.compile(r"(?:^|\.)language_model\.model\.layers\.(\d+)\.")
HYPER_COMPONENT_RE = re.compile(r"hyper_connection\.([^\s.]+(?:\.[^\s.]+)*)$")


def mib(value: int) -> float:
    return value / 1048576.0


def fmt_mib(value: int) -> str:
    return f"{mib(value):.3f}"


def family(prefix: str) -> str:
    return base.family(prefix)


def layer_index(prefix: str) -> int | None:
    match = LAYER_INDEX_RE.search(prefix)
    return int(match.group(1)) if match else None


def hyper_component(prefix: str) -> str:
    marker = ".attn_hyper_connection."
    if marker in prefix:
        return prefix.split(marker, 1)[1]
    marker = ".ffn_hyper_connection."
    if marker in prefix:
        return "ffn:" + prefix.split(marker, 1)[1]
    if "hyper_connection" in prefix:
        return prefix.rsplit("hyper_connection", 1)[-1].lstrip(".") or "unknown"
    return "not_hyper"


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    den_x = math.sqrt(sum(v * v for v in dx))
    den_y = math.sqrt(sum(v * v for v in dy))
    if den_x == 0.0 or den_y == 0.0:
        return None
    return sum(a * b for a, b in zip(dx, dy)) / (den_x * den_y)


def hist_line(counter: Counter[int]) -> str:
    if not counter:
        return "NONE"
    return ",".join(f"{fmt_mib(size)}:{count}" for size, count in sorted(counter.items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=pathlib.Path)
    args = parser.parse_args()
    root = args.evidence

    offset, offsets = base.clock_offset(root)
    events = base.parse_logs(base.read(root / "candidate-container.log"), offset)
    host_page_size = int(base.read(root / "host-page-size.txt").strip())
    order4 = [
        row
        for row in base.parse_rm_entries(base.read(root / "rm-trace.txt"))
        if row.page_size == 65536
    ]
    if not order4:
        raise SystemExit("no 64 KiB-path nv_alloc_pages activity found")

    ctor_pairs = base.pair_simple(events, base.CTOR_BEGIN, base.CTOR_END)
    if not ctor_pairs:
        raise SystemExit("R26 inherited model-constructor marker pair missing")
    scored = [
        (
            base.logical_bytes(
                base.rows_in_interval(order4, begin.mono, end.mono), host_page_size
            ),
            begin,
            end,
        )
        for begin, end in ctor_pairs
    ]
    _, ctor_begin, ctor_end = max(scored, key=lambda item: item[0])
    ctor_rows = base.rows_in_interval(order4, ctor_begin.mono, ctor_end.mono)
    ctor_set = set(ctor_rows)

    moe_all = base.pair_seq(events, base.MOE_BEGIN, base.MOE_END)
    moe_selected = [
        item
        for item in moe_all
        if item.end.mono >= ctor_begin.mono and item.begin.mono <= ctor_end.mono
    ]
    moe_rows = base.row_set_for_intervals(
        ctor_rows, [(item.begin.mono, item.end.mono) for item in moe_selected]
    )
    residual_rows = ctor_set - moe_rows

    unquant_all = base.pair_unquant(events)
    selected = [
        item
        for item in unquant_all
        if item.end.mono >= ctor_begin.mono and item.begin.mono <= ctor_end.mono
    ]
    if not selected:
        raise SystemExit("no selected R28 unquantized Linear intervals")

    per_call: list[dict[str, object]] = []
    union_rows: set[object] = set()
    for item in selected:
        rows = base.rows_in_interval(ctor_rows, item.begin.mono, item.end.mono)
        row_set = set(rows)
        union_rows |= row_set
        residual_part = row_set & residual_rows
        rm_bytes = base.logical_bytes(residual_part, host_page_size)
        payload = base.payload_bytes(item)
        request_sizes = [row.page_count * host_page_size for row in residual_part]
        per_call.append(
            {
                "item": item,
                "family": family(item.prefix),
                "layer": layer_index(item.prefix),
                "component": hyper_component(item.prefix),
                "rm": rm_bytes,
                "payload": payload,
                "request_count": len(residual_part),
                "request_sizes": request_sizes,
            }
        )

    unquant_residual_rows = union_rows & residual_rows
    uncovered = residual_rows - union_rows

    positive = [row for row in per_call if int(row["rm"]) > 0]
    zero = [row for row in per_call if int(row["rm"]) == 0]
    hyper = [row for row in per_call if row["family"] == "hyper_connection"]
    hyper_positive = [row for row in hyper if int(row["rm"]) > 0]

    call_activity_hist = Counter(int(row["rm"]) for row in per_call)
    positive_call_activity_hist = Counter(int(row["rm"]) for row in positive)
    hyper_activity_hist = Counter(int(row["rm"]) for row in hyper)
    hyper_positive_hist = Counter(int(row["rm"]) for row in hyper_positive)

    request_hist = Counter(
        size for row in per_call for size in row["request_sizes"]  # type: ignore[index]
    )
    hyper_request_hist = Counter(
        size for row in hyper for size in row["request_sizes"]  # type: ignore[index]
    )
    uncovered_request_hist = Counter(
        row.page_count * host_page_size for row in uncovered
    )

    family_stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in per_call:
        fam = str(row["family"])
        family_stats[fam]["calls"] += 1
        family_stats[fam]["positive"] += int(int(row["rm"]) > 0)
        family_stats[fam]["rm"] += int(row["rm"])
        family_stats[fam]["payload"] += int(row["payload"])
        family_stats[fam]["requests"] += int(row["request_count"])

    component_stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in hyper:
        comp = str(row["component"])
        component_stats[comp]["calls"] += 1
        component_stats[comp]["positive"] += int(int(row["rm"]) > 0)
        component_stats[comp]["rm"] += int(row["rm"])
        component_stats[comp]["payload"] += int(row["payload"])

    payloads = [float(int(row["payload"])) for row in per_call]
    rms = [float(int(row["rm"])) for row in per_call]
    positive_payloads = [float(int(row["payload"])) for row in positive]
    positive_rms = [float(int(row["rm"])) for row in positive]
    corr_all = pearson(payloads, rms)
    corr_positive = pearson(positive_payloads, positive_rms)

    hyper_layers = sorted(
        {int(row["layer"]) for row in hyper_positive if row["layer"] is not None}
    )
    hyper_layer_gaps = [b - a for a, b in zip(hyper_layers, hyper_layers[1:])]

    uncovered_sorted = sorted(
        uncovered,
        key=lambda row: row.page_count * host_page_size,
        reverse=True,
    )

    print("R28B_UNQUANT_CALL_PATTERNS=BEGIN")
    print("analysis_semantics=posthoc_temporal_pattern_not_causal_ownership")
    print("rm_bytes_semantics=activity_volume_not_resident_ownership")
    print("payload_semantics=nominal_unquantized_weight_tensor_bytes")
    print(f"clock_anchor_count={len(offsets)}")
    print(f"selected_unquant_calls={len(per_call)}")
    print(f"positive_rm_calls={len(positive)}")
    print(f"zero_rm_calls={len(zero)}")
    print(f"positive_rm_call_pct={100.0 * len(positive) / len(per_call):.6f}")
    print(
        "unquant_residual_activity_mib="
        f"{mib(base.logical_bytes(unquant_residual_rows, host_page_size)):.3f}"
    )
    print(
        "uncovered_residual_activity_mib="
        f"{mib(base.logical_bytes(uncovered, host_page_size)):.3f}"
    )
    print(f"call_activity_histogram_mib={hist_line(call_activity_hist)}")
    print(f"positive_call_activity_histogram_mib={hist_line(positive_call_activity_hist)}")
    print(f"rm_request_size_histogram_mib={hist_line(request_hist)}")
    print(
        "payload_rm_pearson_all="
        + ("NA" if corr_all is None else f"{corr_all:.9f}")
    )
    print(
        "payload_rm_pearson_positive="
        + ("NA" if corr_positive is None else f"{corr_positive:.9f}")
    )

    for fam in sorted(family_stats):
        stats = family_stats[fam]
        print(f"family.{fam}.calls={stats['calls']}")
        print(f"family.{fam}.positive_rm_calls={stats['positive']}")
        print(f"family.{fam}.zero_rm_calls={stats['calls'] - stats['positive']}")
        print(f"family.{fam}.request_count={stats['requests']}")
        print(f"family.{fam}.rm_activity_mib={mib(stats['rm']):.3f}")
        print(f"family.{fam}.nominal_payload_mib={mib(stats['payload']):.3f}")

    print(f"hyper_connection.activity_histogram_mib={hist_line(hyper_activity_hist)}")
    print(
        "hyper_connection.positive_activity_histogram_mib="
        f"{hist_line(hyper_positive_hist)}"
    )
    print(
        "hyper_connection.request_size_histogram_mib="
        f"{hist_line(hyper_request_hist)}"
    )
    print(
        "hyper_connection.positive_layers="
        + (",".join(str(value) for value in hyper_layers) if hyper_layers else "NONE")
    )
    gap_hist = Counter(hyper_layer_gaps)
    print(
        "hyper_connection.positive_layer_gap_histogram="
        + (
            ",".join(f"{gap}:{count}" for gap, count in sorted(gap_hist.items()))
            if gap_hist
            else "NONE"
        )
    )

    for index, (component, stats) in enumerate(
        sorted(component_stats.items(), key=lambda pair: pair[1]["rm"], reverse=True),
        start=1,
    ):
        print(
            f"hyper_component.{index}=name={component} calls={stats['calls']} "
            f"positive={stats['positive']} rm_mib={mib(stats['rm']):.3f} "
            f"payload_mib={mib(stats['payload']):.3f}"
        )

    ranked = sorted(per_call, key=lambda row: (int(row["rm"]), -int(row["payload"])), reverse=True)
    for index, row in enumerate(ranked[:32], start=1):
        item = row["item"]
        assert isinstance(item, base.UnquantInterval)
        print(
            f"positive_call.{index}=seq={item.seq} family={row['family']} "
            f"layer_index={row['layer'] if row['layer'] is not None else 'NA'} "
            f"component={row['component']} rm_mib={mib(int(row['rm'])):.3f} "
            f"requests={row['request_count']} payload_mib={mib(int(row['payload'])):.3f} "
            f"prefix={item.prefix}"
        )

    print(f"uncovered.request_count={len(uncovered)}")
    print(f"uncovered.request_size_histogram_mib={hist_line(uncovered_request_hist)}")
    for index, row in enumerate(uncovered_sorted[:20], start=1):
        request_bytes = row.page_count * host_page_size
        previous = [item for item in selected if item.end.mono <= row.mono]
        following = [item for item in selected if item.begin.mono >= row.mono]
        prev_item = max(previous, key=lambda item: item.end.mono) if previous else None
        next_item = min(following, key=lambda item: item.begin.mono) if following else None
        print(
            f"uncovered.top.{index}=mono={row.mono:.9f} rm_mib={mib(request_bytes):.3f} "
            f"prev_seq={prev_item.seq if prev_item else 'NA'} "
            f"prev_prefix={prev_item.prefix if prev_item else 'NONE'} "
            f"next_seq={next_item.seq if next_item else 'NA'} "
            f"next_prefix={next_item.prefix if next_item else 'NONE'}"
        )

    # This analysis intentionally does not promote a causal mechanism. It only
    # determines whether RM activity is sparse/discrete across many small
    # constructor calls, which is the prerequisite for choosing the next narrow
    # allocator discriminator.
    if len(hyper_positive) < len(hyper) and hyper_positive_hist:
        discriminator = "R28B_HYPER_CONNECTION_RM_ACTIVITY_SPARSE_ACROSS_CALLS"
    else:
        discriminator = "R28B_HYPER_CONNECTION_RM_ACTIVITY_NOT_SPARSE"
    print(f"r28b_discriminator={discriminator}")
    print("R28B_UNQUANT_CALL_PATTERNS=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
