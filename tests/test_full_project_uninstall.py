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

    def test_foreign_docker_bind_mount_blocks_project_file_deletion(self) -> None:
        foreign = "e" * 64
        model = self.model_root / "qwen3.8-flash-next-orcarouter"
        model.mkdir()
        with (patch.object(full.inventory, "run_docker", return_value=[
                  {"ID": foreign}]),
              patch.object(full, "json_command", return_value=[
                  {"Id": foreign, "Image": "sha256:" + "d" * 64,
                   "Mounts": [{"Type": "bind", "Source": str(model),
                               "Destination": "/model"}]}])):
            with self.assertRaisesRegex(full.Blocked, "file_mount_used"):
                full.inspect_image_references(
                    [], [], [], [{"kind": "model", "id": str(model)}],
                )

    def test_prefix_only_foreign_assets_fail_closed_before_identity_lookup(self) -> None:
        # A recognizable name is an inventory hint, not ownership evidence.
        # Even an unused foreign image is not safe to delete.
        foreign_model = self.model_root / "qwen3.8-foreign-model"
        foreign_model.mkdir()
        (foreign_model / "KEEP").write_text("external")
        foreign_cache = self.hf / "hub/models--mazinb--Qwen3.8-Flash-Next"
        foreign_cache.mkdir(parents=True)
        candidates = [
            {"kind": "image", "locator": "vllm-foreign-runtime:v1",
             "status": "PRESENT", "ownership": "UNVERIFIED"},
            {"kind": "model", "locator": str(foreign_model),
             "status": "PRESENT", "ownership": "UNVERIFIED"},
            {"kind": "model-cache", "locator": str(foreign_cache),
             "status": "PRESENT", "ownership": "UNVERIFIED"},
        ]
        base = [
            {"kind": "state-root", "locator": str(self.state),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "data-root", "locator": str(self.data),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
        ]
        for candidate in candidates:
            with self.subTest(kind=candidate["kind"]):
                with (patch.object(full.inventory, "gather",
                                   return_value={"issues": [], "resources": base + [candidate]}),
                      patch.object(full, "image_identity",
                                   side_effect=AssertionError("no image inspection for foreign asset")),
                      patch.object(full, "inspect_swap", return_value=None),
                      patch.object(full, "inspect_image_references", return_value=None)):
                    with self.assertRaisesRegex(
                            full.Blocked,
                            "candidate_ownership_not_proven:" + candidate["kind"]):
                        full.scan(self.scope)
        self.assertEqual((foreign_model / "KEEP").read_text(), "external")
        self.assertTrue(foreign_cache.exists())

    def test_positive_owned_image_can_enter_exact_identity_bound_plan(self) -> None:
        tag = "vllm-skinny-tp1:v1"
        rows = [
            {"kind": "state-root", "locator": str(self.state),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "data-root", "locator": str(self.data),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "image", "locator": tag,
             "status": "PRESENT", "ownership": "INSTALLER_OWNED"},
        ]
        identity = {"tag": tag, "id": "sha256:" + "b" * 64}
        with (patch.object(full.inventory, "gather",
                           return_value={"issues": [], "resources": rows}),
              patch.object(full, "image_identity", return_value=identity),
              patch.object(full, "inspect_swap", return_value=None),
              patch.object(full, "inspect_image_references", return_value=None)):
            plan = full.scan(self.scope)
        self.assertIn({"kind": "image", "id": tag, "fingerprint": identity},
                      plan["targets"])

    def test_plan_scope_rejects_parent_and_model_symlink(self) -> None:
        with self.assertRaisesRegex(full.Blocked, "model_outside"):
            full.scoped_file(self.home, "model", self.scope)
        foreign = self.home / "foreign"
        foreign.mkdir()
        item = self.model_root / "qwen3.8-evil"
        item.symlink_to(foreign)
        with self.assertRaisesRegex(full.Blocked, "symlink"):
            full.scoped_file(item, "model", self.scope)

    def test_legacy_checkout_model_link_is_planned_and_unlinked_only(self) -> None:
        target = self.model_root / "qwen3.8-flash-next-orcarouter"
        target.mkdir()
        (target / "config.json").write_text("MODEL_DATA")
        link = self.checkout / "model"
        link.symlink_to(target)
        self.assertTrue(link.is_symlink())
        self.assertEqual(full.inventory.path_status(link), "UNSAFE_SYMLINK")
        fingerprint = full.legacy_model_link_identity(link, self.scope)
        self.assertEqual(fingerprint["resolved_target"], str(target))
        rows = [
            {"kind": "model", "locator": str(link),
             "status": "UNSAFE_SYMLINK", "ownership": "UNVERIFIED"},
            {"kind": "model", "locator": str(target),
             "status": "PRESENT", "ownership": "INSTALLER_OWNED"},
            {"kind": "state-root", "locator": str(self.state),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "data-root", "locator": str(self.data),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
        ]
        with (patch.object(full.inventory, "gather",
                           return_value={"issues": [], "resources": rows}),
              patch.object(full, "inspect_swap", return_value=None),
              patch.object(full, "inspect_image_references", return_value=None)):
            plan = full.scan(self.scope)
        link_entry = next(item for item in plan["targets"]
                          if item["kind"] == "legacy-model-link")
        self.assertEqual(link_entry["fingerprint"], fingerprint)
        self.assertIn({"kind": "model", "id": str(target),
                       "fingerprint": next(x["fingerprint"] for x in plan["targets"]
                                           if x["kind"] == "model")},
                      plan["targets"])
        with patch.object(full, "inspect_image_references", return_value=None):
            full.execute(plan)
        self.assertFalse(link.exists())
        self.assertFalse(link.is_symlink())
        self.assertFalse(target.exists())
        self.assertTrue(self.checkout.is_dir())
        self.assertTrue(self.model_root.is_dir())

    def test_legacy_model_link_to_foreign_live_target_stays_blocked(self) -> None:
        foreign = self.home / "unrelated-data"
        foreign.mkdir()
        (foreign / "important.txt").write_text("KEEP")
        link = self.checkout / "model"
        link.symlink_to(foreign)
        with self.assertRaisesRegex(full.Blocked,
                                     "legacy_model_link_target_outside"):
            full.legacy_model_link_identity(link, self.scope)
        self.assertTrue(link.is_symlink())
        self.assertEqual((foreign / "important.txt").read_text(), "KEEP")

    def test_legacy_model_link_to_untracked_project_directory_stays_blocked(self) -> None:
        target = self.model_root / "qwen3.8-flash-next-mazinb"
        target.mkdir()
        link = self.checkout / "model"
        link.symlink_to(target)
        rows = [
            {"kind": "model", "locator": str(link),
             "status": "UNSAFE_SYMLINK", "ownership": "UNVERIFIED"},
            {"kind": "state-root", "locator": str(self.state),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "data-root", "locator": str(self.data),
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
        ]
        with (patch.object(full.inventory, "gather",
                           return_value={"issues": [], "resources": rows}),
              patch.object(full, "inspect_swap", return_value=None),
              patch.object(full, "inspect_image_references", return_value=None)):
            with self.assertRaisesRegex(full.Blocked,
                                         "legacy_model_link_target_not_selected"):
                full.scan(self.scope)

    def test_legacy_link_drift_refuses_unlink_and_preserves_targets(self) -> None:
        model = self.model_root / "qwen3.8-flash-next-orcarouter"
        model.mkdir()
        other = self.model_root / "qwen3.8-flash-next-mazinb"
        other.mkdir()
        link = self.checkout / "model"
        link.symlink_to(model)
        recorded = full.legacy_model_link_identity(link, self.scope)
        link.unlink()
        link.symlink_to(other)
        with patch.object(full, "inspect_image_references", return_value=None):
            with self.assertRaisesRegex(full.Blocked, "legacy_model_link_drift"):
                full.execute({"scope": self.scope, "targets": [
                    {"kind": "legacy-model-link", "id": str(link),
                     "fingerprint": recorded},
                ]})
        self.assertTrue(link.is_symlink())
        self.assertTrue(model.exists())
        self.assertTrue(other.exists())

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

    def test_nested_symlink_is_unlinked_without_following_foreign_target(self) -> None:
        folder = self.model_root / "qwen3.8-flash-next-mazinb"
        folder.mkdir()
        external = self.home / "unrelated"
        external.mkdir()
        (external / "keep.txt").write_text("KEEP")
        (folder / "link").symlink_to(external)
        full.scoped_file(folder, "model", self.scope)
        full.remove_tree(folder, "model", self.scope)
        self.assertFalse(folder.exists())
        self.assertEqual((external / "keep.txt").read_text(), "KEEP")

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

    def test_service_remove_inherits_shared_lifecycle_lock(self) -> None:
        unit = {"kind": "systemd", "id": "qwen38-flash-next.service"}
        commands = []
        def command(*argv: str) -> str:
            commands.append(argv)
            return ""
        with (patch.object(full, "run", side_effect=command),
              patch.object(full, "inspect_image_references", return_value=None)):
            full.execute({"scope": self.scope, "targets": [unit]})
        self.assertEqual(len(commands), 1)
        call = commands[0]
        self.assertEqual(call[:2], ("sudo", "env"))
        self.assertIn("QWEN38_OPERATION_LOCK_HELD=1", call)
        self.assertIn("QWEN38_OPERATION_LOCK_FILE=" +
                      str(self.state / "operation.lock"), call)
        self.assertEqual(call[-2:], ("remove", "--yes"))

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

    def test_project_only_runtime_caches_are_removable_but_shared_flashinfer_not(self) -> None:
        dedicated = self.home / ".cache/vllm-qwen38-v029"
        dedicated.mkdir(parents=True)
        (dedicated / "token").write_text("safe fixture")
        full.scoped_file(dedicated, "project-cache", self.scope)
        full.remove_tree(dedicated, "project-cache", self.scope)
        self.assertFalse(dedicated.exists())
        shared = self.home / ".cache/flashinfer"
        shared.mkdir(parents=True)
        with self.assertRaisesRegex(full.Blocked, "unverified_runtime_cache"):
            full.scoped_file(shared, "project-cache", self.scope)
        self.assertTrue(shared.exists())

    def test_disposable_full_file_teardown_removes_models_evidence_state_data(self) -> None:
        model = self.model_root / "qwen3.8-flash-next-orcarouter"
        model.mkdir()
        (model / "config.json").write_text("{}")
        forensic = self.home / "Workspace/llm/qwen38-m1-bench-results"
        forensic.mkdir(parents=True)
        (forensic / "monitor.log").write_text("fake")
        (self.state / "install.env").write_text("FAKE")
        (self.data / "current").mkdir()
        targets = []
        for kind, path in (
            ("model", model), ("forensic", forensic),
            ("data-root", self.data), ("state-root", self.state),
        ):
            st = path.lstat()
            targets.append({"kind": kind, "id": str(path),
                            "fingerprint": {"dev": st.st_dev, "ino": st.st_ino,
                                            "mode": st.st_mode}})
        with patch.object(full, "inspect_image_references", return_value=None):
            full.execute({"scope": self.scope, "targets": targets})
        for path in (model, forensic, self.data, self.state):
            self.assertFalse(path.exists(), str(path))
        self.assertTrue(self.home.exists())
        self.assertTrue(self.checkout.exists())
        self.assertTrue(self.hf.exists())

    def test_unsafe_foreign_mount_boundary_is_fail_closed(self) -> None:
        foreign = self.home / "unrelated"
        foreign.mkdir()
        with self.assertRaisesRegex(full.Blocked, "forensic_outside"):
            full.scoped_file(foreign, "forensic", self.scope)

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
