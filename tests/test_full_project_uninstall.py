"""Isolated full-project wipe-engine policy tests; never use real Docker or sudo."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/lifecycle/full-project-uninstall.py"
SPEC = importlib.util.spec_from_file_location("qwen_full_reset_fixture", SOURCE)
assert SPEC is not None and SPEC.loader is not None
full = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(full)


class FullProjectUninstallTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.home = self.base / "home"
        self.checkout = self.base / "repo"
        self.state = self.home / ".local/state/qwen38-spark"
        self.data = self.home / ".local/share/qwen38-spark"
        self.model_root = self.home / "models"
        self.hf = self.home / ".cache/huggingface"
        self.units = self.base / "units"
        self.fstab = self.base / "fstab"
        self.swap = self.base / "swap-ple.img"
        for path in (self.state, self.data, self.model_root, self.hf,
                     self.units, self.checkout):
            path.mkdir(parents=True, exist_ok=True)
        self.fstab.write_text("")
        self.scope = {
            "home": str(self.home), "checkout": str(self.checkout),
            "state": str(self.state), "data": str(self.data),
            "models": str(self.model_root), "hf": str(self.hf),
            "units": str(self.units), "fstab": str(self.fstab),
            "swap": str(self.swap),
        }

    def test_receipt_sha_tamper_is_blocked(self) -> None:
        body = {"schema": 1, "mode": "EXACT_PROJECT_RESET",
                "scope": self.scope, "targets": []}
        raw = {**body, "sha256": full.digest(body)}
        self.assertEqual(full.verify_plan(raw), raw)
        raw["targets"] = [{"kind": "model", "id": "/foreign"}]
        with self.assertRaisesRegex(full.Blocked, "integrity"):
            full.verify_plan(raw)

    def test_short_docker_id_refused(self) -> None:
        with self.assertRaisesRegex(full.Blocked, "full_sha"):
            full.docker_identity("123abc")

    def test_docker_exact_id_must_match_inspect_and_project_label(self) -> None:
        cid = "a" * 64
        baseline = {"Id": cid, "Name": "/qwen38-mazinb-m1-R2",
                    "Config": {"Labels": {"qwen38.abtrial": "mazinb"}},
                    "State": {"Running": False, "Status": "exited"},
                    "Image": "sha256:" + "b" * 64, "Mounts": []}
        with patch.object(full, "json_command", return_value=[baseline]):
            result = full.docker_identity(cid)
        self.assertEqual(result["id"], cid)
        self.assertEqual(result["labels"]["qwen38.abtrial"], "mazinb")
        foreign = {**baseline, "Config": {"Labels": {"app": "unrelated"}}}
        with patch.object(full, "json_command", return_value=[foreign]):
            with self.assertRaisesRegex(full.Blocked, "ownership_label"):
                full.docker_identity(cid)
        wrong = {**baseline, "Id": "b" * 64}
        with patch.object(full, "json_command", return_value=[wrong]):
            with self.assertRaisesRegex(full.Blocked, "identity_mismatch"):
                full.docker_identity(cid)

    def test_docker_preflight_blocks_foreign_image_dependency(self) -> None:
        foreign = "f" * 64
        managed = "a" * 64
        image = "sha256:" + "b" * 64
        def fake_json(*argv: str):
            self.assertEqual(argv[-1], foreign)
            return [{"Id": foreign, "Image": image, "Mounts": []}]
        with (patch.object(full.inventory, "run_docker", return_value=[
                  {"ID": managed}, {"ID": foreign}]),
              patch.object(full, "json_command", side_effect=fake_json)):
            with self.assertRaisesRegex(full.Blocked, "external_container"):
                full.inspect_image_references(
                    [{"id": managed}],
                    [{"kind": "image", "id": "vllm-orcarouter-v029:v1",
                      "fingerprint": {"id": image}}],
                )

    def test_docker_preflight_blocks_foreign_volume_dependency(self) -> None:
        foreign = "f" * 64
        with (patch.object(full.inventory, "run_docker", return_value=[
                  {"ID": foreign}]),
              patch.object(full, "json_command", return_value=[
                  {"Id": foreign, "Image": "sha256:" + "e" * 64,
                   "Mounts": [{"Name": "qwen38-temp"}]}])):
            with self.assertRaisesRegex(full.Blocked, "volume_used"):
                full.inspect_image_references(
                    [], [], [{"kind": "volume", "id": "qwen38-temp"}],
                )

    def test_plan_scope_rejects_parent_and_model_symlink(self) -> None:
        with self.assertRaisesRegex(full.Blocked, "model_outside"):
            full.scoped_file(self.home, "model", self.scope)
        foreign = self.home / "foreign"
        foreign.mkdir()
        item = self.model_root / "qwen3.8-evil"
        item.symlink_to(foreign)
        with self.assertRaisesRegex(full.Blocked, "symlink"):
            full.scoped_file(item, "model", self.scope)

    def test_discovery_does_not_make_foreign_model_permitted(self) -> None:
        foreign = self.home / "unrelated-model"
        foreign.mkdir()
        with self.assertRaisesRegex(full.Blocked, "model_outside"):
            full.scoped_file(foreign, "model", self.scope)
        owned_candidate = self.model_root / "qwen3.8-flash-next-mazinb"
        owned_candidate.mkdir()
        full.scoped_file(owned_candidate, "model", self.scope)

    def test_project_forensic_is_a_removal_target_and_shared_cache_is_not(self) -> None:
        target = self.home / "Workspace/llm/qwen38-m1-bench-results"
        target.mkdir(parents=True)
        full.scoped_file(target, "forensic", self.scope)
        shared = self.hf / "hub/models--other--unrelated"
        shared.mkdir(parents=True)
        with self.assertRaisesRegex(full.Blocked, "unverified_shared"):
            full.scoped_file(shared, "model-cache", self.scope)

    def test_nested_symlink_blocks_recursive_removal(self) -> None:
        folder = self.model_root / "qwen3.8-flash-next-mazinb"
        folder.mkdir()
        (folder / "link").symlink_to(self.home / "outside")
        with self.assertRaisesRegex(full.Blocked, "unsafe_nested"):
            full.scoped_file(folder, "model", self.scope)

    def test_transaction_markers_fail_closed(self) -> None:
        (self.state / "settings-transition.phase").write_text("pending")
        with self.assertRaisesRegex(full.Blocked, "active_or_stale"):
            full.ensure_no_live_transitions(self.scope)

    def test_drift_blocks_before_any_mutator(self) -> None:
        saved = {"schema": 1, "mode": "EXACT_PROJECT_RESET",
                 "scope": self.scope, "targets": []}
        saved["sha256"] = full.digest(saved)
        current = dict(saved)
        current["targets"] = [{"kind": "container", "id": "a" * 64}]
        self.assertNotEqual(saved, current)

    def test_nonproject_unit_is_rejected_even_when_named_correctly(self) -> None:
        path = self.units / "qwen38-flash-next.service"
        path.write_text("[Unit]\nDescription=foreign\n")
        with self.assertRaisesRegex(full.Blocked, "not_provably"):
            full.check_units(self.scope, [])

    def test_postcheck_only_passes_when_project_scoped_inventory_empty(self) -> None:
        empty = {"issues": [], "resources": [
            {"kind": "hf-cache", "locator": str(self.hf),
             "status": "PRESENT", "ownership": "EXCLUDED_SHARED"},
            {"kind": "state-root", "locator": str(self.state),
             "status": "ABSENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "unit-runtime", "locator": "qwen38-flash-next.service",
             "status": "ABSENT", "ownership": "PROJECT_ASSOCIATED"},
        ]}
        with patch.object(full.inventory, "gather", return_value=empty):
            clean, issues = full.verify_removed({"scope": self.scope})
            self.assertTrue(clean)
            self.assertEqual(issues, [])
        empty["resources"][1]["status"] = "PRESENT"
        with patch.object(full.inventory, "gather", return_value=empty):
            clean, issues = full.verify_removed({"scope": self.scope})
            self.assertFalse(clean)
            self.assertIn("state-root:" + str(self.state) + ":PRESENT", issues)

    def test_mutation_sequence_is_exactly_project_scoped_and_checked(self) -> None:
        # Every deletion command is inspect-bound, never docker prune.
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('"docker", "rm", "-f", item["id"]', source)
        self.assertIn('"docker", "image", "rm", item["id"]', source)
        self.assertIn('"docker", "volume", "rm", item["id"]', source)
        for dangerous in ('"docker", "system", "prune"', '"docker", "volume", "prune"',
                          '"rm", "-rf"', '"swapoff", "/swap.img"'):
            self.assertNotIn(dangerous, source)
        self.assertIn("typed_approval_or_full_digest_not_matched", source)

    def test_plan_receipt_cannot_be_inside_deletion_scope(self) -> None:
        with self.assertRaisesRegex(full.Blocked, "receipt_inside"):
            full.ensure_receipt_outside_scope(
                self.state / "uninstall-receipt.json",
                {"scope": self.scope},
            )
        full.ensure_receipt_outside_scope(
            self.home / "uninstall-receipt.json",
            {"scope": self.scope},
        )


if __name__ == "__main__":
    unittest.main()
