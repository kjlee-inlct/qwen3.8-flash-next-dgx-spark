#!/usr/bin/env python3
"""Index-ONLY H38 OrcaRouter CT key -> expert/shard candidate inventory.

No tensor payload, tensor header, torch, vLLM, CUDA or safetensors import.
Reuses existing read-only shard/index path guard from the qualified metadata
analyzer; results DO NOT prove callbacks, parameter values or runtime loading.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Mapping

HERE = Path(__file__).resolve().parent
ORDER_INSPECTOR = HERE / "inspect-h38-checkpoint-metadata-order.py"
DEFAULT_LAYERS = 48
DEFAULT_EXPERTS = 512
SAMPLE_LIMIT = 12

# All keys must be classified before any claim of per-expert metadata coverage.
BASE_PREFIX = "model.language_model.layers."
BASE_EXPERT = re.compile(
    r"^model\.language_model\.layers\.(\d+)\.mlp\.experts\."
    r"(\d+)\.(gate_proj|up_proj|down_proj)\."
    r"(weight|weight_scale|weight_global_scale)$"
)
PROJECTION_SHARDS = {"gate_proj": "w1", "up_proj": "w3", "down_proj": "w2"}
COMPONENT_PARAMETERS = {
    ("gate_proj", "weight"): "w13_weight_packed",
    ("up_proj", "weight"): "w13_weight_packed",
    ("down_proj", "weight"): "w2_weight_packed",
    ("gate_proj", "weight_scale"): "w13_weight_scale",
    ("up_proj", "weight_scale"): "w13_weight_scale",
    ("down_proj", "weight_scale"): "w2_weight_scale",
    ("gate_proj", "weight_global_scale"): "w13_weight_global_scale",
    ("up_proj", "weight_global_scale"): "w13_weight_global_scale",
    ("down_proj", "weight_global_scale"): "w2_weight_global_scale",
}
ALL_SLOTS = frozenset(COMPONENT_PARAMETERS)
EXPECTED_CT_INPUT_SCALES = (
    "w13_input_global_scale", "w2_input_global_scale"
)


def fail(reason: str) -> None:
    raise ValueError(reason)


def read_index(root: Path) -> tuple[dict[str, str], str]:
    """Parse only bounded model index JSON and reject duplicate object keys."""
    path = root / "model.safetensors.index.json"
    if not path.is_file() or path.is_symlink():
        fail("index_missing_or_symlinked")
    if path.stat().st_size > 64 * 1024 * 1024:
        fail("index_exceeds_64m")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()

    def reject_duplicates(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                fail("duplicate_json_field:" + key[:80])
            result[key] = value
        return result

    data = json.loads(raw, object_pairs_hook=reject_duplicates)
    if not isinstance(data, dict) or not isinstance(data.get("weight_map"), dict):
        fail("invalid_index_weight_map")
    weight_map = data["weight_map"]
    if not weight_map or any(not isinstance(k, str) or
                             not isinstance(v, str) for k, v in weight_map.items()):
        fail("invalid_key_file_mapping")
    return weight_map, digest


def load_qualified_shards_guard():
    """Use the existing no-payload index/shard consistency helper verbatim."""
    spec = importlib.util.spec_from_file_location("h38_metadata_index_guard", ORDER_INSPECTOR)
    if spec is None or spec.loader is None:
        fail("existing_order_inspector_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.resolve_shards


def analyze(weight_map: Mapping[str, str], *, layers: int = DEFAULT_LAYERS,
            experts: int = DEFAULT_EXPERTS) -> dict[str, object]:
    """Analyze keys only; no inferred callbacks or actual memory coverage."""
    if layers <= 0 or experts <= 0:
        fail("positive_grid_required")
    if not weight_map or any(not isinstance(k, str) or
                             not isinstance(v, str) for k, v in weight_map.items()):
        fail("invalid_mapping")
    seen: dict[tuple[int, int], set[tuple[str, str]]] = defaultdict(set)
    files_by_expert: dict[tuple[int, int], set[str]] = defaultdict(set)
    per_layer_file: dict[int, Counter[str]] = defaultdict(Counter)
    parameter_counter: Counter[str] = Counter()
    unclassified: list[str] = []
    unsupported: list[str] = []
    duplicates: list[str] = []
    extra_input_scale_keys = 0
    base_candidate_total = 0
    mtp_key_count = 0
    for name, filename in weight_map.items():
        if name.startswith("mtp."):
            mtp_key_count += 1
        if "input_scale" in name or "input_global_scale" in name:
            extra_input_scale_keys += 1
        # Treat any base-model routed expert key not matching the qualified
        # nine-slot scheme as an unresolved input, never silently exclude it.
        if not name.startswith(BASE_PREFIX) or ".mlp.experts." not in name:
            continue
        base_candidate_total += 1
        matched = BASE_EXPERT.fullmatch(name)
        if not matched:
            if len(unclassified) < SAMPLE_LIMIT:
                unclassified.append(name)
            continue
        lid, expert_id = int(matched[1]), int(matched[2])
        proj, component = matched[3], matched[4]
        if lid >= layers or expert_id >= experts:
            if len(unsupported) < SAMPLE_LIMIT:
                unsupported.append(name)
            continue
        slot = (proj, component)
        owner = (lid, expert_id)
        if slot in seen[owner]:
            if len(duplicates) < SAMPLE_LIMIT:
                duplicates.append(name)
            continue
        seen[owner].add(slot)
        files_by_expert[owner].add(filename)
        per_layer_file[lid][filename] += 1
        parameter_counter[COMPONENT_PARAMETERS[slot]] += 1

    expected_per_layer = experts * len(ALL_SLOTS)
    expected_total = layers * expected_per_layer
    missing_samples = []
    missing_slot_count = 0
    incomplete_experts = 0
    cross_shard_experts = 0
    cross_shard_samples = []
    for lid in range(layers):
        for expert_id in range(experts):
            owner = (lid, expert_id)
            missing = ALL_SLOTS - seen.get(owner, set())
            if missing:
                incomplete_experts += 1
                missing_slot_count += len(missing)
                if len(missing_samples) < SAMPLE_LIMIT:
                    missing_samples.append({
                        "layer": lid, "expert": expert_id,
                        "missing_slots": [
                            f"{p}.{component}" for p, component in sorted(missing)
                        ],
                    })
            files = files_by_expert.get(owner, set())
            if len(files) > 1:
                cross_shard_experts += 1
                if len(cross_shard_samples) < SAMPLE_LIMIT:
                    cross_shard_samples.append({
                        "layer": lid, "expert": expert_id,
                        "files": sorted(files),
                    })

    status = ("PASS_BASE_KEY_SCHEMA_ONLY"
              if not (unclassified or unsupported or duplicates or missing_slot_count)
              and base_candidate_total == expected_total
              else "FAIL_KEY_SCHEMA")
    return {
        "status": status,
        "classification": "INDEX_NAMES_ONLY_NOT_RUNTIME_OR_CT_8_PARAMETER_COVERAGE",
        "expected_base_routed_keys": expected_total,
        "expected_base_keys_per_layer": expected_per_layer,
        "base_routed_key_candidates": base_candidate_total,
        "base_routed_key_schema": "512_experts_x_gate/up/down_x_weight/group/global",
        "layers_checked": layers, "experts_per_layer_checked": experts,
        "unclassified_base_routed_key_samples": unclassified,
        "out_of_range_base_routed_key_samples": unsupported,
        "duplicate_semantic_slot_samples": duplicates,
        "incomplete_expert_grid_count": incomplete_experts,
        "missing_canonical_slot_count": missing_slot_count,
        "missing_expert_slot_samples": missing_samples,
        "per_CT_parameter_key_counts": dict(sorted(parameter_counter.items())),
        "layer_8_11_shard_key_counts": {
            str(lid): dict(sorted(per_layer_file.get(lid, Counter()).items()))
            for lid in (8, 11) if lid < layers
        },
        "expert_with_keys_in_multiple_shards_count": cross_shard_experts,
        "expert_cross_shard_samples": cross_shard_samples,
        "auxiliary_mtp_namespace_key_count": mtp_key_count,
        "checkpoint_key_names_with_input_scale_substring": extra_input_scale_keys,
        "ct_input_scale_parameters_not_in_nine_slot_schema": list(
            EXPECTED_CT_INPUT_SCALES
        ),
        "ct_input_scale_initialization_or_loading": "UNVERIFIED",
        "unique_destination_element_coverage": "UNVERIFIED",
        "h38_parameter_loader_event_count": "UNVERIFIED",
        "split_layer_8_11_runtime_buffer_lifetime": "UNVERIFIED",
        "checkpoint_tensor_payload_read": "NO",
        "safetensors_headers_reread": "NO",
        "h38_gpu_or_model_runtime": "NOT_EXECUTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        resolve_shards = load_qualified_shards_guard()
        paths, guarded_map = resolve_shards(args.model_dir)
        weight_map, digest = read_index(args.model_dir)
        if weight_map != guarded_map:
            fail("index_changed_during_guarded_read")
        report = analyze(weight_map)
        report["checkpoint_index_sha256"] = digest
        report["index_file_shard_count"] = len(paths)
        report["index_total_tensor_key_count"] = len(weight_map)
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print("H38_CKPT_CT_KEY_MAP=INVALID reason=" + str(exc), file=sys.stderr)
        return 2

    print("H38_CKPT_CT_KEY_MAP=BEGIN")
    print(json.dumps(report, indent=2, sort_keys=True))
    print("H38_CKPT_CT_KEY_MAP=END")
    print("H38_CKPT_CT_KEY_MAP_GATE=" + str(report["status"]))
    return 0 if report["status"] == "PASS_BASE_KEY_SCHEMA_ONLY" else 3


if __name__ == "__main__":
    raise SystemExit(main())
