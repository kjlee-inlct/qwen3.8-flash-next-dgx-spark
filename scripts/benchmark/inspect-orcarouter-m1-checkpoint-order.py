#!/usr/bin/env python3
"""Read-only M1 feasibility check for the actual safetensors iteration order.

vLLM v0.29's default single-thread safetensors loader iterates:
  1. checkpoint files in natural-sort order;
  2. ``safe_open(file).keys()`` within each file.

M1's online layerwise loader buffers checkpoint tensors until a routed-expert
layer is complete. This inspector reproduces that name order without loading
any tensor payload and checks whether routed-expert keys for each decoder layer
arrive in one contiguous run. A PASS therefore means M1 should not need to keep
checkpoint buffers open for multiple routed-expert layers at once under the
matched default single-thread safetensors path.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from safetensors import safe_open


LAYER_RE = re.compile(r"(?:^|\.)(?:layers|h)\.(\d+)(?:\.|$)")
DIGIT_RE = re.compile(r"(\d+)")


def natural_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part for part in DIGIT_RE.split(path.name)]


def layer_id(name: str) -> int | None:
    match = LAYER_RE.search(name)
    return int(match.group(1)) if match else None


def is_routed_expert_key(name: str) -> bool:
    # Qwen-family raw checkpoints normally expose routed experts under
    # ``.experts.``. Keep two narrow aliases for model variants while avoiding
    # shared-expert/router tensors that do not belong to RoutedExperts packed
    # w13/w2 storage.
    lowered = name.lower()
    return any(token in lowered for token in (".experts.", ".routed_experts.", ".routed_expert."))


def resolve_files(model_dir: Path) -> list[Path]:
    files = list(model_dir.glob("*.safetensors"))
    index = model_dir / "model.safetensors.index.json"
    if index.is_file():
        weight_map = json.loads(index.read_text(encoding="utf-8")).get("weight_map", {})
        referenced = {model_dir / str(value) for value in weight_map.values()}
        files = [path for path in files if path in referenced]
    return sorted(files, key=natural_key)


def contiguous_runs(layer_sequence: list[int]) -> list[tuple[int, int, int]]:
    if not layer_sequence:
        return []
    result: list[tuple[int, int, int]] = []
    start = 0
    current = layer_sequence[0]
    for index, value in enumerate(layer_sequence[1:], start=1):
        if value != current:
            result.append((current, start, index - 1))
            current = value
            start = index
    result.append((current, start, len(layer_sequence) - 1))
    return result


def max_overlapping_intervals(first: dict[int, int], last: dict[int, int]) -> int:
    if not first:
        return 0
    events: list[tuple[int, int]] = []
    for layer in first:
        events.append((first[layer], 1))
        events.append((last[layer] + 1, -1))
    # Close-before-open at the same logical position.
    events.sort(key=lambda item: (item[0], item[1]))
    active = 0
    peak = 0
    for _, delta in events:
        active += delta
        peak = max(peak, active)
    return peak


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model_dir", type=Path)
    parser.add_argument("--expected-layers", type=int, default=48)
    parser.add_argument("--sample-count", type=int, default=12)
    args = parser.parse_args()

    model_dir = args.model_dir.resolve()
    files = resolve_files(model_dir)
    if not files:
        raise SystemExit(f"M1_CHECKPOINT_ORDER=FAIL reason=no_safetensors dir={model_dir}")

    all_tensor_count = 0
    all_layer_ids: set[int] = set()
    expert_names: list[str] = []
    expert_layers: list[int] = []
    first: dict[int, int] = {}
    last: dict[int, int] = {}
    per_file_expert = Counter()

    for file_index, path in enumerate(files):
        with safe_open(str(path), framework="pt", device="cpu") as handle:
            keys = list(handle.keys())
        all_tensor_count += len(keys)
        for name in keys:
            lid = layer_id(name)
            if lid is not None:
                all_layer_ids.add(lid)
            if lid is None or not is_routed_expert_key(name):
                continue
            pos = len(expert_layers)
            expert_names.append(name)
            expert_layers.append(lid)
            first.setdefault(lid, pos)
            last[lid] = pos
            per_file_expert[file_index] += 1

    if not expert_layers:
        print("M1_CHECKPOINT_ORDER=FAIL")
        print("reason=no_routed_expert_keys")
        print(f"file_count={len(files)}")
        print(f"tensor_count={all_tensor_count}")
        print(f"decoder_layer_count={len(all_layer_ids)}")
        return 2

    runs = contiguous_runs(expert_layers)
    run_count_by_layer = Counter(layer for layer, _, _ in runs)
    revisited = sorted(layer for layer, count in run_count_by_layer.items() if count > 1)
    layer_counts = Counter(expert_layers)
    missing = sorted(set(range(args.expected_layers)) - set(layer_counts))
    extra = sorted(set(layer_counts) - set(range(args.expected_layers)))
    max_open = max_overlapping_intervals(first, last)

    gate = (
        len(layer_counts) == args.expected_layers
        and not missing
        and not extra
        and not revisited
        and max_open == 1
    )

    print("M1_CHECKPOINT_ORDER=BEGIN")
    print("semantics=read_only_default_single_thread_safetensors_name_order")
    print(f"model_dir={model_dir}")
    print(f"file_count={len(files)}")
    print(f"tensor_count={all_tensor_count}")
    print(f"decoder_layer_count={len(all_layer_ids)}")
    print(f"routed_expert_tensor_count={len(expert_layers)}")
    print(f"routed_expert_layer_count={len(layer_counts)}")
    print(f"routed_expert_run_count={len(runs)}")
    print(f"routed_expert_revisited_layer_count={len(revisited)}")
    print(
        "routed_expert_revisited_layers="
        + (",".join(map(str, revisited)) if revisited else "NONE")
    )
    print(f"routed_expert_max_open_layer_intervals={max_open}")
    print("missing_expected_layers=" + (",".join(map(str, missing)) if missing else "NONE"))
    print("extra_layers=" + (",".join(map(str, extra)) if extra else "NONE"))
    print(
        "routed_expert_tensor_count_per_layer_min="
        + str(min(layer_counts.values()))
    )
    print(
        "routed_expert_tensor_count_per_layer_max="
        + str(max(layer_counts.values()))
    )
    file_counts = [per_file_expert[index] for index in range(len(files))]
    print("routed_expert_tensor_count_per_file=" + ",".join(map(str, file_counts)))
    for index, name in enumerate(expert_names[: args.sample_count]):
        print(f"sample.{index}={name}")
    print("M1_CHECKPOINT_ORDER=END")
    print(f"M1_CHECKPOINT_ORDER_GATE={'PASS' if gate else 'FAIL'}")
    print("model_restart=NO")
    print("candidate_launch=NO")
    print("tensor_payload_read=NO")
    print("evidence_mutation=NO")
    return 0 if gate else 3


if __name__ == "__main__":
    raise SystemExit(main())
