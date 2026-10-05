#!/usr/bin/env python3
"""Post-hoc R29 global constructor RM chunk-cadence analysis.

Reads only preserved R28 evidence. It does not launch a model, mutate the
managed service, add probes, or change kernel/runtime state.

RM bytes are logical direct-RM allocation activity volume, not exact resident
ownership. Marker alignment is temporal localization, not causal proof.
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import statistics
import sys
from collections import Counter, defaultdict

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


r27 = load_module("r27_linear_overlap_base", R27_PATH)
r28 = load_module("r28_unquant_overlap_base", R28_PATH)

MIB = 1048576
LARGE_MIN_BYTES = 256 * MIB


def fmt_mib(value: int) -> str:
    return f"{value / MIB:.3f}"


def hist_line(counter: Counter[int]) -> str:
    if not counter:
        return "NONE"
    return ",".join(
        f"{fmt_mib(size)}:{count}" for size, count in sorted(counter.items())
    )


def interval_contains(item, mono: float) -> bool:
    return item.begin.mono <= mono <= item.end.mono


def active_items(items: list, mono: float) -> list:
    return [item for item in items if interval_contains(item, mono)]


def nearest_unquant(unquant: list, mono: float):
    active = active_items(unquant, mono)
    if active:
        return "inside", active[0]
    previous = [item for item in unquant if item.end.mono <= mono]
    following = [item for item in unquant if item.begin.mono >= mono]
    prev_item = max(previous, key=lambda item: item.end.mono) if previous else None
    next_item = min(following, key=lambda item: item.begin.mono) if following else None
    if prev_item is None:
        return "next", next_item
    if next_item is None:
        return "prev", prev_item
    prev_gap = mono - prev_item.end.mono
    next_gap = next_item.begin.mono - mono
    return ("prev", prev_item) if prev_gap <= next_gap else ("next", next_item)


def classify_region(mono: float, moe: list, unquant: list) -> str:
    in_moe = bool(active_items(moe, mono))
    in_unquant = bool(active_items(unquant, mono))
    if in_moe and in_unquant:
        return "modelopt_moe+unquant_linear"
    if in_moe:
        return "modelopt_moe"
    if in_unquant:
        return "unquant_linear"
    return "other_ctor"


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
    ctor_bytes, ctor_begin, ctor_end = max(scored_ctors, key=lambda item: item[0])
    ctor_rows = r27.rows_in_interval(order4, ctor_begin.mono, ctor_end.mono)

    moe_all = r27.pair_seq(events, r27.MOE_BEGIN, r27.MOE_END)
    moe = [
        item
        for item in moe_all
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

    rows: list[dict[str, object]] = []
    for index, row in enumerate(ctor_rows):
        size = row.page_count * host_page_size
        active_layers = active_items(layers, row.mono)
        layer = active_layers[0] if active_layers else None
        nearest_kind, nearest = nearest_unquant(unquant, row.mono)
        region = classify_region(row.mono, moe, unquant)
        rows.append(
            {
                "index": index,
                "row": row,
                "size": size,
                "region": region,
                "layer": layer,
                "nearest_kind": nearest_kind,
                "nearest": nearest,
            }
        )

    size_hist = Counter(int(item["size"]) for item in rows)
    region_counts = Counter(str(item["region"]) for item in rows)
    region_bytes = Counter()
    for item in rows:
        region_bytes[str(item["region"])] += int(item["size"])

    repeated_large_sizes = [
        size
        for size, count in sorted(size_hist.items())
        if size >= LARGE_MIN_BYTES and count >= 2
    ]
    large_rows = [item for item in rows if int(item["size"]) in repeated_large_sizes]

    print("R29_GLOBAL_RM_CHUNK_CADENCE=BEGIN")
    print("analysis_semantics=posthoc_temporal_pattern_not_causal_ownership")
    print("rm_bytes_semantics=activity_volume_not_resident_ownership")
    print(f"clock_anchor_count={len(offsets)}")
    print(f"model_ctor.marker_pair_count={len(ctor_pairs)}")
    print(f"model_ctor.duration_s={ctor_end.mono - ctor_begin.mono:.6f}")
    print(f"constructor_order4_request_count={len(ctor_rows)}")
    print(f"constructor_order4_activity_mib={ctor_bytes / MIB:.3f}")
    print(f"constructor_request_size_histogram_mib={hist_line(size_hist)}")
    print(
        "repeated_large_request_sizes_mib="
        + (
            ",".join(fmt_mib(size) for size in repeated_large_sizes)
            if repeated_large_sizes
            else "NONE"
        )
    )

    for region in sorted(region_counts):
        print(f"region.{region}.request_count={region_counts[region]}")
        print(f"region.{region}.activity_mib={region_bytes[region] / MIB:.3f}")

    spanning_sizes: list[int] = []
    for number, size in enumerate(repeated_large_sizes, start=1):
        selected = [item for item in rows if int(item["size"]) == size]
        regions = Counter(str(item["region"]) for item in selected)
        layer_types = Counter(
            item["layer"].layer_type if item["layer"] is not None else "outside_layer"
            for item in selected
        )
        if len(regions) >= 2:
            spanning_sizes.append(size)
        print(
            f"chunk.{number}=size_mib={fmt_mib(size)} count={len(selected)} "
            + "regions="
            + ",".join(f"{name}:{count}" for name, count in sorted(regions.items()))
            + " layer_types="
            + ",".join(
                f"{name}:{count}" for name, count in sorted(layer_types.items())
            )
        )

        monos = [item["row"].mono for item in selected]
        time_gaps = [b - a for a, b in zip(monos, monos[1:])]
        stream_indices = [int(item["index"]) for item in selected]
        request_gaps = [b - a - 1 for a, b in zip(stream_indices, stream_indices[1:])]
        if time_gaps:
            print(
                f"chunk.{number}.interarrival_ms="
                f"min={min(time_gaps) * 1000.0:.6f} "
                f"median={statistics.median(time_gaps) * 1000.0:.6f} "
                f"max={max(time_gaps) * 1000.0:.6f}"
            )
            print(
                f"chunk.{number}.intervening_order4_requests="
                f"min={min(request_gaps)} median={statistics.median(request_gaps):.3f} "
                f"max={max(request_gaps)}"
            )

        for event_index, item in enumerate(selected[:24], start=1):
            rm_row = item["row"]
            layer = item["layer"]
            nearest = item["nearest"]
            nearest_kind = str(item["nearest_kind"])
            if nearest is None:
                nearest_desc = "NONE"
            else:
                nearest_desc = f"{nearest_kind}:{nearest.seq}:{nearest.prefix}"
            if layer is None:
                layer_desc = "NONE"
            else:
                layer_desc = f"{layer.layer}:{layer.layer_type}"
            print(
                f"chunk.{number}.event.{event_index}="
                f"mono={rm_row.mono:.9f} stream_index={item['index']} "
                f"region={item['region']} layer={layer_desc} "
                f"nearest_unquant={nearest_desc}"
            )

    if spanning_sizes:
        discriminator = "R29_REPEATED_LARGE_RM_CHUNKS_SPAN_MULTIPLE_CONSTRUCTOR_BOUNDARIES"
    elif repeated_large_sizes:
        discriminator = "R29_REPEATED_LARGE_RM_CHUNKS_REGION_LOCALIZED"
    else:
        discriminator = "R29_NO_REPEATED_LARGE_RM_CHUNK_PATTERN"

    print(
        "spanning_repeated_large_request_sizes_mib="
        + (",".join(fmt_mib(size) for size in spanning_sizes) if spanning_sizes else "NONE")
    )
    print(f"r29_discriminator={discriminator}")
    print("R29_GLOBAL_RM_CHUNK_CADENCE=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
