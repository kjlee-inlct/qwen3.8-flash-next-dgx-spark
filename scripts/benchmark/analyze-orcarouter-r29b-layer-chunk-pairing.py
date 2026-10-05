#!/usr/bin/env python3
"""Post-hoc R29b 800/400 MiB decoder-layer chunk pairing analysis.

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


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import analyzer: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


r27 = load_module("r27_layer_pairing_base", R27_PATH)

MIB = 1048576
SIZE_400 = 400 * MIB
SIZE_800 = 800 * MIB


def active_layer(layers: list, mono: float):
    active = [item for item in layers if item.begin.mono <= mono <= item.end.mono]
    return active[0] if active else None


def relation(layer800, layer400) -> str:
    if layer800 is None and layer400 is None:
        return "both_outside"
    if layer800 is None:
        return "800_outside"
    if layer400 is None:
        return "400_outside"
    if layer800.layer == layer400.layer:
        return "same_layer"
    if layer800.layer + 1 == layer400.layer:
        return "800_prev_layer"
    if layer800.layer == layer400.layer + 1:
        return "800_next_layer"
    return "different_layer"


def layer_desc(item) -> str:
    if item is None:
        return "NONE"
    return f"{item.layer}:{item.layer_type}"


def stat_line(values: list[float]) -> str:
    if not values:
        return "NONE"
    return (
        f"min={min(values):.6f} median={statistics.median(values):.6f} "
        f"max={max(values):.6f}"
    )


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

    layers_all = r27.pair_layers(events)
    layers = [
        item
        for item in layers_all
        if r27.interval_overlaps(
            item.begin.mono, item.end.mono, ctor_begin.mono, ctor_end.mono
        )
    ]
    layers.sort(key=lambda item: item.layer)

    stream = [
        {
            "index": index,
            "row": row,
            "size": row.page_count * host_page_size,
            "layer": active_layer(layers, row.mono),
        }
        for index, row in enumerate(ctor_rows)
    ]
    rows400 = [item for item in stream if item["size"] == SIZE_400]
    rows800 = [item for item in stream if item["size"] == SIZE_800]

    pair_count = min(len(rows400), len(rows800))
    pairs: list[dict[str, object]] = []
    for ordinal in range(pair_count):
        item800 = rows800[ordinal]
        item400 = rows400[ordinal]
        idx800 = int(item800["index"])
        idx400 = int(item400["index"])
        mono800 = item800["row"].mono
        mono400 = item400["row"].mono
        layer800 = item800["layer"]
        layer400 = item400["layer"]
        pairs.append(
            {
                "ordinal": ordinal + 1,
                "item800": item800,
                "item400": item400,
                "delta_ms": (mono400 - mono800) * 1000.0,
                "stream_delta": idx400 - idx800,
                "relation": relation(layer800, layer400),
            }
        )

    layers_by_number = {item.layer: item for item in layers}
    counts400 = Counter(
        item["layer"].layer for item in rows400 if item["layer"] is not None
    )
    counts800 = Counter(
        item["layer"].layer for item in rows800 if item["layer"] is not None
    )

    expected_layers = set(layers_by_number)
    exact_once_400 = sorted(layer for layer in expected_layers if counts400[layer] == 1)
    missing_400 = sorted(layer for layer in expected_layers if counts400[layer] == 0)
    multi_400 = sorted(layer for layer in expected_layers if counts400[layer] > 1)
    exact_once_800 = sorted(layer for layer in expected_layers if counts800[layer] == 1)
    missing_800 = sorted(layer for layer in expected_layers if counts800[layer] == 0)
    multi_800 = sorted(layer for layer in expected_layers if counts800[layer] > 1)

    before_count = sum(float(item["delta_ms"]) > 0 for item in pairs)
    adjacent_count = sum(int(item["stream_delta"]) == 1 for item in pairs)
    same_layer_count = sum(item["relation"] == "same_layer" for item in pairs)
    prev_layer_count = sum(item["relation"] == "800_prev_layer" for item in pairs)
    relation_hist = Counter(str(item["relation"]) for item in pairs)
    stream_delta_hist = Counter(int(item["stream_delta"]) for item in pairs)
    delta_ms = [float(item["delta_ms"]) for item in pairs]

    pair_layer_type = Counter()
    for item in pairs:
        layer400 = item["item400"]["layer"]
        key = layer400.layer_type if layer400 is not None else "outside_layer"
        pair_layer_type[key] += 1

    strict = (
        len(layers) > 0
        and len(rows400) == len(layers)
        and len(rows800) == len(layers)
        and pair_count == len(layers)
        and len(exact_once_400) == len(layers)
        and before_count == pair_count
        and adjacent_count == pair_count
    )
    two_phase = (
        len(layers) > 0
        and len(rows400) == len(layers)
        and len(rows800) == len(layers)
        and pair_count == len(layers)
        and len(exact_once_400) == len(layers)
        and before_count == pair_count
    )

    if strict:
        discriminator = "R29B_STRICT_800_THEN_400_ADJACENT_PAIR_PER_DECODER_LAYER"
    elif two_phase:
        discriminator = "R29B_800_THEN_400_TWO_PHASE_CADENCE_PER_DECODER_LAYER"
    else:
        discriminator = "R29B_800_400_CADENCE_NOT_STRICTLY_LAYER_PAIRED"

    print("R29B_LAYER_CHUNK_PAIRING=BEGIN")
    print("analysis_semantics=posthoc_temporal_pairing_not_causal_ownership")
    print("rm_bytes_semantics=activity_volume_not_resident_ownership")
    print(f"clock_anchor_count={len(offsets)}")
    print(f"selected_layer_count={len(layers)}")
    print(f"size400_request_count={len(rows400)}")
    print(f"size800_request_count={len(rows800)}")
    print(f"ordinal_pair_count={pair_count}")
    print(f"pair_800_before_400_count={before_count}")
    print(f"pair_adjacent_stream_count={adjacent_count}")
    print(f"pair_same_layer_count={same_layer_count}")
    print(f"pair_800_prev_layer_count={prev_layer_count}")
    print(
        "pair_relation_histogram="
        + (",".join(f"{k}:{v}" for k, v in sorted(relation_hist.items())) or "NONE")
    )
    print(
        "pair_stream_delta_histogram="
        + (",".join(f"{k}:{v}" for k, v in sorted(stream_delta_hist.items())) or "NONE")
    )
    print(f"pair_delta_ms={stat_line(delta_ms)}")
    print(
        "pair_layer_type_histogram="
        + (",".join(f"{k}:{v}" for k, v in sorted(pair_layer_type.items())) or "NONE")
    )

    print(f"layer400.exact_once_count={len(exact_once_400)}")
    print(f"layer400.missing_count={len(missing_400)}")
    print(f"layer400.multi_count={len(multi_400)}")
    print(
        "layer400.missing_layers="
        + (",".join(str(v) for v in missing_400) if missing_400 else "NONE")
    )
    print(
        "layer400.multi_layers="
        + (",".join(str(v) for v in multi_400) if multi_400 else "NONE")
    )

    print(f"layer800.exact_once_count={len(exact_once_800)}")
    print(f"layer800.missing_count={len(missing_800)}")
    print(f"layer800.multi_count={len(multi_800)}")
    print(
        "layer800.missing_layers="
        + (",".join(str(v) for v in missing_800) if missing_800 else "NONE")
    )
    print(
        "layer800.multi_layers="
        + (",".join(str(v) for v in multi_800) if multi_800 else "NONE")
    )

    for layer in sorted(expected_layers):
        item = layers_by_number[layer]
        print(
            f"layer.{layer}=type={item.layer_type} "
            f"count400={counts400[layer]} count800={counts800[layer]}"
        )

    for item in pairs:
        item800 = item["item800"]
        item400 = item["item400"]
        print(
            f"pair.{item['ordinal']}="
            f"800_stream={item800['index']} 400_stream={item400['index']} "
            f"stream_delta={item['stream_delta']} delta_ms={item['delta_ms']:.6f} "
            f"800_layer={layer_desc(item800['layer'])} "
            f"400_layer={layer_desc(item400['layer'])} "
            f"relation={item['relation']}"
        )

    print(f"r29b_discriminator={discriminator}")
    print("R29B_LAYER_CHUNK_PAIRING=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
