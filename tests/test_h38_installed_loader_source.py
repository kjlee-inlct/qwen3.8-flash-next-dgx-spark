"""Guarded synthetic tests for installed H38 loader source-contract inspector."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/benchmark/inspect-h38-installed-loader-source.py"
RUNNER = ROOT / "scripts/benchmark/check-h38-installed-loader-source.sh"
spec = importlib.util.spec_from_file_location("h38_installed_loader_source", SCRIPT)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

MOCK = {
    "default_loader": """
class DefaultModelLoader:
    def _prepare_weights(self, model):
        hf_weights_files = filter_duplicate_safetensors_files(hf_weights_files, root, idx)
    def _get_weights_iterator(self, source):
        if extra_config.get("enable_multithread_load"):
            weights = multi_thread_safetensors_weights_iterator(files)
        elif self.load_config.load_format == "fastsafetensors":
            weights = fastsafetensors_weights_iterator(files)
        else:
            weights = safetensors_weights_iterator(files, self.load_config.safetensors_load_strategy)
    def get_all_weights(self, model_config, model):
        yield from self._get_weights_iterator(primary_weights)
        secondary_weights = model.secondary_weights
        for source in secondary_weights:
            yield from self._get_weights_iterator(source)
    def load_weights(self, model, model_config):
        return model.load_weights(self.get_all_weights(model_config, model))
""",
    "weight_utils": """
def filter_duplicate_safetensors_files(files, folder, index_file):
    weight_map = json.load(f)["weight_map"]
    weight_files_in_index = set()
    return hf_weights_files
def safetensors_weights_iterator(hf_weights_files, *args):
    sorted_files = sorted(hf_weights_files, key=_natural_sort_key)
    if safetensors_load_strategy == "eager":
        pass
    if safetensors_load_strategy == "torchao":
        pass
    if should_prefetch:
        pass
    for st_file in sorted_files:
        with safe_open(st_file, framework="pt") as f:
            for name in f.keys():
                yield name, f.get_tensor(name)
""",
    "model_utils": """
class WeightsMapper:
    def _map_name_with_shard(self, key):
        for substr, new_key in self.orig_to_new_substr.items():
            if substr in key:
                if new_key is None:
                    return None
        return key
    def apply(self, weights):
        for name, data in weights:
            result = self._map_name_with_shard(name)
            if result is None:
                continue
            yield name, data
class AutoWeightsLoader:
    def load_weights(self, weights, mapper):
        weights = mapper.apply(weights)
        return weights
""",
    "qwen4_exp": """
class Qwen4ExpForCausalLM:
    def load_weights(self, weights):
        mapper = WeightsMapper(orig_to_new_substr={"mtp.": None})
        loader = AutoWeightsLoader(self)
        return loader.load_weights(weights, mapper=mapper)
class Qwen4ExpForConditionalGeneration:
    def load_weights(self, weights):
        mapper = WeightsMapper(orig_to_new_substr={"mtp.": None})
        loader = AutoWeightsLoader(self)
        return loader.load_weights(weights, mapper=mapper)
""",
    "layerwise": """
def initialize_online_processing(layer):
    info.load_numel_total = get_layer_size(layer)
    _wrap_parameters_weight_loader(layer)
def make_online_process_loader(layer, param_name):
    def closure():
        info.loaded_weights.append((param_name, args))
        n = get_numel_loaded(original_loader, bound_args)
        if info.load_numel >= info.load_numel_total:
            _layerwise_process(layer, info)
    return closure
def finalize_layerwise_processing(model, model_config):
    _layerwise_process(layer, info)
def _layerwise_process(layer, info):
    materialize_layer(layer, info)
    for name, args in info.loaded_weights:
        param.weight_loader(*args.args, **args.kwargs)
    quant_method.process_weights_after_loading(layer)
""",
    "meta": """
def materialize_layer(layer, info):
    if tensor.is_meta:
        materialize_meta_tensor(tensor)
""",
    "base_loader": """
def _has_online_quant(model):
    if getattr(quant_method, "uses_meta_device", False):
        return True
""",
    "ct": """
class CompressedTensorsW4A4Nvfp4MoEMethod:
    def create_weights(self, layer):
        w13_weight = ModelWeightParameter(data=torch.empty(4))
        layer.register_parameter("w13_weight_packed", w13_weight)
        w2_weight = ModelWeightParameter(data=torch.empty(2))
        layer.register_parameter("w2_weight_packed", w2_weight)
    def process_weights_after_loading(self, layer):
        layer.register_parameter("w13_weight", layer.w13_weight_packed)
        layer.register_parameter("w2_weight", layer.w2_weight_packed)
