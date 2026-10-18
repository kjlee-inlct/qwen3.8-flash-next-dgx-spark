"""Synthetic offline gates for the source-only official ARM64 C preflight."""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
from unittest import TestCase, mock

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/runtime/orcarouter-peer-c-readonly.py"
SPEC = importlib.util.spec_from_file_location("orcarouter_peer_c_readonly", TARGET)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class PeerCReadOnlyTests(TestCase):
    def test_plan_never_reaches_host_or_docker(self):
        with mock.patch.object(MOD, "command", side_effect=AssertionError("host call")), \
             mock.patch.object(MOD, "metadata", side_effect=AssertionError("Docker")), \
             mock.patch.object(MOD.shutil, "disk_usage", side_effect=AssertionError("disk")), \
             redirect_stdout(io.StringIO()) as out:
            MOD.plan()
        self.assertIn("PEER_C_MODEL_START=NOT_IMPLEMENTED_OR_AUTHORIZED", out.getvalue())
        self.assertIn("PEER_C_IMAGE_PULL=NO_ACTION_BY_THIS_READ_ONLY_TOOL", out.getvalue())
        self.assertIn(MOD.DIGEST, out.getvalue())

    def test_no_image_blocks(self):
        with mock.patch.object(MOD, "metadata", return_value=None):
            self.assertEqual(MOD.image_receipt(), "ABSENT_EXACT_AND_TAG")

    def test_pinned_manifest_is_not_config_image_id(self):
        exact = {"Os": "linux", "Architecture": "arm64",
                 "RepoDigests": [MOD.PINNED], "Id": MOD.EXPECTED_IMAGE_ID}
        with mock.patch.object(MOD, "metadata",
                               side_effect=lambda name, *, image: exact if name == MOD.PINNED else None):
            self.assertEqual(MOD.image_receipt(), "PINNED_MATCH")

    def test_tag_digest_mismatch_blocks(self):
        tagged = {"Os": "linux", "Architecture": "arm64",
                  "RepoDigests": ["vllm/vllm-openai@sha256:" + "b" * 64],
                  "Id": "sha256:" + "a" * 64}
        with mock.patch.object(MOD, "metadata",
                               side_effect=lambda name, *, image: tagged if name == MOD.TAG else None):
            self.assertEqual(MOD.image_receipt(), "DIGEST_NOT_ATTESTED")

    def test_same_digest_wrong_image_config_id_blocks(self):
        exact = {"Os": "linux", "Architecture": "arm64",
                 "RepoDigests": [MOD.PINNED], "Id": MOD.EXPECTED_IMAGE_ID}
        tagged = {**exact, "Id": "sha256:" + "b" * 64}
        with mock.patch.object(MOD, "metadata",
                               side_effect=lambda name, *, image: exact if name == MOD.PINNED else tagged):
            self.assertEqual(MOD.image_receipt(), "IMAGE_CONFIG_ID_MISMATCH")

    def test_protected_three_stopped_exact_ids(self):
        def stopped(name):
            cid, image_id = MOD.PROTECTED_IDENTITIES[name]
            return {"Id": cid, "Image": image_id, "State": {
                "Status": "exited", "Running": False, "OOMKilled": False}}
        data = {name: stopped(name) for name in MOD.PROTECTED}
        with mock.patch.object(MOD, "metadata",
                               side_effect=lambda name, *, image: data.get(name)):
            self.assertEqual(MOD.protected_receipt(), "THREE_STOPPED_EXISTING_IDS")
        data[MOD.PROTECTED[-1]]["State"]["Running"] = True
        with mock.patch.object(MOD, "metadata",
                               side_effect=lambda name, *, image: data.get(name)):
            self.assertEqual(MOD.protected_receipt(), "PROTECTED_CONTAINER_NOT_STOPPED")

    def test_protected_image_id_drift_blocks(self):
        data = {name: {"Id": identity[0], "Image": identity[1],
                        "State": {"Status": "exited", "Running": False,
                                  "OOMKilled": False}}
                for name, identity in MOD.PROTECTED_IDENTITIES.items()}
        data["qwen38-ab-v029"]["Image"] = "sha256:" + "f" * 64
        with mock.patch.object(MOD, "metadata",
                               side_effect=lambda name, *, image: data.get(name)):
            self.assertEqual(MOD.protected_receipt(), "PROTECTED_ID_OR_IMAGE_DRIFT")

    def test_runtime_entrypoint_matches_without_source_attestation(self):
        data = {"Config": {
            "Entrypoint": ["vllm", "serve"], "WorkingDir": "/vllm-workspace",
            "Env": ["CUDA_VERSION=13.0.1", "VLLM_BUILD_COMMIT=unknown",
                    "VLLM_IMAGE_TAG=local/vllm-openai:dev"]}}
        with mock.patch.object(MOD, "metadata", return_value=data):
            self.assertEqual(MOD.image_runtime_receipt(),
                             "ENTRYPOINT_SHAPE_MATCH_WHEEL_SOURCE_UNATTESTED")

    def test_runtime_cmd_absent_is_valid_but_unexpected_cmd_blocks(self):
        data = {"Config": {
            "Entrypoint": ["vllm", "serve"], "WorkingDir": "/vllm-workspace",
            "Cmd": ["unexpected"], "Env": ["CUDA_VERSION=13.0.1"]}}
        with mock.patch.object(MOD, "metadata", return_value=data):
            self.assertEqual(MOD.image_runtime_receipt(),
                             "UNEXPECTED_IMAGE_DEFAULT_CMD")

    def test_runtime_entrypoint_mismatch_blocks(self):
        data = {"Config": {
            "Entrypoint": ["/bin/bash"], "WorkingDir": "/vllm-workspace",
            "Env": ["CUDA_VERSION=13.0.1"]}}
        with mock.patch.object(MOD, "metadata", return_value=data):
            self.assertEqual(MOD.image_runtime_receipt(),
                             "ENTRYPOINT_MISMATCH")

    def test_runtime_absent_image_blocks(self):
        with mock.patch.object(MOD, "metadata", return_value=None):
            self.assertEqual(MOD.image_runtime_receipt(),
                             "PINNED_IMAGE_NOT_INSPECTABLE")

    def test_missing_pinned_image_is_not_live_admission(self):
        with mock.patch.object(MOD, "image_receipt", return_value="ABSENT_EXACT_AND_TAG"), \
             mock.patch.object(MOD, "image_runtime_receipt",
                               return_value="PINNED_IMAGE_NOT_INSPECTABLE"), \
             mock.patch.object(MOD, "protected_receipt", return_value="THREE_STOPPED_EXISTING_IDS"), \
             mock.patch.object(MOD, "command", return_value=(3, "")), \
             mock.patch.object(MOD.platform, "machine", return_value="aarch64"), \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(MOD.preflight(), 2)
        self.assertIn("PEER_C_ADMISSION=BLOCKED_IMAGE_NOT_INSTALLED", out.getvalue())
        self.assertIn("PEER_C_BENCHMARK=NOT_MEASURED", out.getvalue())
        self.assertIn("PEER_C_OPERATION=PREFLIGHT_READ_ONLY_HOST_INSPECTION",
                      out.getvalue())

    def test_pass_still_does_not_authorize_runtime(self):
        with mock.patch.object(MOD, "image_receipt", return_value="PINNED_MATCH"), \
             mock.patch.object(MOD, "image_runtime_receipt",
                               return_value="ENTRYPOINT_SHAPE_MATCH_WHEEL_SOURCE_UNATTESTED"), \
             mock.patch.object(MOD, "protected_receipt", return_value="THREE_STOPPED_EXISTING_IDS"), \
             mock.patch.object(MOD, "command", return_value=(3, "")), \
             mock.patch.object(MOD.platform, "machine", return_value="aarch64"), \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(MOD.preflight(), 0)
        self.assertIn("PEER_C_ADMISSION=SOURCE_READ_ONLY_PREFLIGHT_PASS_NOT_LIVE_APPROVAL", out.getvalue())
        self.assertIn("PEER_C_MODEL_START=NOT_IMPLEMENTED_OR_AUTHORIZED", out.getvalue())

    def test_unknown_managed_service_is_not_declared_inactive(self):
        with mock.patch.object(MOD, "image_receipt", return_value="PINNED_MATCH"), \
             mock.patch.object(MOD, "image_runtime_receipt",
                               return_value="ENTRYPOINT_SHAPE_MATCH_WHEEL_SOURCE_UNATTESTED"), \
             mock.patch.object(MOD, "protected_receipt", return_value="THREE_STOPPED_EXISTING_IDS"), \
             mock.patch.object(MOD, "command", return_value=(4, "")), \
             mock.patch.object(MOD.platform, "machine", return_value="aarch64"), \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(MOD.preflight(), 0)
        self.assertIn("PEER_C_MANAGED_SERVICE=UNKNOWN_NOT_LIVE_APPROVED", out.getvalue())
        self.assertIn("PEER_C_ADMISSION=SOURCE_READ_ONLY_PREFLIGHT_PASS_NOT_LIVE_APPROVAL",
                      out.getvalue())

    def test_active_managed_service_blocks_static_preflight(self):
        with mock.patch.object(MOD, "image_receipt", return_value="PINNED_MATCH"), \
             mock.patch.object(MOD, "image_runtime_receipt",
                               return_value="ENTRYPOINT_SHAPE_MATCH_WHEEL_SOURCE_UNATTESTED"), \
             mock.patch.object(MOD, "protected_receipt", return_value="THREE_STOPPED_EXISTING_IDS"), \
             mock.patch.object(MOD, "command", return_value=(0, "")), \
             mock.patch.object(MOD.platform, "machine", return_value="aarch64"), \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(MOD.preflight(), 2)
        self.assertIn("PEER_C_MANAGED_SERVICE=ACTIVE_OR_UNCLASSIFIED", out.getvalue())
        self.assertIn("PEER_C_ADMISSION=BLOCKED_REVIEW", out.getvalue())

    def test_docker_metadata_uses_inspect_only(self):
        def fake_command(*args):
            self.assertEqual(args[0], "docker")
            self.assertIn("inspect", args)
            self.assertNotIn("run", args)
            self.assertNotIn("pull", args)
            return (1, "")
        with mock.patch.object(MOD, "command", side_effect=fake_command):
            self.assertIsNone(MOD.metadata(MOD.PINNED, image=True))
            self.assertIsNone(MOD.metadata("qwen38-flash-next", image=False))
