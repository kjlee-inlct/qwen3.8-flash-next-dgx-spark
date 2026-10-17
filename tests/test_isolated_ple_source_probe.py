"""Offline-only tests for tightly gated single temporary Docker source inspection.

No tests invoke Docker, GPU, network, or the protected physical DGX.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "scripts/model/probe_isolated_ple_source.py"
sys.path.insert(0, str(SRC.parent))
spec = importlib.util.spec_from_file_location("isolated_ple_probe", SRC)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def source_code() -> str:
    return (
        "class Qwen3_8FlashNextPLEFp8EmbeddingMethod:\n"
        "    def create_weights(self, layer):\n"
        "        scale_dtype = torch.bfloat16\n"
        "        layer.register_parameter('weight_scale', scale_dtype)\n"
        "    def embedding(self, layer, input_):\n"
        "        return F.embedding(input_, layer.weight)\n"
        "def _get_ple_embedding_quant_method(quant_config, prefix):\n"
        "    if not isinstance(quant_config, Fp8Config):\n"
        "        return None\n"
        "    return Qwen3_8FlashNextPLEFp8EmbeddingMethod()\n"
        "def _dequantize_embeddings(embeddings, weight_scale):\n"
        "    return embeddings * weight_scale\n"
    )


def tar_file(name: str, text: str) -> bytes:
    raw = text.encode("utf-8")
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w") as tar:
        info = tarfile.TarInfo(name)
        info.size = len(raw)
        tar.addfile(info, io.BytesIO(raw))
    return out.getvalue()


def fixture():
    mounts = [
        {"Destination": "/model", "Type": "bind", "RW": False,
         "Source": "/private/checkpoint"},
        {"Destination": "/model/config.json", "Type": "bind", "RW": False,
         "Source": "/private/config"},
    ]
    image = {
        "Id": mod.EXPECTED_IMAGE_ID,
        "Size": mod.EXPECTED_IMAGE_SIZE,
        "Config": {"Volumes": None},
    }
    managed = {
        "Id": mod.EXPECTED_MANAGED_ID,
        "Name": "/qwen38-flash-next",
        "Image": mod.EXPECTED_IMAGE_ID,
        "Config": {"Image": mod.ple.IMAGE_TAG},
        "State": {"Status": "exited"},
        "HostConfig": {"ReadonlyRootfs": False},
        "Mounts": copy.deepcopy(mounts),
    }
    legacy = {
        "Id": mod.EXPECTED_LEGACY_ID,
        "Name": "/qwen38-ab-legacy",
        "Image": mod.EXPECTED_IMAGE_ID,
        "Config": {"Image": mod.ple.IMAGE_TAG},
        "State": {"Status": "exited"},
        "HostConfig": {"ReadonlyRootfs": False},
        "Mounts": copy.deepcopy(mounts),
    }
    return image, managed, legacy


class FakeDocker:
    def __init__(self):
        self.image, self.managed, self.legacy = fixture()
        self.calls = []
        self.temp = None
        self.cid = "e" * 64
        self.temp_removed = False
        self.control_failure = False
        self.source_failure = False
        self.changes_temp_state = False
        self.change_protected = False
        self.missing_src = False

    def __call__(self, args, limit=mod.MAX_DOCKER_META_BYTES):
        self.calls.append(tuple(args))
        if args == ["image", "inspect", mod.ple.IMAGE_TAG]:
            return json.dumps([self.image]).encode()
        if args == ["container", "inspect", mod.ple.MANAGED_CONTAINER]:
            return json.dumps([self.managed]).encode()
        if args == ["container", "inspect", mod.ple.LEGACY_CONTAINER]:
            return json.dumps([self.legacy]).encode()
        if args == ["container", "inspect", mod.EXPECTED_MANAGED_ID]:
            return json.dumps([self.managed]).encode()
        if args == ["container", "inspect", mod.EXPECTED_LEGACY_ID]:
            return json.dumps([self.legacy]).encode()
        if args == ["container", "create", *args[2:]]:
            assert not self.temp
            assert "--network" in args and args[args.index("--network") + 1] == "none"
            assert "--runtime" in args and args[args.index("--runtime") + 1] == "runc"
            assert "--pull" in args and args[args.index("--pull") + 1] == "never"
            assert args[-1] == mod.EXPECTED_IMAGE_ID
            name = args[args.index("--name") + 1]
            nonce = None
            for i, arg in enumerate(args):
                if arg == "--label" and args[i+1].startswith(
                    "com.qwen38.source-probe.nonce="
                ):
                    nonce = args[i+1].split("=", 1)[1]
            assert nonce
            self.temp = {
                "Id": self.cid,
                "Name": "/" + name,
                "Image": mod.EXPECTED_IMAGE_ID,
                "Config": {"Labels": {
                    mod.PROBE_LABEL_KEY: mod.PROBE_LABEL_VALUE,
                    "com.qwen38.source-probe.nonce": nonce,
                }},
                "State": {"Status": "created"},
                "Mounts": [],
                "HostConfig": {
                    "Binds": None, "Privileged": False, "ReadonlyRootfs": False, "NetworkMode": "none",
                    "RestartPolicy": {"Name": "no"}, "Devices": [],
                    "Runtime": "runc",
                },
            }
            return (self.cid + "\n").encode()
        if args == ["container", "inspect", self.cid]:
            if self.temp_removed:
                raise mod.CommandFailed("CONTAINER_NOT_FOUND")
            result = copy.deepcopy(self.temp)
            if self.changes_temp_state:
                result["State"]["Status"] = "running"
            return json.dumps([result]).encode()
        if args[:1] == ["cp"]:
            assert args[-1] == "-"
            assert args[1].startswith(self.cid + ":")
            if args[1].endswith(":/etc/group"):
                if self.control_failure:
                    raise mod.CommandFailed("FILESYSTEM_READ_ONLY")
                return tar_file("group", "root:x:0:\n")
            if self.missing_src:
                raise mod.CommandFailed("SOURCE_PATH_NOT_FOUND")
            if args[1].endswith(mod.ple.SOURCE_RELATIVE):
                if self.source_failure:
                    raise mod.CommandFailed("DOCKER_TIMEOUT")
                return tar_file("ple_layer.py", source_code())
            raise AssertionError("Unexpected path")
        if args == ["container", "rm", self.cid]:
            assert not self.temp_removed
            self.temp_removed = True
            if self.change_protected:
                self.managed["State"]["Status"] = "running"
            return (self.cid + "\n").encode()
        if args == ["info", "--format", "{{.DockerRootDir}}"]:
            return b"/tmp\n"
        raise AssertionError("Unexpected Docker request " + repr(args))


class IsolatedProbeTests(unittest.TestCase):
    def run_execute(self, fake: FakeDocker):
        out = io.StringIO()
        with patch.object(mod, "docker", side_effect=fake), patch.object(
            mod, "available_docker_space",
            return_value=(mod.MIN_FREE_BYTES + 4096, mod.MIN_FREE_INODES + 5)
        ), patch.object(mod.secrets, "token_hex", return_value="abcd1234abcd1234abcd1234"):
            with redirect_stdout(out):
                result = mod.main([
                    "--execute", "--approved-image-id", mod.EXPECTED_IMAGE_ID,
                    "--approved-scope", mod.APPROVAL_SCOPE,
                ])
        return result, out.getvalue()

    def test_default_plan_no_mutations(self):
        fake = FakeDocker()
        out = io.StringIO()
        with patch.object(mod, "docker", side_effect=fake), redirect_stdout(out):
            code = mod.main([])
        self.assertEqual(code, 0)
        self.assertEqual(len(fake.calls), 3)
        self.assertFalse(any(x[1] in ("create", "cp", "rm") for x in fake.calls))
        self.assertIn("PLAN_ONLY_PROTECTED_IDENTITIES_MATCH", out.getvalue())

    def test_wrong_approval_scope_does_not_call_docker(self):
        with patch.object(mod, "docker", side_effect=AssertionError("No Docker calls")):
            self.assertEqual(mod.main(["--execute"]), 2)
            self.assertEqual(mod.main([
                "--execute", "--approved-image-id", mod.EXPECTED_IMAGE_ID,
                "--approved-scope", "ANYTHING",
            ]), 2)

    def test_create_copy_cleanup_exact_id_and_postcheck(self):
        fake = FakeDocker()
        code, stdout = self.run_execute(fake)
        self.assertEqual(code, 0)
        self.assertTrue(fake.temp_removed)
        self.assertIn("PLE_TEMP_CREATED_STATE=CREATED_NO_MOUNTS", stdout)
        self.assertIn("PLE_TEMP_SOURCE_SHA256=", stdout)
        self.assertIn("PLE_TEMP_CLEANUP=EXACT_ID_REMOVED_VERIFIED", stdout)
        self.assertIn("PLE_TEMP_PROTECTED_POSTCHECK=MATCH", stdout)
        self.assertIn("PLE_TEMP_LYCHEE888_TP1=NOT_QUALIFIED", stdout)
        self.assertEqual(
            [x for x in fake.calls if x[:2] == ("container", "rm")],
            [("container", "rm", fake.cid)],
        )
        forbidden = {("container", "run"), ("container", "start"),
                     ("container", "exec"), ("container", "kill"),
                     ("container", "rm", mod.EXPECTED_MANAGED_ID),
                     ("container", "rm", mod.EXPECTED_LEGACY_ID)}
        self.assertFalse(any(x[:2] in forbidden or x in forbidden
                             for x in fake.calls))
        self.assertNotIn("docker", stdout.lower().split("source_sha256")[-1])

    def test_transport_failure_still_cleans_up(self):
        fake = FakeDocker()
        fake.control_failure = True
        code, stdout = self.run_execute(fake)
        self.assertEqual(code, 2)
        self.assertTrue(fake.temp_removed)
        self.assertIn("PLE_TEMP_CLEANUP=EXACT_ID_REMOVED_VERIFIED", stdout)
        self.assertIn("STOP_CommandFailed", stdout)
        self.assertFalse(any(x[:1] == ("cp",) and not x[1].endswith(
            ":/etc/group"
        ) for x in fake.calls))

    def test_changed_temp_state_never_removed(self):
        fake = FakeDocker()
        fake.changes_temp_state = True
        code, stdout = self.run_execute(fake)
        self.assertEqual(code, 2)
        self.assertFalse(fake.temp_removed)
        self.assertIn("PLE_TEMP_CLEANUP=STOP_LEFT_FOR_REVIEW", stdout)
        self.assertNotIn(("container", "rm", fake.cid), fake.calls)

    def test_missing_source_is_not_claimed_and_temp_removed(self):
        fake = FakeDocker()
        fake.missing_src = True
        code, stdout = self.run_execute(fake)
        self.assertEqual(code, 2)
        self.assertTrue(fake.temp_removed)
        self.assertNotIn("PLE_TEMP_SOURCE_SHA256=", stdout)
        self.assertIn("PLE_TEMP_PROTECTED_POSTCHECK=MATCH", stdout)

    def test_protected_postcheck_failure_never_reports_success(self):
        fake = FakeDocker()
        fake.change_protected = True
        code, stdout = self.run_execute(fake)
        self.assertEqual(code, 2)
        self.assertTrue(fake.temp_removed)
        self.assertIn("PLE_TEMP_PROTECTED_POSTCHECK=FAIL_REVIEW", stdout)
        self.assertNotIn("PLE_TEMP_PROBE=SOURCE_CAPTURED_STATIC_ONLY", stdout)

    def test_volume_declared_prevents_creation(self):
        fake = FakeDocker()
        fake.image["Config"]["Volumes"] = {"/model": {}}
        code, stdout = self.run_execute(fake)
        self.assertEqual(code, 2)
        self.assertFalse(fake.temp)
        self.assertNotIn(("container", "rm", fake.cid), fake.calls)

    def test_wrong_image_or_protected_ids_stop_before_creation(self):
        for field, value in [
            ("Image", "sha256:" + "1" * 64),
            ("Id", "1" * 64),
        ]:
            fake = FakeDocker()
            if field == "Image":
                fake.legacy[field] = value
            else:
                fake.managed[field] = value
            code, stdout = self.run_execute(fake)
            self.assertEqual(code, 2)
            self.assertFalse(fake.temp)

    def test_disk_reserve_shortage_prevents_creation(self):
        fake = FakeDocker()
        with patch.object(mod, "docker", side_effect=fake), patch.object(
            mod, "available_docker_space", return_value=(1000, 2000)
        ):
            out = io.StringIO()
            with redirect_stdout(out):
                code = mod.main([
                    "--execute", "--approved-image-id", mod.EXPECTED_IMAGE_ID,
                    "--approved-scope", mod.APPROVAL_SCOPE,
                ])
        self.assertEqual(code, 2)
        self.assertFalse(fake.temp)


if __name__ == "__main__":
    unittest.main()
