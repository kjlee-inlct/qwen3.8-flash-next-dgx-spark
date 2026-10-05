#!/usr/bin/env python3
"""Read-only H6 ModelOpt routing inspection after R27.

This does not instantiate the model or modify checkpoint files. It records the
H6 quantization config, inherited ignore/exclude patterns, manifest identity,
and a diagnostic approximation of checkpoint module names matched by those
patterns.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path
from typing import Any


PARAM_SUFFIXES = (
    ".weight_scale_2",
    ".weight_global_scale",
    ".weight_scale",
    ".input_scale",
    ".output_scale",
    ".k_scale",
    ".v_scale",
    ".weight",
    ".bias",
)


def load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"JSON root is not an object: {path}")
    return data


def module_prefix(name: str) -> str:
    for suffix in PARAM_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name.rsplit(".", 1)[0] if "." in name else name


def approx_pattern_match(prefix: str, pattern: str) -> bool:
    """Approximate ModelOpt exclusion routing for checkpoint-name diagnostics.

    vLLM also applies packed-module mapping in is_layer_skipped(); this helper is
    deliberately labelled approximate and must not be treated as an exact
    runtime routing decision.
    """

    if prefix == pattern:
        return True
    if pattern in prefix:
        return True
    if prefix.startswith("language_model.") and pattern in prefix.removeprefix(
        "language_model."
    ):
        return True
    return fnmatch.fnmatch(prefix, pattern)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "checkpoint",
        type=Path,
        nargs="?",
        default=Path("models/qwen3.8-h6-modelopt-w4a16"),
    )
    parser.add_argument("--sample-limit", type=int, default=12)
    args = parser.parse_args()

    root = args.checkpoint.resolve()
    config_path = root / "config.json"
    index_path = root / "model.safetensors.index.json"
    manifest_path = root / ".qwen38-hybrid-manifest.json"

    for path in (config_path, index_path, manifest_path):
        if not path.is_file():
            raise SystemExit(f"required file missing: {path}")

    config = load_object(config_path)
    index = load_object(index_path)
    manifest = load_object(manifest_path)

    quant = config.get("quantization_config")
    if not isinstance(quant, dict):
        raise SystemExit("config.json has no object quantization_config")

    raw_patterns = quant.get("ignore")
    pattern_key = "ignore"
    if raw_patterns is None:
        raw_patterns = quant.get("exclude_modules", [])
        pattern_key = "exclude_modules"
    if not isinstance(raw_patterns, list) or not all(
        isinstance(item, str) for item in raw_patterns
    ):
        raise SystemExit(f"quantization_config.{pattern_key} is not a string list")
    patterns = list(raw_patterns)

    weight_map = index.get("weight_map")
    if not isinstance(weight_map, dict):
        raise SystemExit("checkpoint index has no object weight_map")
    tensor_names = sorted(str(name) for name in weight_map)
    prefixes = sorted({module_prefix(name) for name in tensor_names})

    matched_by_pattern: dict[str, list[str]] = {
        pattern: [p for p in prefixes if approx_pattern_match(p, pattern)]
        for pattern in patterns
    }
    matched_union = sorted(
        {prefix for values in matched_by_pattern.values() for prefix in values}
    )

    print("R27_H6_QUANT_ROUTING_INSPECTION=BEGIN")
    print("inspection_semantics=read_only_config_and_checkpoint_name_diagnostic")
    print("runtime_routing_semantics=approximate_until_linearbase_dispatch_is_observed")
    print(f"checkpoint={root}")
    print(f"manifest.status={manifest.get('status')}")
    print(f"manifest.variant={manifest.get('variant')}")
    print(f"manifest.parent_variant={manifest.get('parent_variant')}")
    print(f"manifest.quant_algo_before={manifest.get('quant_algo_before')}")
    print(f"manifest.quant_algo_after={manifest.get('quant_algo_after')}")
    print(f"manifest.safetensor_bytes_changed={manifest.get('safetensor_bytes_changed')}")
    print(f"quant.quant_method={quant.get('quant_method')}")
    print(f"quant.quant_algo={quant.get('quant_algo')}")
    print(f"quant.pattern_key={pattern_key}")
    print(f"quant.pattern_count={len(patterns)}")
    print(f"quant.config_group_count={len(quant.get('config_groups', {})) if isinstance(quant.get('config_groups'), dict) else 0}")
    print(f"checkpoint.tensor_count={len(tensor_names)}")
    print(f"checkpoint.derived_module_prefix_count={len(prefixes)}")
    print(f"checkpoint.approx_excluded_prefix_count={len(matched_union)}")

    for idx, pattern in enumerate(patterns, start=1):
        values = matched_by_pattern[pattern]
        print(f"pattern.{idx}.value={pattern}")
        print(f"pattern.{idx}.approx_prefix_count={len(values)}")
        for sample_idx, value in enumerate(values[: args.sample_limit], start=1):
            print(f"pattern.{idx}.sample.{sample_idx}={value}")

    config_groups = quant.get("config_groups")
    if isinstance(config_groups, dict):
        for name in sorted(config_groups):
            group = config_groups[name]
            if not isinstance(group, dict):
                continue
            print(f"config_group.{name}.targets={group.get('targets')}")
            print(f"config_group.{name}.weights={group.get('weights')}")
            print(f"config_group.{name}.input_activations={group.get('input_activations')}")

    print("R27_H6_QUANT_ROUTING_INSPECTION=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
