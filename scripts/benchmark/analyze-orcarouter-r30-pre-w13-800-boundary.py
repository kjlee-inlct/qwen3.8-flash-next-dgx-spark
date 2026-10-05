#!/usr/bin/env python3
"""R30: verify the 400 MiB RM family against R26 w13 markers and
classify the immediately preceding 800 MiB request.

Reads only preserved R28 evidence. RM bytes are logical allocation activity
volume, not exact resident ownership. Marker alignment is temporal evidence,
not causal ownership proof.
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
R28_PATH = HERE / "analyze-orcarouter-r28-unquant-linear-overlap.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import analyzer: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


r27 = load_module("r27_r30_base", R27_PATH)
r28 = load_module("r28_r30_base", R28_PATH)

MIB = 1048576
SIZE_400 = 400 * MIB
SIZE_800 = 800 * MIB
W13_BEGIN = "QWEN38_R26_MODELOPT_W13_BEGIN"
W13_END = "QWEN38_R26_MODELOPT_W13_END"


def active_one(items: list, mono: float):
    active = [item for item in items if item.begin.mono <= mono <= item.end.mono]
    return active[0] if active else None


def layer_desc(item) -> str:
    if item is None:
        return "NONE"
    return f"{item.layer}:{item.layer_type}"


def stats(values: list[float]) -> str:
    if not values:
        return "NONE"
    return (
        f"min={min(values):.6f} median={statistics.median(values):.6f} "
        f"max={max(values):.6f}"
    )


def counter_line(counter: Counter[str]) -> str:
    if not counter:
        return "NONE"
    return ",".join(f"{key}:{counter[key]}" for key in sorted(counter))


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
        raise SystemExit("R26 inherited model-constructor marker pair missing")
    scored_ctors = [
        (
            r27.logical_bytes(
                r27.rows_in_interval(order4, begin.mono, end.mono), host_page_size
            ),
            begin,
            end,
        )
        for begin, end in ctor_pairs
    ]
    _, ctor_begin, ctor_end = max(scored_ctors, key=lambda item: item[0])
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
    ctor_400 = [item for item in stream if int(item["size"]) == SIZE_400]

    w13_all = r27.pair_seq(events, W13_BEGIN, W13_END)
    w13 = [
        item
        for item in w13_all
        if r27.interval_overlaps(
            item.begin.mono, item.end.mono, ctor_begin.mono, ctor_end.mono
        )
    ]

    layers_all = r27.pair_layers(events)
    layers = [
        item
        for item in layers_all
        if r27.interval_overlaps(
            item.begin.mono, item.end.mono, ctor_begin.mono, ctor_end.mono
        )
    ]

    unquant_all = r28.pair_unquant(events)
    unquant = [
        item
        for item in unquant_all
        if item.end.mono >= ctor_begin.mono and item.begin.mono <= ctor_end.mono
    ]

    exact_w13: list[tuple[object, object]] = []
    missing_w13: list[int] = []
    multi_w13: list[int] = []
    covered_400 = set()
    for interval in w13:
        rows = [
            row
            for row in ctor_rows
            if interval.begin.mono <= row.mono <= interval.end.mono
            and row.page_count * host_page_size == SIZE_400
        ]
        if len(rows) == 1:
            exact_w13.append((interval, rows[0]))
            covered_400.add(rows[0])
        elif not rows:
            missing_w13.append(interval.seq)
        else:
            multi_w13.append(interval.seq)
            covered_400.update(rows)

    outside_400 = [item for item in ctor_400 if item["row"] not in covered_400]

    pair_rows: list[dict[str, object]] = []
    for interval, row400 in exact_w13:
        item400 = stream_by_row[row400]
        idx400 = int(item400["index"])
        prev = stream[idx400 - 1] if idx400 > 0 else None
        is_800 = prev is not None and int(prev["size"]) == SIZE_800
        prev_row = prev["row"] if prev is not None else None
        prev_mono = prev_row.mono if prev_row is not None else None
        item_unquant = active_one(unquant, prev_mono) if prev_mono is not None else None
        item_layer800 = active_one(layers, prev_mono) if prev_mono is not None else None
        item_layer400 = active_one(layers, row400.mono)
        pair_rows.append(
            {
                "w13": interval,
                "item400": item400,
                "prev": prev,
                "is_800": is_800,
                "unquant": item_unquant,
                "layer800": item_layer800,
                "layer400": item_layer400,
                "delta_ms": (
                    (row400.mono - prev_mono) * 1000.0
                    if prev_mono is not None
                    else None
                ),
                "pre800_to_w13_begin_ms": (
                    (interval.begin.mono - prev_mono) * 1000.0
                    if prev_mono is not None
                    else None
                ),
                "w13_begin_to_400_ms": (row400.mono - interval.begin.mono) * 1000.0,
            }
        )

    preceding_800 = [item for item in pair_rows if item["is_800"]]
    before_w13_begin = [
        item
        for item in preceding_800
        if item["prev"]["row"].mono < item["w13"].begin.mono
    ]

    family_hist: Counter[str] = Counter()
    prefix_hist: Counter[str] = Counter()
    layer_relation_hist: Counter[str] = Counter()
    for item in preceding_800:
        unquant_item = item["unquant"]
        if unquant_item is None:
            family_name = "outside_unquant"
            prefix = "NONE"
        else:
            family_name = r28.family(unquant_item.prefix)
            prefix = unquant_item.prefix
        family_hist[family_name] += 1
        prefix_hist[prefix] += 1

        layer800 = item["layer800"]
        layer400 = item["layer400"]
        if layer800 is None or layer400 is None:
            relation = "outside_layer"
        elif layer800.layer == layer400.layer:
            relation = "same_layer"
        elif layer800.layer + 1 == layer400.layer:
            relation = "800_prev_layer"
        else:
            relation = "other_layer_relation"
        layer_relation_hist[relation] += 1

    dominant_family = "NONE"
    dominant_count = 0
    if family_hist:
        dominant_family, dominant_count = family_hist.most_common(1)[0]
    dominant_pct = 100.0 * dominant_count / len(preceding_800) if preceding_800 else 0.0

    if (
        len(w13) > 0
        and len(exact_w13) == len(w13)
        and len(ctor_400) == len(w13)
        and not outside_400
        and len(preceding_800) == len(w13)
        and len(before_w13_begin) == len(w13)
    ):
        if dominant_pct >= 90.0:
            discriminator = "R30_EXACT_W13_400_WITH_PRECEDING_800_LOCALIZED_TO_SINGLE_USERSPACE_FAMILY"
        else:
            discriminator = "R30_EXACT_W13_400_WITH_IMMEDIATE_PRECEDING_800_MIXED_USERSPACE_PLACEMENT"
    else:
        discriminator = "R30_W13_400_OR_PRECEDING_800_PATTERN_NOT_EXACT"

    pair_delta = [float(item["delta_ms"]) for item in preceding_800]
    pre_to_begin = [float(item["pre800_to_w13_begin_ms"]) for item in preceding_800]
    begin_to_400 = [float(item["w13_begin_to_400_ms"]) for item in preceding_800]

    print("R30_PRE_W13_800_BOUNDARY=BEGIN")
    print("analysis_semantics=posthoc_temporal_boundary_not_causal_ownership")
    print("rm_bytes_semantics=activity_volume_not_resident_ownership")
    print(f"clock_anchor_count={len(offsets)}")
    print(f"selected_w13_count={len(w13)}")
    print(f"constructor_400_request_count={len(ctor_400)}")
    print(f"w13_exact_one_400_count={len(exact_w13)}")
    print(f"w13_missing_400_count={len(missing_w13)}")
    print(f"w13_multi_400_count={len(multi_w13)}")
    print(
        "w13_missing_400_seqs="
        + (",".join(str(v) for v in missing_w13) if missing_w13 else "NONE")
    )
    print(
        "w13_multi_400_seqs="
        + (",".join(str(v) for v in multi_w13) if multi_w13 else "NONE")
    )
    print(f"constructor_400_outside_w13_count={len(outside_400)}")
    print(f"w13_400_immediate_preceding_800_count={len(preceding_800)}")
    print(f"preceding_800_before_w13_begin_count={len(before_w13_begin)}")
    print(f"pair_800_to_400_delta_ms={stats(pair_delta)}")
    print(f"pair_800_to_w13_begin_ms={stats(pre_to_begin)}")
    print(f"pair_w13_begin_to_400_ms={stats(begin_to_400)}")
    print(f"preceding_800_family_histogram={counter_line(family_hist)}")
    print(f"preceding_800_dominant_family={dominant_family}")
    print(f"preceding_800_dominant_family_pct={dominant_pct:.6f}")
    print(f"preceding_800_layer_relation_histogram={counter_line(layer_relation_hist)}")

    for rank, (prefix, count) in enumerate(prefix_hist.most_common(12), start=1):
        print(f"preceding_800.top_prefix_{rank}=count={count} prefix={prefix}")

    for ordinal, item in enumerate(pair_rows, start=1):
        prev = item["prev"]
        prev_idx = int(prev["index"]) if prev is not None else -1
        item400 = item["item400"]
        unquant_item = item["unquant"]
        if unquant_item is None:
            family_name = "outside_unquant"
            prefix = "NONE"
        else:
            family_name = r28.family(unquant_item.prefix)
            prefix = unquant_item.prefix
        print(
            f"pair.{ordinal}=w13_seq={item['w13'].seq} "
            f"pre_stream={prev_idx} pre_size_mib="
            f"{(int(prev['size']) / MIB if prev is not None else -1):.3f} "
            f"w13_400_stream={item400['index']} "
            f"delta_ms={(item['delta_ms'] if item['delta_ms'] is not None else -1):.6f} "
            f"pre_to_w13_begin_ms={(item['pre800_to_w13_begin_ms'] if item['pre800_to_w13_begin_ms'] is not None else -1):.6f} "
            f"w13_begin_to_400_ms={item['w13_begin_to_400_ms']:.6f} "
            f"pre_family={family_name} pre_prefix={prefix} "
            f"pre_layer={layer_desc(item['layer800'])} "
            f"w13_layer={layer_desc(item['layer400'])}"
        )

    print(f"r30_discriminator={discriminator}")
    print("R30_PRE_W13_800_BOUNDARY=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