""",
}


class H38InstalledLoaderSourceTests(unittest.TestCase):
    def test_mock_exact_source_contract_paths(self) -> None:
        result = audit.inspect_sources(MOCK)
        self.assertEqual(result["safetensors_natural_file_sort_and_key_iteration"],
                         "SOURCE_PRESENT")
        self.assertEqual(result["weights_mapper_none_skips_name"],
                         "SOURCE_PRESENT")
        self.assertEqual(result["layerwise_numel_completion_and_buffer_replay"],
                         "SOURCE_PRESENT")

    def test_missing_exact_mtp_mapper_fails_closed(self) -> None:
        invalid = dict(MOCK)
        invalid["qwen4_exp"] = invalid["qwen4_exp"].replace(
            '{"mtp.": None}', '{"mtp.": "mtp."}')
        with self.assertRaisesRegex(ValueError, "Qwen4ExpForCausalLM"):
            audit.inspect_sources(invalid)

    def test_missing_natural_sort_fails_closed(self) -> None:
        invalid = dict(MOCK)
        invalid["weight_utils"] = invalid["weight_utils"].replace(
            "sorted(hf_weights_files, key=_natural_sort_key)",
            "sorted(hf_weights_files)")
        with self.assertRaisesRegex(ValueError, "default_safetensors_stream"):
            audit.inspect_sources(invalid)

    def test_missing_materialize_replay_fails_closed(self) -> None:
        invalid = dict(MOCK)
        invalid["layerwise"] = invalid["layerwise"].replace(
            "materialize_layer(layer, info)", "skip_meta(layer, info)")
        with self.assertRaisesRegex(ValueError, "layerwise_replay_and_postload"):
            audit.inspect_sources(invalid)

    def test_missing_index_filter_fails_closed(self) -> None:
        invalid = dict(MOCK)
        invalid["default_loader"] = invalid["default_loader"].replace(
            "filter_duplicate_safetensors_files(", "do_not_check_index(")
        with self.assertRaisesRegex(ValueError, "indexed_shard_filter"):
            audit.inspect_sources(invalid)

    def test_reads_only_installed_source_under_explicit_root(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name, relative in audit.FILES.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(MOCK[name], encoding="utf-8")
            result = audit.inspect(root)
            self.assertEqual(sum(k.startswith("installed_source_sha256_")
                                 for k in result), len(MOCK))
            self.assertEqual(len(result["installed_source_sha256_layerwise"]), 64)
            # Missing installed file must fail rather than falling back to
            # upstream/main or a non-exact image.
            (root / audit.FILES["default_loader"]).unlink()
            with self.assertRaisesRegex(ValueError, "missing:"):
                audit.inspect(root)

    def test_guarded_read_only_cpu_source_runner(self) -> None:
        script = RUNNER.read_text(encoding="utf-8")
        for flag in (
            "--runtime runc --network none --read-only", "--pull never",
            "--cap-drop ALL --security-opt no-new-privileges",
            "--user 65534:65534", "dirty_checkout",
            "installed_image_id_mismatch", "H38_lineage_mismatch",
            "--tmpfs /tmp:rw,noexec,nosuid,nodev,size=32m,mode=1777",
            "model_checkpoint_payload_read=NO",
            "host_protection_changed=NO",
        ):
            self.assertIn(flag, script)
        self.assertEqual(script.count("--mount "), 1)
        for forbidden in (
            "--gpus all", "docker build", "docker pull ",
            "systemctl", "sysctl -w", "drop_caches", "compact_memory",
            "--privileged", "--user 0:0", "chmod -R",
            "dst=/opt/checkpoint", "dst=/mnt/models",
        ):
            self.assertNotIn(forbidden, script)
        result = subprocess.run(["bash", "-n", str(RUNNER)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_runner_rejects_unspecified_checkout(self) -> None:
        env = dict(os.environ)
        env.pop("H38_LOADER_SOURCE_TARGET_SHA", None)
        result = subprocess.run(["bash", str(RUNNER)], env=env,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("exact_checkout_sha_required", result.stderr)

    def test_source_reader_does_not_import_vllm_or_torch(self) -> None:
        import ast

        parsed = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        imports = [
            alias.name
            for node in ast.walk(parsed)
            if isinstance(node, ast.Import)
            for alias in node.names
        ]
        imports.extend(
            node.module or ""
            for node in ast.walk(parsed)
            if isinstance(node, ast.ImportFrom)
        )
        self.assertFalse(any(name.startswith(("torch", "vllm", "safetensors"))
                             for name in imports), imports)


if __name__ == "__main__":
    unittest.main()
