#!/usr/bin/env python3
"""Pure-stdlib counterexamples for aggregate layerwise copy-count completion.

A SMALL TOY MODEL of the documented vLLM v0.29 count/threshold policy.
This is NOT an H38 execution, not a trace of 512 routed experts, not a
prediction of real checkpoint ordering and NOT a memory-size measurement.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Mapping, Sequence

# Names match eight H38 CT registrations; element counts are deliberately
# tiny SYNTHETIC numbers, not real shapes, on-disk bytes or GPU allocations.
REQUIRED: dict[str, int] = {
    "w13_weight_packed": 8,
    "w2_weight_packed": 4,
    "w13_weight_scale": 2,
    "w2_weight_scale": 2,
    "w13_weight_global_scale": 1,
    "w2_weight_global_scale": 1,
    "w13_input_global_scale": 1,
    "w2_input_global_scale": 1,
}


@dataclass(frozen=True)
class CopyEvent:
    """A synthetic copied destination subrange; [start, start + elements)."""

    parameter: str
    start: int
    elements: int
    shard: str


def covered_size(intervals: Sequence[tuple[int, int]]) -> int:
    """Count unique covered indices; unlike CopyCounter, deduplicate overlap."""
    if not intervals:
        return 0
    ordered = sorted(intervals)
    start, end = ordered[0]
    total = 0
    for lo, hi in ordered[1:]:
        if lo <= end:
            end = max(end, hi)
        else:
            total += end - start
            start, end = lo, hi
    return total + end - start


def simulate(required: Mapping[str, int],
             events: Sequence[CopyEvent]) -> dict[str, object]:
    """Compare copy-based aggregate with per-parameter unique coverage.

    Implements a conservative *abstraction*: per-call count = min(copied,
    param.numel), aggregated until the first threshold processing event.
    After that synthetic processing, further calls are classified ignored.
    If a nonempty incomplete layer remains, end-of-stream finalization
    mirrors the observed non-attention partial finalizer branch. No torch.
    """
    if not required or any(not isinstance(n, int) or n <= 0
                           for n in required.values()):
        raise ValueError("positive_synthetic_parameter_sizes_required")
    target = sum(required.values())
    credited = 0
    seen: dict[str, list[tuple[int, int]]] = {name: [] for name in required}
    processing_index: int | None = None
    ignored: list[int] = []
    for i, event in enumerate(events):
        if event.parameter not in required:
            raise ValueError(f"unknown_parameter:{event.parameter}")
        maximum = required[event.parameter]
        if (event.start < 0 or event.elements <= 0
                or event.start + event.elements > maximum):
            raise ValueError(f"invalid_copy_range:{event.parameter}")
        if processing_index is not None:
            ignored.append(i)
            continue
        credited += min(event.elements, maximum)
        seen[event.parameter].append((event.start, event.start + event.elements))
        if credited >= target:
            processing_index = i

    unique = {name: covered_size(seen[name]) for name in required}
    missing = {name: required[name] - unique[name]
               for name in required if unique[name] < required[name]}
    partial_end_processing = processing_index is None and credited > 0
    return {
        "synthetic_only": True,
        "required_elements": target,
        "credited_elements": credited,
        "uniquely_covered_elements": sum(unique.values()),
        "all_parameters_covered": not missing,
        "missing_elements_by_parameter": missing,
        "threshold_processing_event": processing_index,
        "partial_end_finalizer_possible": partial_end_processing,
        "ignored_event_indices_after_processing": ignored,
        "safe_real_memory_bound_proven": False,
        "actual_h38_ct_loader_behavior_proven": False,
    }


def normal_events(layer: str) -> list[CopyEvent]:
    """Interleave an artificial shard split while ultimately covering all."""
    prefix = f"synthetic-layer-{layer}"
    return (
        [CopyEvent("w13_weight_packed", 0, 4, prefix + "-shard-a")]
        + [CopyEvent(name, 0, count, prefix + "-intermediate")
           for name, count in REQUIRED.items() if name != "w13_weight_packed"]
        + [CopyEvent("w13_weight_packed", 4, 4, prefix + "-shard-b")]
    )


def cases() -> dict[str, dict[str, object]]:
    """Deterministic witness cases; only layer labels echo historical revisits."""
    complete = normal_events("8")
    duplicate_whole = (
        [CopyEvent("w13_weight_packed", 0, 8, "synthetic-shard-4"),
         CopyEvent("w13_weight_packed", 0, 8, "synthetic-shard-4-retry"),
         CopyEvent("w2_weight_packed", 0, 4, "synthetic-shard-5")]
        + [CopyEvent(n, 0, count, "synthetic-shard-6")
           for n, count in REQUIRED.items()
           if n not in ("w13_weight_packed", "w2_weight_packed")]
    )
    duplicate_half = (
        [CopyEvent("w13_weight_packed", 0, 4, "synthetic-shard-5"),
         CopyEvent("w13_weight_packed", 0, 4, "synthetic-shard-5-retry")]
        + [CopyEvent(n, 0, count, "synthetic-shard-6")
           for n, count in REQUIRED.items() if n != "w13_weight_packed"]
    )
    return {
        "split_layer_8_complete": simulate(REQUIRED, complete),
        "split_layer_11_complete": simulate(REQUIRED, normal_events("11")),
        "duplicate_packed_early_completion": simulate(REQUIRED, duplicate_whole),
        "duplicate_partial_early_completion": simulate(REQUIRED, duplicate_half),
        "split_layer_8_partial_end_finalizer": simulate(REQUIRED, complete[:-1]),
    }


def main() -> int:
    results = cases()
    assert results["split_layer_8_complete"]["all_parameters_covered"]
    assert results["split_layer_11_complete"]["all_parameters_covered"]
    assert not results["duplicate_packed_early_completion"]["all_parameters_covered"]
    assert results["duplicate_packed_early_completion"]["threshold_processing_event"] is not None
    assert not results["duplicate_partial_early_completion"]["all_parameters_covered"]
    assert results["split_layer_8_partial_end_finalizer"]["partial_end_finalizer_possible"]
    print("H38_CT_SYNTHETIC_COUNTEREXAMPLES=PASS")
    print(json.dumps(results, indent=2, sort_keys=True))
    print("REAL_H38_LOADER_COMPLETENESS=UNVERIFIED")
    print("REAL_H38_MEMORY_PEAK=UNVERIFIED")
    print("GPU_OR_MODEL_EXECUTION=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
