from __future__ import annotations

import importlib.util
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "scripts" / "model" / "relocate_model_root.py"
sys.path.insert(0, str(MODULE_PATH.parent))

spec = importlib.util.spec_from_file_location("relocate_model_root", MODULE_PATH)
assert spec is not None and spec.loader is not None
relocate_model_root = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = relocate_model_root
spec.loader.exec_module(relocate_model_root)


class ModelRootRelocationTests(unittest.TestCase):
    def make_managed_root(self, base: Path) -> tuple[Path, Path]:
        source = base / "home" / "models"
        model = source / "qwen3.8-flash-next-orcarouter"
        model.mkdir(parents=True)
        (model / ".qwen38-model-manifest.json").write_text(
            json.dumps(
                {
                    "status": "complete",
                    "repository": "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
                    "revision": "c1209bda15a6bbc4c68b585e93d40c0d85f50306",
                }
            ),
            encoding="utf-8",
        )
        return source, model

    def test_atomic_relocation_leaves_compatibility_symlinks_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, model = self.make_managed_root(base)
            repo = base / "repo"
            repo.mkdir()
            destination = repo / "models"
            legacy = repo / "model"
            legacy.symlink_to(model, target_is_directory=True)

            with (
                mock.patch.object(relocate_model_root, "running_container_mounts", return_value=[]),
                mock.patch.object(relocate_model_root, "managed_service_active", return_value=False),
            ):
                plan = relocate_model_root.plan_relocation(source, destination, repo)
                self.assertFalse(plan.already_relocated)
                relocate_model_root.apply_relocation(plan)

                self.assertTrue(source.is_symlink())
                self.assertEqual(source.resolve(), destination.resolve())
                self.assertTrue(legacy.is_symlink())
                self.assertEqual(
                    legacy.resolve(),
                    (destination / "qwen3.8-flash-next-orcarouter").resolve(),
                )
                self.assertTrue(
                    (
                        destination
                        / "qwen3.8-flash-next-orcarouter"
                        / ".qwen38-model-manifest.json"
                    ).is_file()
                )

                again = relocate_model_root.plan_relocation(source, destination, repo)
                self.assertTrue(again.already_relocated)

    def test_linked_hybrid_uses_chain_validator_instead_of_raw_shard_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, _ = self.make_managed_root(base)
            h4 = source / "qwen3.8-h4-orca-all"
            h4.mkdir()
            (h4 / ".qwen38-hybrid-manifest.json").write_text(
                json.dumps(
                    {
                        "status": "complete",
                        "variant": "h4-orca-all",
                    }
                ),
                encoding="utf-8",
            )
            (h4 / "model.safetensors.index.json").write_text(
                json.dumps(
                    {
                        "weight_map": {
                            "x": "/base-model/model-00001-of-00017.safetensors"
                        }
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.object(
                    relocate_model_root,
                    "validate_checkpoint_index",
                    wraps=relocate_model_root.validate_checkpoint_index,
                ) as checkpoint_validator,
                mock.patch.object(
                    relocate_model_root,
                    "validate_hybrid_chain",
                    return_value=None,
                ) as hybrid_validator,
            ):
                entries = relocate_model_root.inspect_root(source)

            self.assertEqual(len(entries), 2)
            checkpoint_validator.assert_called_once()
            self.assertEqual(
                checkpoint_validator.call_args.args[0].name,
                "qwen3.8-flash-next-orcarouter",
            )
            hybrid_validator.assert_called_once()

    def test_hybrid_chain_validator_selects_highest_present_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = []
            for dirname, variant in (
                ("qwen3.8-hybrid-quant-layout", "quant-layout-mazinb-experts"),
                ("qwen3.8-h4-orca-all", "h4-orca-all"),
                ("qwen3.8-h5-neutral-input-scale", "h5-neutral-input-scale"),
            ):
                path = root / dirname
                path.mkdir()
                manifest = path / ".qwen38-hybrid-manifest.json"
                manifest.write_text(
                    json.dumps({"status": "complete", "variant": variant}),
                    encoding="utf-8",
                )
                entries.append(
                    relocate_model_root.ManagedEntry(path, manifest, "hybrid")
                )

            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="OrcaRouter hybrid chain is valid through H5\n",
                stderr="",
            )
            with mock.patch.object(
                relocate_model_root.subprocess,
                "run",
                return_value=completed,
            ) as runner:
                relocate_model_root.validate_hybrid_chain(root, tuple(entries))

            command = runner.call_args.args[0]
            self.assertIn("--runtime-only", command)
            self.assertEqual(command[command.index("--through") + 1], "h5")
            self.assertEqual(
                command[command.index("--base-dir") + 1],
                str(root / "qwen3.8-flash-next-orcarouter"),
            )

    def test_unknown_hybrid_variant_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "unknown-hybrid"
            path.mkdir()
            manifest = path / ".qwen38-hybrid-manifest.json"
            manifest.write_text(
                json.dumps({"status": "complete", "variant": "future-hybrid"}),
                encoding="utf-8",
            )
            entry = relocate_model_root.ManagedEntry(path, manifest, "hybrid")

            with self.assertRaisesRegex(
                relocate_model_root.RelocationError,
                "unsupported hybrid variant",
            ):
                relocate_model_root.validate_hybrid_chain(root, (entry,))

    def test_unmanaged_top_level_entry_refuses_whole_root_move(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, _ = self.make_managed_root(base)
            (source / "other-model").mkdir()
            repo = base / "repo"
            repo.mkdir()

            with self.assertRaisesRegex(
                relocate_model_root.RelocationError,
                "unmanaged top-level entries",
            ):
                relocate_model_root.plan_relocation(source, repo / "models", repo)

    def test_conflicting_destination_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, _ = self.make_managed_root(base)
            repo = base / "repo"
            destination = repo / "models"
            destination.mkdir(parents=True)

            with self.assertRaisesRegex(
                relocate_model_root.RelocationError,
                "destination already exists",
            ):
                relocate_model_root.plan_relocation(source, destination, repo)

    def test_running_container_mount_refuses_relocation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, _ = self.make_managed_root(base)
            repo = base / "repo"
            repo.mkdir()

            with (
                mock.patch.object(
                    relocate_model_root,
                    "running_container_mounts",
                    return_value=["qwen38:/tmp/model"],
                ),
                mock.patch.object(relocate_model_root, "managed_service_active", return_value=False),
                self.assertRaisesRegex(
                    relocate_model_root.RelocationError,
                    "running container",
                ),
            ):
                relocate_model_root.plan_relocation(source, repo / "models", repo)

    def test_active_managed_service_refuses_relocation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, _ = self.make_managed_root(base)
            repo = base / "repo"
            repo.mkdir()

            with (
                mock.patch.object(relocate_model_root, "running_container_mounts", return_value=[]),
                mock.patch.object(relocate_model_root, "managed_service_active", return_value=True),
                self.assertRaisesRegex(
                    relocate_model_root.RelocationError,
                    "service first",
                ),
            ):
                relocate_model_root.plan_relocation(source, repo / "models", repo)

    def test_cross_filesystem_move_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, _ = self.make_managed_root(base)
            repo = base / "repo"
            repo.mkdir()

            with (
                mock.patch.object(relocate_model_root, "same_filesystem", return_value=False),
                self.assertRaisesRegex(
                    relocate_model_root.RelocationError,
                    "different filesystems",
                ),
            ):
                relocate_model_root.plan_relocation(source, repo / "models", repo)

    def test_operator_command_exposes_root_relocation(self) -> None:
        manager = (ROOT / "scripts" / "manage-models.sh").read_text(encoding="utf-8")
        self.assertIn("relocate-root", manager)
        self.assertIn("relocate_model_root.py", manager)
        self.assertIn("--source", manager)
        self.assertIn("--destination", manager)


if __name__ == "__main__":
    unittest.main()
