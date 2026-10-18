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
        self.assertIn("PEER_C_IMAGE_PULL=NOT_PERFORMED_OR_AUTHORIZED", out.getvalue())
        self.assertIn(MOD.DIGEST, out.getvalue())

    def test_no_image_blocks(self):
        with mock.patch.object(MOD, "metadata", return_value=None):
            self.assertEqual(MOD.image_receipt(), "ABSENT_EXACT_AND_TAG")

    def test_pinned_manifest_is_not_config_image_id(self):
        exact = {"Os": "linux", "Architecture": "arm64",
                 "RepoDigests": [MOD.PINNED], "Id": "sha256:" + "a" * 64}
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

    def test_mixed_alias_ids_block(self):
        exact = {"Os": "linux", "Architecture": "arm64",
                 "RepoDigests": [MOD.PINNED], "Id": "sha256:" + "a" * 64}
        tagged = {**exact, "Id": "sha256:" + "b" * 64}
        with mock.patch.object(MOD, "metadata",
                               side_effect=lambda name, *, image: exact if name == MOD.PINNED else tagged):
            self.assertEqual(MOD.image_receipt(), "TAG_ID_DIFFERS_FROM_PINNED")

    def test_protected_three_stopped_exact_ids(self):
        def stopped(i):
            return {"Id": str(i) * 64, "State": {
                "Status": "exited", "Running": False, "OOMKilled": False}}
        data = dict(zip(MOD.PROTECTED, [stopped(1), stopped(2), stopped(3)]))
        with mock.patch.object(MOD, "metadata",
                               side_effect=lambda name, *, image: data.get(name)):
            self.assertEqual(MOD.protected_receipt(), "THREE_STOPPED_EXISTING_IDS")
        data[MOD.PROTECTED[-1]]["State"]["Running"] = True
        with mock.patch.object(MOD, "metadata",
                               side_effect=lambda name, *, image: data.get(name)):
            self.assertEqual(MOD.protected_receipt(), "PROTECTED_CONTAINER_NOT_STOPPED")

    def test_missing_pinned_image_is_not_live_admission(self):
        with mock.patch.object(MOD, "image_receipt", return_value="ABSENT_EXACT_AND_TAG"), \
             mock.patch.object(MOD, "protected_receipt", return_value="THREE_STOPPED_EXISTING_IDS"), \
             mock.patch.object(MOD, "command", return_value=(3, "")), \
             mock.patch.object(MOD.platform, "machine", return_value="aarch64"), \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(MOD.preflight(), 2)
        self.assertIn("PEER_C_ADMISSION=BLOCKED_IMAGE_NOT_INSTALLED", out.getvalue())
        self.assertIn("PEER_C_BENCHMARK=NOT_MEASURED", out.getvalue())

    def test_pass_still_does_not_authorize_runtime(self):
        with mock.patch.object(MOD, "image_receipt", return_value="PINNED_MATCH"), \
             mock.patch.object(MOD, "protected_receipt", return_value="THREE_STOPPED_EXISTING_IDS"), \
             mock.patch.object(MOD, "command", return_value=(3, "")), \
             mock.patch.object(MOD.platform, "machine", return_value="aarch64"), \
             redirect_stdout(io.StringIO()) as out:
            self.assertEqual(MOD.preflight(), 0)
        self.assertIn("PEER_C_ADMISSION=SOURCE_READ_ONLY_PREFLIGHT_PASS_NOT_LIVE_APPROVAL", out.getvalue())
        self.assertIn("PEER_C_MODEL_START=NOT_IMPLEMENTED_OR_AUTHORIZED", out.getvalue())

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
