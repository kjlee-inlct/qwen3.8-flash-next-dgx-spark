from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).parents[1]
TOOL = ROOT / "scripts" / "model" / "migrate_orcarouter.py"
SPEC = importlib.util.spec_from_file_location("migrate_orcarouter", TOOL)
assert SPEC is not None and SPEC.loader is not None
migrate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = migrate
SPEC.loader.exec_module(migrate)


def write_checkpoint(root: Path, *, status: str = "complete", revision: str | None = None) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "model-00001.safetensors").write_bytes(b"x")
    (root / "model.safetensors.index.json").write_text(
        json.dumps({"weight_map": {"x": "model-00001.safetensors"}}),
        encoding="utf-8",
    )
    (root / ".qwen38-model-manifest.json").write_text(
        json.dumps(
            {
                "status": status,
                "repository": migrate.ORCA_REPOSITORY,
                "revision": revision or migrate.ORCA_REVISION,
                "files": [],
            }
        ),
        encoding="utf-8",
    )


def write_partial(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / ".qwen38-model-manifest.json").write_text(
        json.dumps(
            {
                "status": "downloading",
                "repository": migrate.ORCA_REPOSITORY,
                "revision": migrate.ORCA_REVISION,
                "files": [],
            }
        ),
        encoding="utf-8",
    )


class OrcaRouterMigrationTests(unittest.TestCase):
    def test_dry_run_preserves_complete_legacy_and_partial_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "repo" / "model"
            canonical = root / "models" / "qwen3.8-flash-next-orcarouter"
            write_checkpoint(legacy)
            write_partial(canonical)

            plan = migrate.prepare_plan(
                legacy,
                canonical,
                mount_checker=lambda _: [],
            )
            self.assertIsNotNone(plan.backup)

            with mock.patch("builtins.print") as printer:
                migrate.apply_plan(plan, dry_run=True)

            self.assertTrue(legacy.is_dir())
            self.assertFalse(legacy.is_symlink())
            self.assertEqual(
                json.loads((canonical / ".qwen38-model-manifest.json").read_text())["status"],
                "downloading",
            )
            self.assertTrue(any("DRY-RUN" in str(call) for call in printer.call_args_list))

    def test_apply_moves_complete_legacy_backs_up_partial_and_links_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "repo" / "model"
            canonical = root / "models" / "qwen3.8-flash-next-orcarouter"
            write_checkpoint(legacy)
            write_partial(canonical)

            plan = migrate.prepare_plan(
                legacy,
                canonical,
                mount_checker=lambda _: [],
            )
            backup = plan.backup
            self.assertIsNotNone(backup)

            migrate.apply_plan(plan, dry_run=False)

            self.assertTrue(canonical.is_dir())
            self.assertTrue(legacy.is_symlink())
            self.assertEqual(legacy.resolve(), canonical.resolve())
            self.assertTrue(backup.is_dir())
            self.assertEqual(
                json.loads((backup / ".qwen38-model-manifest.json").read_text())["status"],
                "downloading",
            )
            migrate.validate_complete_checkpoint(canonical)

    def test_second_run_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "repo" / "model"
            canonical = root / "models" / "qwen3.8-flash-next-orcarouter"
            write_checkpoint(canonical)
            legacy.parent.mkdir(parents=True)
            legacy.symlink_to(canonical, target_is_directory=True)

            plan = migrate.prepare_plan(
                legacy,
                canonical,
                mount_checker=lambda _: [],
            )

            self.assertTrue(plan.already_migrated)
            self.assertIsNone(plan.backup)
            migrate.apply_plan(plan, dry_run=False)
            self.assertTrue(legacy.is_symlink())

    def test_wrong_legacy_revision_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "repo" / "model"
            canonical = root / "models" / "qwen3.8-flash-next-orcarouter"
            write_checkpoint(legacy, revision="0" * 40)

            with self.assertRaisesRegex(migrate.MigrationError, "unexpected revision"):
                migrate.prepare_plan(
                    legacy,
                    canonical,
                    mount_checker=lambda _: [],
                )

    def test_incomplete_legacy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "repo" / "model"
            canonical = root / "models" / "qwen3.8-flash-next-orcarouter"
            write_checkpoint(legacy, status="downloading")

            with self.assertRaisesRegex(migrate.MigrationError, "not complete"):
                migrate.prepare_plan(
                    legacy,
                    canonical,
                    mount_checker=lambda _: [],
                )

    def test_conflicting_complete_canonical_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "repo" / "model"
            canonical = root / "models" / "qwen3.8-flash-next-orcarouter"
            write_checkpoint(legacy)
            write_checkpoint(canonical)

            with self.assertRaisesRegex(migrate.MigrationError, "manual reconciliation"):
                migrate.prepare_plan(
                    legacy,
                    canonical,
                    mount_checker=lambda _: [],
                )

    def test_running_container_mount_rejects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "repo" / "model"
            canonical = root / "models" / "qwen3.8-flash-next-orcarouter"
            write_checkpoint(legacy)

            with self.assertRaisesRegex(migrate.MigrationError, "mounted by running container"):
                migrate.prepare_plan(
                    legacy,
                    canonical,
                    mount_checker=lambda path: ["qwen38-test"] if path == legacy else [],
                )

    def test_different_filesystem_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "repo" / "model"
            canonical = root / "models" / "qwen3.8-flash-next-orcarouter"
            write_checkpoint(legacy)

            with mock.patch.object(migrate, "same_filesystem", return_value=False):
                with self.assertRaisesRegex(migrate.MigrationError, "different filesystems"):
                    migrate.prepare_plan(
                        legacy,
                        canonical,
                        mount_checker=lambda _: [],
                    )


if __name__ == "__main__":
    unittest.main()
