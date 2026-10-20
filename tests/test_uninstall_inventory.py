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
