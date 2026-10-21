"""Offline read-only uninstall scope tests; never talk to real Docker/systemd."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/lifecycle/uninstall-inventory.py"
SPEC = importlib.util.spec_from_file_location("uninstall_inventory", SOURCE)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class UninstallInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.state = self.root / "state/qwen38-spark"
        self.data = self.root / "data/qwen38-spark"
        self.models = self.root / "models"
        self.units = self.root / "units"
        self.swap = self.root / "swap-ple.img"
        self.hf = self.root / "hf"
        self.checkout = self.root / "checkout"
        for path in (self.state, self.data, self.models, self.units,
                     self.hf, self.checkout):
            path.mkdir(parents=True)
        self.containers = []
        self.images = []
        self.volumes = []
        self.fstab = self.root / "fstab"
        self.fstab.write_text("", encoding="utf-8")

    def gather(self, *, error: bool = False) -> dict:
        if error:
            fn = lambda *args: (_ for _ in ()).throw(RuntimeError("daemon_offline"))
        else:
            fn = lambda *args: (self.containers if args[0] == "ps" else
                                self.images if args[0] == "image" else self.volumes)
        with (patch.object(audit, "run_docker", side_effect=fn),
              patch.object(audit, "run_unit_status", return_value={
                  "LoadState": "not-found", "ActiveState": "inactive",
                  "UnitFileState": "",
              })):
            return audit.gather(
                state=self.state, data=self.data, models=self.models,
                units=self.units, swap=self.swap, hf=self.hf, fstab=self.fstab,
                home=self.root, checkout=self.checkout,
            )

    @staticmethod
    def lookup(data: dict, kind: str, locator: str) -> dict:
        return next(x for x in data["resources"]
                    if x["kind"] == kind and x["locator"] == locator)

    def test_absent_resources_are_not_misreported_as_present(self) -> None:
        data = self.gather()
        self.assertEqual(data["issues"], [])
        self.assertEqual(self.lookup(data, "swap", str(self.swap))["status"], "ABSENT")
        self.assertEqual(self.lookup(
            data, "systemd", str(self.units / "qwen38-flash-next.service"))["status"], "ABSENT")
        self.assertIn("unrelated_system_swap", data["exclusions"])

    def test_mazinb_r2_named_journals_are_reported_without_opening_contents(self) -> None:
        item = self.state / "mazinb-m1-reinstall"
        item.mkdir()
        (item / "active.json").write_text("NOT_VALID_JSON")
        data = self.gather()
        self.assertEqual(self.lookup(data, "state", str(item))["status"], "PRESENT")
        self.assertFalse(data["issues"])

    def test_docker_exact_id_is_kept_and_other_app_ignored(self) -> None:
        cid = "a" * 64
        self.containers = [
            {"ID": cid, "Names": "qwen38-mazinb-m1-20261019065452-abcd1234",
             "Labels": "qwen38.abtrial=mazinb,qwen38.variant=m1"},
            {"ID": "b" * 64, "Names": "postgres", "Labels": "project=unrelated"},
        ]
        data = self.gather()
        self.assertEqual(self.lookup(data, "container", cid)["status"], "PRESENT")
        self.assertFalse(any(x["locator"] == "b" * 64 for x in data["resources"]))

    def test_reject_truncated_docker_ids_even_when_project_named(self) -> None:
        self.containers = [{"ID": "abc", "Names": "qwen38-x", "Labels": ""}]
        data = self.gather()
        self.assertTrue(any("docker_inventory_incomplete" in x for x in data["issues"]))

    def test_registry_owned_and_discovered_unowned_are_distinct(self) -> None:
        good = self.models / "qwen3.8-flash-next-mazinb"
        other = self.models / "qwen3.8-h6-modelopt-w4a16"
        good.mkdir()
        other.mkdir()
        (self.state / "asset-ownership.json").write_text(json.dumps({
            "schema_version": 1,
            "assets": [{
                "kind": "model", "locator": str(good), "root": str(self.models),
                "owned": True, "state": "ready", "fingerprint": "",
                "depends_on": [],
            }],
        }))
        data = self.gather()
        self.assertEqual(self.lookup(data, "model", str(good))["ownership"], "INSTALLER_OWNED")
        self.assertEqual(self.lookup(data, "model", str(other))["ownership"], "UNVERIFIED")
        self.assertFalse(data["issues"])

    def test_image_and_model_name_prefix_alone_remain_unverified(self) -> None:
        unrelated = self.models / "qwen3.8-other-application"
        unrelated.mkdir()
        self.images = [
            {"Repository": "vllm-other-application", "Tag": "v1"},
            {"Repository": "qwen38-unrelated", "Tag": "test"},
        ]
        result = self.gather()
        self.assertEqual(self.lookup(result, "model", str(unrelated))["ownership"],
                         "UNVERIFIED")
        for name in ("vllm-other-application:v1", "qwen38-unrelated:test"):
            self.assertEqual(self.lookup(result, "image", name)["ownership"],
                             "UNVERIFIED")
        self.assertEqual(result["issues"], [])

    def test_registry_owned_image_does_not_own_other_similar_tags(self) -> None:
        owned_tag = "vllm-skinny-tp1:v1"
        unrelated_tag = "vllm-another-research:v1"
        (self.state / "asset-ownership.json").write_text(json.dumps({
            "schema_version": 1,
            "assets": [{
                "kind": "image", "locator": owned_tag, "root": "",
                "owned": True, "state": "ready",
                "fingerprint": "sha256:" + "b" * 64,
                "depends_on": [],
            }],
        }))
        self.images = [
            {"Repository": "vllm-skinny-tp1", "Tag": "v1"},
            {"Repository": "vllm-another-research", "Tag": "v1"},
        ]
        result = self.gather()
        self.assertEqual(self.lookup(result, "image", owned_tag)["ownership"],
                         "INSTALLER_OWNED")
        self.assertEqual(self.lookup(result, "image", unrelated_tag)["ownership"],
                         "UNVERIFIED")

    def make_model_provenance_fixture(self, *, status: str = "complete",
                                      wrong_size: bool = False,
                                      as_symlink: bool = False) -> dict:
        import hashlib
        model = self.models / "qwen3.8-flash-next-orcarouter"
        model.mkdir()
        weight = model / "model.safetensors"
        weight.write_bytes(b"TEST_SHARD")
        if as_symlink:
            weight.unlink()
            target = self.root / "foreign-model-weight"
            target.write_bytes(b"FOREIGN")
            weight.symlink_to(target)
        marker = model / ".qwen38-model-manifest.json"
        obj = {
            "schema_version": 1,
            "status": status,
            "repository": "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4",
            "revision": "a" * 40,
            "files": [{
                "path": "model.safetensors",
                "size": 99 if wrong_size else 10,
                "sha256": None,
            }],
        }
        marker.write_text(json.dumps(obj), encoding="utf-8")
        (self.state / "asset-ownership.json").write_text(json.dumps({
            "schema_version": 1,
            "assets": [{
                "kind": "model", "locator": str(model),
                "root": str(self.models), "owned": False,
                "state": "ready",
                "fingerprint": hashlib.sha256(marker.read_bytes()).hexdigest(),
                "depends_on": [],
            }],
        }), encoding="utf-8")
        return {
            "scope": {"state": str(self.state), "checkout": str(self.checkout)},
            "issues": [],
            "resources": [{
                "kind": "model", "locator": str(model),
                "status": "PRESENT", "ownership": "UNVERIFIED",
            }],
        }

    def test_model_provenance_reports_consistent_metadata_without_ownership(self) -> None:
        fixture = self.make_model_provenance_fixture()
        result = audit.model_provenance_audit(fixture)
        self.assertEqual(result["result"], "CONSISTENT_METADATA_NOT_OWNERSHIP")
        self.assertEqual(len(result["models"]), 1)
        model = result["models"][0]
        self.assertFalse(model["registry_owned"])
        self.assertEqual(model["marker_status"], "complete")
        self.assertTrue(model["recorded_sha256_matches"])
        self.assertEqual(model["present_regular_files"], 1)
        self.assertEqual(model["content_sha256_verified"], 0)
        self.assertEqual(model["issues"], [])

    def test_model_provenance_detects_incomplete_marker_and_bad_weight(self) -> None:
        cases = (
            ({"status": "downloading"}, "model_marker_not_complete"),
            ({"wrong_size": True}, "model_file_size_mismatch"),
            ({"as_symlink": True}, "symlinked_model_file_or_parent"),
        )
        for kwargs, expected in cases:
            with self.subTest(case=kwargs):
                fixture = self.make_model_provenance_fixture(**kwargs)
                result = audit.model_provenance_audit(fixture)
                self.assertEqual(result["result"], "REVIEW_REQUIRED")
                self.assertIn(expected, json.dumps(result))
                model = self.models / "qwen3.8-flash-next-orcarouter"
                marker = model / ".qwen38-model-manifest.json"
                marker.unlink()
                weight = model / "model.safetensors"
                weight.unlink()
                model.rmdir()

    def test_model_provenance_detects_marker_registry_drift(self) -> None:
        fixture = self.make_model_provenance_fixture()
        model = self.models / "qwen3.8-flash-next-orcarouter"
        marker = model / ".qwen38-model-manifest.json"
        doc = json.loads(marker.read_text())
        doc["revision"] = "b" * 40
        marker.write_text(json.dumps(doc), encoding="utf-8")
        result = audit.model_provenance_audit(fixture)
        self.assertEqual(result["result"], "REVIEW_REQUIRED")
        self.assertIn("marker_registry_fingerprint_mismatch", json.dumps(result))
        self.assertFalse(result["models"][0]["recorded_sha256_matches"])

    def reference_fixture(self, *, source: str = "", volume: bool = False,
                          same_image: bool = False, alias: bool = False) -> dict:
        """Isolated known project and foreign Docker identity fixture."""
        project_id, external_id = "a" * 64, "b" * 64
        image_id = "sha256:" + "c" * 64
        model = self.models / "qwen3.8-flash-next-orcarouter"
        model.mkdir(exist_ok=True)
        project_tag = "vllm-orcarouter-v029:v1"
        rows = [
            {"kind": "container", "locator": project_id,
             "status": "PRESENT", "ownership": "PROJECT_ASSOCIATED"},
            {"kind": "image", "locator": project_tag,
             "status": "PRESENT", "ownership": "UNVERIFIED"},
            {"kind": "model", "locator": str(model),
             "status": "PRESENT", "ownership": "UNVERIFIED"},
            {"kind": "volume", "locator": "qwen38-owned-volume",
             "status": "PRESENT", "ownership": "UNVERIFIED"},
            {"kind": "shared-runtime-cache",
             "locator": str(self.root / ".cache/flashinfer"),
             "status": "PRESENT", "ownership": "EXCLUDED_SHARED"},
        ]
        observed = {"issues": [], "resources": rows,
                    "scope": {"checkout": str(self.checkout)}}
        def fake_docker(*args: str) -> list[dict]:
            if args[:2] == ("image", "inspect"):
                self.assertEqual(args[2], project_tag)
                return [{"Id": image_id}]
            if args[0] == "ps":
                return [{"ID": project_id}, {"ID": external_id}]
            if args[0] == "inspect":
                self.assertEqual(args[1], external_id)
                return [{"Id": external_id,
                         "Image": image_id if same_image else "sha256:" + "d" * 64,
                         "Mounts": [{
                             "Type": "bind", "Source": source,
                             "Name": "qwen38-owned-volume" if volume else None
                         }] if source or volume else []}]
            if args[:2] == ("image", "ls"):
                rows = [{"ID": image_id, "Repository": "vllm-orcarouter-v029",
                         "Tag": "v1"}]
                if alias:
                    rows.append({"ID": image_id, "Repository": "other-project",
                                 "Tag": "shared"})
                return rows
            raise AssertionError(args)
        with patch.object(audit, "run_docker", side_effect=fake_docker):
            return audit.reference_audit(observed)

    def test_reference_audit_no_external_conflict_does_not_claim_ownership(self) -> None:
        result = self.reference_fixture(source=str(self.root / ".cache/flashinfer"))
        self.assertEqual(result["result"], "NO_OBSERVED_CONFLICTS")
        self.assertEqual(result["project_container_count"], 1)
        self.assertEqual(result["external_container_count"], 1)
        self.assertEqual(result["project_image_count"], 1)
        self.assertIn("not_an_ownership_proof", result["limitations"])

    def test_reference_audit_rejects_external_image_mount_volume_and_alias(self) -> None:
        model = str(self.models / "qwen3.8-flash-next-orcarouter")
        cases = (
            ({"same_image": True}, "project_image_id"),
            ({"source": model}, "project_file_mount"),
            ({"volume": True}, "project_docker_volume"),
            ({"alias": True}, "other-project:shared"),
        )
        for kwargs, expected in cases:
            with self.subTest(case=kwargs):
                result = self.reference_fixture(**kwargs)
                self.assertEqual(result["result"], "CONFLICTS")
                self.assertIn(expected, json.dumps(result))

    def test_reference_audit_fails_closed_when_full_docker_list_drifts(self) -> None:
        project_id = "a" * 64
        observed = {"issues": [],
                    "resources": [{"kind": "container", "locator": project_id,
                                   "status": "PRESENT",
                                   "ownership": "PROJECT_ASSOCIATED"}],
                    "scope": {"checkout": str(self.checkout)}}
        with patch.object(audit, "run_docker", return_value=[]):
            with self.assertRaisesRegex(
                    RuntimeError, "reference_container_inventory_drift"):
                audit.reference_audit(observed)
        observed["issues"] = ["docker_inventory_incomplete"]
        with self.assertRaisesRegex(RuntimeError, "project_inventory_incomplete"):
            audit.reference_audit(observed)

    def test_invalid_registry_fails_closed(self) -> None:
        (self.state / "asset-ownership.json").write_text("{bad")
        data = self.gather()
        self.assertTrue(any("asset_registry_invalid" in x for x in data["issues"]))

    def test_unit_marker_required_for_attribution(self) -> None:
        good = self.units / "qwen38-flash-next.service"
        good.write_text("# Managed qwen38-spark runtime service\n")
        bad = self.units / "qwen38-openwebui-proxy.socket"
        bad.write_text("Not managed\n")
        data = self.gather()
        self.assertEqual(self.lookup(data, "systemd", str(good))["ownership"], "INSTALLER_OWNED")
        self.assertEqual(self.lookup(data, "systemd", str(bad))["ownership"], "UNVERIFIED")

    def test_symlinked_unit_is_not_followed(self) -> None:
        (self.units / "qwen38-flash-next.service").symlink_to("/etc/passwd")
        data = self.gather()
        self.assertEqual(self.lookup(data, "systemd",
                                     str(self.units / "qwen38-flash-next.service"))["status"],
                         "UNSAFE_SYMLINK")

    def test_swap_fstab_registration_is_visible_even_if_file_absent(self) -> None:
        self.fstab.write_text(f"{self.swap} none swap sw,pri=10 0 0 # qwen38-ple-swap\n",
                              encoding="utf-8")
        data = self.gather()
        self.assertEqual(self.lookup(data, "swap-fstab",
                                     str(self.fstab) + "#qwen38-ple-swap")["status"],
                         "PRESENT")

    def test_project_docker_volume_is_reported_not_automatically_owned(self) -> None:
        self.volumes = [{"Name": "qwen38-research", "Labels": "qwen38.variant=test"}]
        data = self.gather()
        self.assertEqual(self.lookup(data, "volume", "qwen38-research")["ownership"],
                         "UNVERIFIED")

    def test_project_runtime_caches_are_separate_from_shared_parent(self) -> None:
        dedicated = self.root / ".cache/vllm-qwen38-v029"
        shared = self.root / ".cache/flashinfer"
        dedicated.mkdir(parents=True)
        shared.mkdir(parents=True)
        data = self.gather()
        self.assertEqual(self.lookup(data, "project-cache", str(dedicated))["status"],
                         "PRESENT")
        self.assertEqual(self.lookup(data, "shared-runtime-cache", str(shared))["ownership"],
                         "EXCLUDED_SHARED")

    def test_shared_hf_cache_is_never_an_automatic_purge_candidate(self) -> None:
        data = self.gather()
        self.assertEqual(self.lookup(data, "hf-cache", str(self.hf))["ownership"],
                         "EXCLUDED_SHARED")

    def test_baseline_verification_detects_new_and_existing_residues(self) -> None:
        self.swap.write_bytes(b"x")
        before = self.gather()
        result, details = audit.verification(before, self.gather())
        self.assertEqual(result, "RESIDUALS_PRESENT")
        self.assertTrue(any("swap:" in x for x in details))

    def test_postcheck_does_not_greenlight_without_coverage(self) -> None:
        before = self.gather()
        self.assertEqual(audit.verification(before, self.gather())[0],
                         "RESIDUALS_PRESENT")  # fixture has state/data/hf
        unknown = self.gather(error=True)
        self.assertEqual(audit.verification(before, unknown)[0], "INCOMPLETE")

    def test_postcheck_pass_is_limited_to_deleted_project_scope(self) -> None:
        before = self.gather()
        self.state.rmdir()
        self.data.rmdir()
        after = self.gather()
        outcome, leftovers = audit.verification(before, after)
        self.assertEqual(outcome, "PROJECT_SCOPE_NO_RESIDUALS")
        self.assertEqual(leftovers, [])

    def test_dangling_ownership_symlink_fails_closed(self) -> None:
        (self.state / "asset-ownership.json").symlink_to(
            self.root / "missing-registry.json")
        data = self.gather()
        self.assertTrue(any("asset_registry_invalid" in x for x in data["issues"]))

    def test_existing_unit_runtime_is_a_residual_without_a_unit_file(self) -> None:
        with (patch.object(audit, "run_docker", return_value=[]),
              patch.object(audit, "run_unit_status", return_value={
                  "LoadState": "loaded", "ActiveState": "active",
              })):
            data = audit.gather(
                state=self.state, data=self.data, models=self.models,
                units=self.units, swap=self.swap, hf=self.hf, fstab=self.fstab,
                home=self.root, checkout=self.checkout,
            )
        self.assertEqual(self.lookup(data, "unit-runtime",
                                     "qwen38-flash-next.service")["status"],
                         "PRESENT")

    def test_unreadable_fstab_reports_incomplete(self) -> None:
        self.fstab.unlink()
        data = self.gather()
        self.assertIn("fstab_unavailable_or_unsafe", data["issues"])

    def test_complete_scope_includes_orcarouter_and_all_three_mazinb_r2_containers(self) -> None:
        model = self.models / "qwen3.8-flash-next-orcarouter"
        model.mkdir()
        ids = ("82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424",
               "68cd243882bf117dbccdfad577cfdec7a95063ee8f2a96dbe6bcf51cfd8554e7",
               "bee2e3819b7c2fef595357b61ea23934dd8969215a7fe2b957678bbf98eb1dd8",
               "f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24")
        self.containers = [
            {"ID": ids[0], "Names": "qwen38-mazinb-m1-20261019054700-first",
             "Labels": "qwen38.abtrial=mazinb"},
            {"ID": ids[1], "Names": "qwen38-mazinb-m1-20261019065452-e70d6233",
             "Labels": "qwen38.abtrial=mazinb"},
            {"ID": ids[2], "Names": "qwen38-mazinb-m1-20261019221159-90ee9851",
             "Labels": "qwen38.abtrial=mazinb"},
            {"ID": ids[3], "Names": "qwen38-flash-next",
             "Labels": ""},
        ]
        result = self.gather()
        self.assertEqual(self.lookup(result, "model", str(model))["status"], "PRESENT")
        for cid in ids:
            self.assertEqual(self.lookup(result, "container", cid)["status"], "PRESENT")
        self.assertFalse(result["issues"])

    def test_legacy_checkout_model_symlink_is_reported_as_unsafe_not_followed(self) -> None:
        target = self.models / "qwen3.8-flash-next-orcarouter"
        target.mkdir()
        link = self.checkout / "model"
        link.symlink_to(target)
        data = self.gather()
        row = self.lookup(data, "model", str(link))
        self.assertEqual(row["status"], "UNSAFE_SYMLINK")
        self.assertEqual(row["ownership"], "UNVERIFIED")
        self.assertTrue(link.is_symlink())
        self.assertTrue(target.is_dir())

    def test_legacy_orcarouter_checkout_model_is_a_review_candidate(self) -> None:
        legacy = self.checkout / "model"
        legacy.mkdir()
        result = self.gather()
        row = self.lookup(result, "model", str(legacy))
        self.assertEqual(row["status"], "PRESENT")
        self.assertEqual(row["ownership"], "UNVERIFIED")

    def test_local_and_checkout_forensic_evidence_are_full_purge_targets(self) -> None:
        local = self.root / "Workspace/llm/qwen38-m1-bench-results"
        local.mkdir(parents=True)
        local_archive = self.state / "retirement-archives"
        local_archive.mkdir()
        repo_archive = self.checkout / "docs/model-reports/evidence"
        repo_archive.mkdir(parents=True)
        result = self.gather()
        for path in (local, local_archive, repo_archive):
            row = self.lookup(result, "forensic", str(path))
            self.assertEqual(row["status"], "PRESENT")
            self.assertNotEqual(row["ownership"], "EXCLUDED_SHARED")
        self.assertEqual(audit.verification(result, result)[0], "RESIDUALS_PRESENT")

    def test_only_project_specific_hf_cache_is_in_purge_scope(self) -> None:
        hub = self.hf / "hub"
        hub.mkdir()
        project = hub / "models--mazinb--Qwen3.8-Flash-Next-Uncensored-NVFP4"
        foreign = hub / "models--elsewhere--unrelated"
        project.mkdir()
        foreign.mkdir()
        result = self.gather()
        self.assertEqual(self.lookup(result, "model-cache", str(project))["status"], "PRESENT")
        self.assertFalse(any(row["locator"] == str(foreign)
                             for row in result["resources"]))
        self.assertEqual(self.lookup(result, "hf-cache", str(self.hf))["ownership"],
                         "EXCLUDED_SHARED")

    def test_baseline_scope_drift_fails_closed(self) -> None:
        before = self.gather()
        before["scope"]["state"] = "/wrong"
        result, _ = audit.verification(before, self.gather())
        self.assertEqual(result, "INVALID_BASELINE")

    def test_no_mutator_in_source_and_wizard_route_is_read_only(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in ('"docker", "rm"', '"docker", "stop"',
                          '"systemctl", "disable"', '"swapoff"', "shutil.rmtree"):
            self.assertNotIn(forbidden, source)
        wizard = (ROOT / "scripts/wizard/menus.sh").read_text(encoding="utf-8")
        self.assertIn("uninstall-inventory.py", wizard)


if __name__ == "__main__":
    unittest.main()
