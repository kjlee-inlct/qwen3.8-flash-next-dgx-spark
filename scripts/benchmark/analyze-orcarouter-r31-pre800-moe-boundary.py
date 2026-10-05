#!/usr/bin/env python3
"""R31: classify each pre-w13 800 MiB RM request relative to MoE BEGIN.

Reads only preserved R28 evidence. No model launch, service mutation, probe
change, or evidence mutation is performed. RM bytes are logical allocation
activity volume, not exact resident ownership. Marker alignment is temporal
localization, not causal ownership proof.
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import statistics
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
R27_PATH = HERE / "analyze-orcarouter-r27-linear-overlap.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import analyzer: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


r27 = load_module("r27_r31_base", R27_PATH)

MIB = 1048576
SIZE_400 = 400 * MIB
SIZE_800 = 800 * MIB
MOE_BEGIN = "QWEN38_R26_MODELOPT_MOE_BEGIN"
MOE_END = "QWEN38_R26_MODELOPT_MOE_END"
W13_BEGIN = "QWEN38_R26_MODELOPT_W13_BEGIN"
W13_END = "QWEN38_R26_MODELOPT_W13_END"


def stat_line(values: list[float]) -> str:
    if not values:
        return "NONE"
    return (
        f"min={min(values):.6f} median={statistics.median(values):.6f} "
        f"max={max(values):.6f}"
    )


def classify(pre_mono: float, moe, w13) -> str:
    if pre_mono < moe.begin.mono:
        return "before_moe_begin"
    if moe.begin.mono <= pre_mono < w13.begin.mono:
        return "inside_moe_pre_w13"
    if w13.begin.mono <= pre_mono <= w13.end.mono:
        return "inside_w13"
    if w13.end.mono < pre_mono <= moe.end.mono:
        return "inside_moe_after_w13"
    return "outside_expected_moe_interval"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=pathlib.Path)
    args = parser.parse_args()
    root = args.evidence

    offset, offsets = r27.clock_offset(root)
    events = r27.parse_logs(r27.read(root / "candidate-container.log"), offset)
    host_page_size = int(r27.read(root / "host-page-size.txt").strip())
    order4 = [
        row
        for row in r27.parse_rm_entries(r27.read(root / "rm-trace.txt"))
        if row.page_size == 65536
    ]
    if not order4:
        raise SystemExit("no 64 KiB-path nv_alloc_pages activity found")

    ctor_pairs = r27.pair_simple(events, r27.CTOR_BEGIN, r27.CTOR_END)
    if not ctor_pairs:
        raise SystemExit("R26 model constructor marker pair missing")
    scored = [
        (
            r27.logical_bytes(
                r27.rows_in_interval(order4, begin.mono, end.mono), host_page_size
            ),
            begin,
            end,
        )
        for begin, end in ctor_pairs
    ]
    _, ctor_begin, ctor_end = max(scored, key=lambda item: item[0])
    ctor_rows = r27.rows_in_interval(order4, ctor_begin.mono, ctor_end.mono)
    stream = [
        {
            "index": index,
            "row": row,
            "size": row.page_count * host_page_size,
        }
        for index, row in enumerate(ctor_rows)
    ]
    stream_by_row = {item["row"]: item for item in stream}

    moe_all = r27.pair_seq(events, MOE_BEGIN, MOE_END)
    w13_all = r27.pair_seq(events, W13_BEGIN, W13_END)
    moe = {
        item.seq: item
        for item in moe_all
        if r27.interval_overlaps(
            item.begin.mono, item.end.mono, ctor_begin.mono, ctor_end.mono
        )
    }
    w13 = {
        item.seq: item
        for item in w13_all
        if r27.interval_overlaps(
            item.begin.mono, item.end.mono, ctor_begin.mono, ctor_end.mono
        )
    }

    common = sorted(set(moe) & set(w13))
    missing_moe = sorted(set(w13) - set(moe))
    missing_w13 = sorted(set(moe) - set(w13))

    rows: list[dict[str, object]] = []
    for seq in common:
        m = moe[seq]
        w = w13[seq]
        candidates = [
            row
            for row in ctor_rows
            if w.begin.mono <= row.mono <= w.end.mono
            and row.page_count * host_page_size == SIZE_400
        ]
        if len(candidates) != 1:
            continue
        row400 = candidates[0]
        item400 = stream_by_row[row400]
        idx400 = int(item400["index"])
        prev = stream[idx400 - 1] if idx400 > 0 else None
        if prev is None or int(prev["size"]) != SIZE_800:
            continue
        pre_mono = prev["row"].mono
        rows.append(
            {
                "seq": seq,
                "moe": m,
                "w13": w,
                "pre": prev,
                "item400": item400,
                "class": classify(pre_mono, m, w),
                "pre_to_moe_begin_ms": (m.begin.mono - pre_mono) * 1000.0,
                "moe_begin_to_w13_begin_ms": (w.begin.mono - m.begin.mono) * 1000.0,
                "pre_to_w13_begin_ms": (w.begin.mono - pre_mono) * 1000.0,
            }
        )

    hist = Counter(str(item["class"]) for item in rows)
    before = hist["before_moe_begin"]
    inside_pre = hist["inside_moe_pre_w13"]
    inside_w13 = hist["inside_w13"]

    if len(rows) == len(common) and before == len(rows):
        discriminator = "R31_PRE800_STRICTLY_BEFORE_MODELOPT_MOE_BEGIN"
    elif len(rows) == len(common) and inside_pre == len(rows):
        discriminator = "R31_PRE800_STRICTLY_INSIDE_MODELOPT_MOE_PRE_W13"
    elif len(rows) == len(common) and before + inside_pre == len(rows):
        discriminator = "R31_PRE800_MIXED_ACROSS_MODELOPT_MOE_BEGIN"
    else:
        discriminator = "R31_PRE800_BOUNDARY_PATTERN_NOT_EXACT"

    pre_to_moe = [float(item["pre_to_moe_begin_ms"]) for item in rows]
    moe_to_w13 = [float(item["moe_begin_to_w13_begin_ms"]) for item in rows]
    pre_to_w13 = [float(item["pre_to_w13_begin_ms"]) for item in rows]

    print("R31_PRE800_MOE_BOUNDARY=BEGIN")
    print("analysis_semantics=posthoc_temporal_boundary_not_causal_ownership")
    print("rm_bytes_semantics=activity_volume_not_resident_ownership")
    print(f"clock_anchor_count={len(offsets)}")
    print(f"selected_moe_count={len(moe)}")
    print(f"selected_w13_count={len(w13)}")
    print(f"common_seq_count={len(common)}")
    print(f"missing_moe_for_w13_count={len(missing_moe)}")
    print(f"missing_w13_for_moe_count={len(missing_w13)}")
    print(f"exact_800_400_pair_count={len(rows)}")
    print(
        "pre800_boundary_histogram="
        + (",".join(f"{key}:{hist[key]}" for key in sorted(hist)) or "NONE")
    )
    print(f"pre800_before_moe_begin_count={before}")
    print(f"pre800_inside_moe_pre_w13_count={inside_pre}")
    print(f"pre800_inside_w13_count={inside_w13}")
    print(f"pre800_to_moe_begin_ms={stat_line(pre_to_moe)}")
    print(f"moe_begin_to_w13_begin_ms={stat_line(moe_to_w13)}")
    print(f"pre800_to_w13_begin_ms={stat_line(pre_to_w13)}")

    for ordinal, item in enumerate(rows, start=1):
        pre = item["pre"]
        item400 = item["item400"]
        print(
            f"pair.{ordinal}=seq={item['seq']} class={item['class']} "
            f"pre800_stream={pre['index']} w13_400_stream={item400['index']} "
            f"pre_to_moe_begin_ms={item['pre_to_moe_begin_ms']:.6f} "
            f"moe_begin_to_w13_begin_ms={item['moe_begin_to_w13_begin_ms']:.6f} "
            f"pre_to_w13_begin_ms={item['pre_to_w13_begin_ms']:.6f}"
        )

    print(f"r31_discriminator={discriminator}")
    print("R31_PRE800_MOE_BOUNDARY=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
