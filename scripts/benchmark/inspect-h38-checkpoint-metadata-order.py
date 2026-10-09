#!/usr/bin/env python3
"""Offline H38 18-shard checkpoint NAME/HEADER order and buffer-risk analysis.

No tensor payloads are read. Runtime uses safetensors.safe_open(...).keys()
to reproduce the *declared* default one-file-at-a-time, single-thread order.
This does not prove the installed H38 loader uses that path on every run.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import struct
import sys
from typing import Callable

MAX_HEADER = 64 * 1024 * 1024
EXPECTED_SHARDS = 18
EXPECTED_LAYERS = 48
DIGITS = re.compile(r"(\d+)")
LAYER = re.compile(r"(?:^|\.)(?:layers|h)\.(\d+)(?:\.|$)")
ROUTED_PARTS = (".experts.", ".routed_experts.", ".routed_expert.")
NUMBERED_SHARD = re.compile(r"^model-\d+-of-\d+\.safetensors$")
MAX_RUN_SAMPLES_PER_REVISITED_LAYER = 8


def fail(reason: str) -> None:
    raise ValueError(reason)


def natural_key(path: Path) -> list[object]:
    return [int(v) if v.isdigit() else v for v in DIGITS.split(path.name)]


def layer_id(name: str) -> int | None:
    match = LAYER.search(name)
    return int(match.group(1)) if match else None


def routed_expert(name: str) -> bool:
    return any(token in name.lower() for token in ROUTED_PARTS)


def read_header(path: Path) -> dict[str, int]:
    """Read exactly 8 + N bytes of the safetensors header, no tensor body."""
    total_size = path.stat().st_size
    with path.open("rb") as handle:
        prefix = handle.read(8)
        if len(prefix) != 8:
            fail(f"short_safetensors_prefix:{path.name}")
        (length,) = struct.unpack("<Q", prefix)
        if not 2 <= length <= MAX_HEADER or 8 + length > total_size:
            fail(f"invalid_header_bounds:{path.name}")
        header = handle.read(length)
        if len(header) != length:
            fail(f"truncated_safetensors_header:{path.name}")
    try:
        raw = json.loads(header)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid_header_json:{path.name}") from exc
    if not isinstance(raw, dict):
        fail(f"invalid_header_root:{path.name}")
    raw.pop("__metadata__", None)
    data_length = total_size - 8 - length
    sizes: dict[str, int] = {}
    offsets: list[tuple[int, int]] = []
    for name, meta in raw.items():
        if (not isinstance(name, str) or not isinstance(meta, dict)
                or not isinstance(meta.get("dtype"), str)
                or not isinstance(meta.get("shape"), list)):
            fail(f"invalid_tensor_meta:{path.name}")
        rng = meta.get("data_offsets")
        if (not isinstance(rng, list) or len(rng) != 2
                or any(type(n) is not int for n in rng)
                or not 0 <= rng[0] <= rng[1] <= data_length):
            fail(f"invalid_tensor_offsets:{path.name}")
        if any(type(dim) is not int or dim < 0 for dim in meta["shape"]):
            fail(f"invalid_tensor_shape:{path.name}")
        sizes[name] = rng[1] - rng[0]
        offsets.append((rng[0], rng[1]))
    offsets.sort()
    for (_, end), (next_start, _) in zip(offsets, offsets[1:]):
        if end > next_start:
            fail(f"overlapping_tensor_offsets:{path.name}")
    return sizes


def resolve_shards(root: Path) -> tuple[list[Path], dict[str, str]]:
    if not root.is_dir():
        fail("checkpoint_path_not_directory")
    index = root / "model.safetensors.index.json"
    if not index.is_file():
        fail("missing_model_safetensors_index")
    if index.stat().st_size > MAX_HEADER:
        fail("index_json_too_large")
    mapping = json.loads(index.read_text(encoding="utf-8"))
    if not isinstance(mapping, dict) or not isinstance(mapping.get("weight_map"), dict):
        fail("missing_index_weight_map")
    weight_map = mapping["weight_map"]
    if not weight_map or any(
        not isinstance(key, str) or not isinstance(value, str)
        or not value.endswith(".safetensors") or Path(value).name != value
        for key, value in weight_map.items()
    ):
        fail("unsafe_or_invalid_index_entries")
    filenames = sorted(set(weight_map.values()), key=lambda v: natural_key(Path(v)))
    if len(filenames) != EXPECTED_SHARDS:
        fail(f"shard_count_not_{EXPECTED_SHARDS}:{len(filenames)}")
    paths = [root / name for name in filenames]
    if any(not p.is_file() or p.is_symlink() for p in paths):
        fail("missing_or_symlinked_shard")
    extras = {p.name for p in root.glob("*.safetensors")} - set(filenames)
    if extras:
        fail("unindexed_shard_files_present")
    return paths, weight_map


def scan_checkpoint(
    root: Path,
    key_reader: Callable[[Path], list[str]],
) -> dict[str, object]:
    paths, index = resolve_shards(root)
    all_seen: set[str] = set()
    ordered: list[tuple[str, int, int | None, bool]] = []
    per_shard: list[dict[str, object]] = []
    for path in paths:
        sizes = read_header(path)
        names = key_reader(path)
        if len(names) != len(sizes) or len(set(names)) != len(names) or set(names) != set(sizes):
            fail(f"safe_open_header_key_mismatch:{path.name}")
        if any(name in all_seen for name in names):
            fail(f"duplicate_tensor_across_shards:{path.name}")
        if any(index.get(name) != path.name for name in names):
            fail(f"index_header_mapping_mismatch:{path.name}")
        all_seen.update(names)
        routed_in_file = [n for n in names if routed_expert(n)]
        per_shard.append({
            "name": path.name, "tensor_count": len(names),
            "routed_count": len(routed_in_file),
            "routed_layer_ids": sorted({
                lid for n in routed_in_file
                if (lid := layer_id(n)) is not None
            }),
            "is_numbered_model_shard": bool(NUMBERED_SHARD.fullmatch(path.name)),
        })
        ordered.extend((name, sizes[name], layer_id(name), routed_expert(name))
                       for name in names)
    if all_seen != set(index):
        fail("index_contains_missing_tensor_keys")

    routed = [(i, name, size, lid) for i, (name, size, lid, expert)
              in enumerate(ordered) if expert]
    if not routed:
        fail("no_routed_expert_tensor_keys")
    if any(lid is None for _, _, _, lid in routed):
        fail("routed_expert_without_layer_id")

    layer_sequence = [int(lid) for _, _, _, lid in routed]
    observed = set(layer_sequence)
    expected = set(range(EXPECTED_LAYERS))
    last_routed: dict[int, int] = {}
    last_all: dict[int, int] = {}
    first_routed: dict[int, int] = {}
    for i, (_, size, lid, expert) in enumerate(ordered):
        if lid is not None:
            last_all[lid] = i
            if expert:
                last_routed[lid] = i
                first_routed.setdefault(lid, i)
    runs = [layer_sequence[0]]
    for lid in layer_sequence[1:]:
        if lid != runs[-1]:
            runs.append(lid)
    counts = Counter(runs)
    revisited = sorted(lid for lid, cnt in counts.items() if cnt > 1)

    # Each run spans consecutive routed keys (non-routed keys may interleave);
    # report *bounded* first/last key and owning shard for repeated layers.
    run_spans: dict[int, list[dict[str, object]]] = {}
    run_start = 0
    for pos in range(1, len(routed) + 1):
        if pos < len(routed) and routed[pos][3] == routed[run_start][3]:
            continue
        first_key = routed[run_start][1]
        last_key = routed[pos - 1][1]
        lid = int(routed[run_start][3])
        spans = run_spans.setdefault(lid, [])
        if len(spans) < MAX_RUN_SAMPLES_PER_REVISITED_LAYER:
            spans.append({
                "first_shard": index[first_key],
                "last_shard": index[last_key],
                "first_key": first_key,
                "last_key": last_key,
                "routed_key_count": pos - run_start,
                "first_global_tensor_ordinal": routed[run_start][0],
                "last_global_tensor_ordinal": routed[pos - 1][0],
            })
        run_start = pos
    revisit_locations = [
        {
            "layer": lid,
            "total_run_count": counts[lid],
            "run_sample_count": len(run_spans[lid]),
            "runs_truncated": counts[lid] > len(run_spans[lid]),
            "runs": run_spans[lid],
        }
        for lid in revisited
    ]

    # Optional diagnostic using only indexed numbered base-model shards.
    # This NEVER alters the full-stream strict gate or silently drops MTP.
    base_layers = [
        lid for _, key, _, lid in routed
        if NUMBERED_SHARD.fullmatch(index[key])
    ]
    base_runs = [base_layers[0]] if base_layers else []
    for lid in base_layers[1:]:
        if lid != base_runs[-1]:
            base_runs.append(lid)
    base_counts = Counter(base_runs)
    base_revisited = sorted(lid for lid, n in base_counts.items() if n > 1)

    # Interval concurrency over the FULL stream, not filtered expert-only indices.
    events: list[tuple[int, int]] = []
    for lid, first in first_routed.items():
        events.extend(((first, +1), (last_routed[lid] + 1, -1)))
    active = peak_active = 0
    for _, delta in sorted(events):
        active += delta
        peak_active = max(peak_active, active)

    # Two static buffer scenarios; neither predicts actual loader retention.
    # "routed-only" frees when the last routed key arrives (optimistic).
    # "last-layer" frees when the last key with any layer prefix arrives.
    def hypothetical_peak(last: dict[int, int]) -> int:
        buffered: dict[int, int] = {}
        total = peak = 0
        for i, (_, size, lid, expert) in enumerate(ordered):
            if expert and lid is not None:
                buffered[lid] = buffered.get(lid, 0) + size
                total += size
                peak = max(total, peak)
            if lid is not None and last.get(lid) == i:
                total -= buffered.pop(lid, 0)
        return peak

    passed = observed == expected and not revisited and peak_active == 1
    return {
        "status": "PASS" if passed else "FAIL",
        "semantics": "metadata_only_safetensors_key_order_assuming_default_single_thread_loader",
        "index_verified": True,
        "shard_count": len(paths),
        "numbered_model_shard_count": sum(
            bool(NUMBERED_SHARD.fullmatch(path.name)) for path in paths
        ),
        "auxiliary_shard_names": [
            path.name for path in paths
            if not NUMBERED_SHARD.fullmatch(path.name)
        ],
        "base_model_only_revisited_layers_diagnostic": base_revisited,
        "base_model_only_routed_layer_count_diagnostic": len(set(base_layers)),
        "routed_expert_revisit_run_locations": revisit_locations,
        "tensor_count": len(ordered),
        "routed_expert_tensor_count": len(routed),
        "routed_expert_layer_count": len(observed),
        "routed_expert_revisited_layers": revisited,
        "routed_expert_max_overlapping_intervals": peak_active,
        "missing_layers": sorted(expected - observed),
        "unexpected_layers": sorted(observed - expected),
        "routed_weight_total_bytes": sum(size for _, _, size, _ in routed),
        "scenario_peak_routed_bytes_release_at_last_routed_key":
            hypothetical_peak(last_routed),
        "scenario_peak_routed_bytes_release_at_last_any_layer_key":
            hypothetical_peak(last_all),
        "per_shard": per_shard,
        "diagnostic_base_only_scope_can_override_full_gate": False,
        "exact_h38_loader_order_contract_verified": False,
        "all_layerwise_weight_buffers_bounded": False,
        "meta_materialization_proven": False,
        "ct_meta_patch_implemented": False,
        "host_stability_qualified": False,
    }


def safetensors_reader(path: Path) -> list[str]:
    from safetensors import safe_open  # lightweight metadata interface
    with safe_open(str(path), framework="pt", device="cpu") as handle:
        return list(handle.keys())  # get_tensor/get_slice never called


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    try:
        result = scan_checkpoint(args.model_dir, safetensors_reader)
    except (OSError, ValueError, UnicodeError, ImportError, json.JSONDecodeError) as exc:
        print(f"H38_CKPT_METADATA_ORDER=INVALID reason={exc}", file=sys.stderr)
        return 2
    print("H38_CKPT_METADATA_ORDER=BEGIN")
    print(json.dumps(result, sort_keys=True, indent=2))
    print("H38_CKPT_METADATA_ORDER=END")
    print(f"H38_CKPT_METADATA_ORDER_GATE={result['status']}")
    if args.json_output:
        args.json_output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                                    encoding="utf-8")
    return 0 if result["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
