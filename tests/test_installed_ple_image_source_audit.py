"""Host-free synthetic tests for existing-container FP8 PLE source audit."""
from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import tarfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "scripts/model/audit_installed_ple_image.py"
spec = importlib.util.spec_from_file_location("existing_ple_image_audit", SOURCE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

IMAGE_ID = "sha256:" + "a" * 64
CONTAINER_ID = "b" * 64


def identities():
    image = {"Id": IMAGE_ID}
    container = {
        "Id": CONTAINER_ID, "Image": IMAGE_ID, "Name": "/qwen38-flash-next",
        "Config": {"Image": "vllm-skinny-tp1:v1"},
        "Mounts": [{"Destination": "/model"}],
    }
    return image, container


def code(selector='''if not isinstance(quant_config, Fp8Config):
    return None
return Qwen3_8FlashNextPLEFp8EmbeddingMethod()'''):
    return (
        "class Qwen3_8FlashNextPLEFp8EmbeddingMethod:\n"
        "    def create_weights(self, layer):\n"
        "        scale_dtype = torch.bfloat16\n"
        "        layer.register_parameter('weight_scale', scale_dtype)\n"
        "    def embedding(self, layer, input_):\n"
        "        return F.embedding(input_, layer.weight)\n"
        "def _get_ple_embedding_quant_method(quant_config, prefix, ple_embedding_dtype=None):\n"
        "    " + selector.replace("\n", "\n    ") + "\n"
        "def _dequantize_embeddings(embeddings, weight_scale):\n"
        "    return embeddings * weight_scale\n"
    )


def tar_source(payload, *, symlink=False, filename="ple_layer.py"):
    data = payload.encode()
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        info = tarfile.TarInfo(filename)
        info.size = len(data)
        if symlink:
            info.type = tarfile.SYMTYPE
            info.linkname = "sneaky"
        tar.addfile(info, None if symlink else io.BytesIO(data))
    return stream.getvalue()


class InstalledImagePLETests(unittest.TestCase):
    def test_readonly_docker_allowlist_rejects_mutations(self):
        for op in (("run", "x"), ("create", "x"), ("start", "x"),
                   ("exec", "x"), ("image", "pull", "x"),
                   ("cp", "unowned:/file", "-")):
            with self.subTest(op=op):
                with self.assertRaisesRegex(mod.AttestationError, "allowlist"):
                    mod.docker_read(*op)

    def test_inspect_image_and_container_identity_exact(self):
        image, container = identities()
        result = mod.validate_identity(image, container)
        self.assertEqual(result["image_id"], IMAGE_ID)
        container["Config"]["Image"] = "some-unowned-image:v1"
        with self.assertRaisesRegex(mod.AttestationError, "differs"):
            mod.validate_identity(image, container)

    def test_identifies_only_mounts_shadowing_exact_ple_path(self):
        img, c = identities()
        unrelated = {"Type": "bind", "Destination":
                     "/usr/local/lib/python3.12/dist-packages/vllm/model_executor",
                     "Source": "/tmp/modelopt-patch"}
        c["Mounts"].append(unrelated)
        mod.validate_identity(img, c)
        self.assertEqual(mod.covering_mounts(c, mod.PATHS[0]), [])
        bound = {"Type": "bind", "Destination": mod.PATHS[0],
                 "Source": "/tmp/test-patched-ple.py", "RW": False}
        c["Mounts"].append(bound)
        self.assertEqual(mod.covering_mounts(c, mod.PATHS[0]), [bound])
        self.assertEqual(mod.host_bind_target(bound, mod.PATHS[0]),
                         "/tmp/test-patched-ple.py")

    def test_rejects_nested_mounts_and_nonbind_override(self):
        _, container = identities()
        container["Mounts"].extend([
            {"Type": "bind", "Destination": "/usr/local/lib/python3.12/dist-packages/vllm",
             "Source": "/tmp/vllm", "RW": False},
            {"Type": "bind", "Destination": mod.PATHS[0],
             "Source": "/tmp/ple.py", "RW": False},
        ])
        with self.assertRaisesRegex(mod.AttestationError, "Overlapping"):
            mod.covering_mounts(container, mod.PATHS[0])
        with self.assertRaisesRegex(mod.AttestationError, "non-bind"):
            mod.host_bind_target(
                {"Type": "volume", "Destination": mod.PATHS[0], "Source": "/tmp/foo"},
                mod.PATHS[0],
            )

    def test_no_container_or_image_source_remains_inconclusive(self):
        with patch.object(mod, "docker_read", side_effect=mod.AttestationError("absent")):
            self.assertEqual(mod.main(), 2)

    def test_bind_mapping_directory_to_specific_ple_path(self):
        mount = {"Type": "bind", "Destination":
                 "/usr/local/lib/python3.12/dist-packages/vllm",
                 "Source": "/tmp/mapped-vllm"}
        expected = "/tmp/mapped-vllm/models/qwen3_8_flash_next/nvidia/ple_layer.py"
        self.assertEqual(mod.host_bind_target(mount, mod.PATHS[0]), expected)

    def test_read_host_source_nofollow_and_bounded_without_docker(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path
            p = Path(tmp) / "ple_layer.py"
            p.write_text(code(), encoding="utf-8")
            self.assertIn("_get_ple_embedding_quant_method",
                          mod.read_host_source_nofollow(str(p)))
            fake = Path(tmp) / "alias.py"
            fake.symlink_to(p)
            with self.assertRaisesRegex(mod.AttestationError, "inaccessible or unsafe"):
                mod.read_host_source_nofollow(str(fake))
            p.write_text("x" * (mod.MAX_SOURCE + 1))
            with self.assertRaisesRegex(mod.AttestationError, "bounded regular"):
                mod.read_host_source_nofollow(str(p))

    def test_exact_mounted_ple_source_is_used_without_docker_cp(self):
        import tempfile
        from pathlib import Path
        image, container = identities()
        commands = []
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "mounted.py"
            source.write_text(code(), encoding="utf-8")
            container["Mounts"].append({
                "Type": "bind", "Destination": mod.PATHS[0],
                "Source": str(source), "RW": False,
            })
            def docker(*args):
                commands.append(args)
                if args[:2] == ("image", "inspect"):
                    return __import__("json").dumps([image]).encode()
                if args[:2] == ("container", "inspect"):
                    return __import__("json").dumps([container]).encode()
                raise AssertionError("Docker copy must not be used for bind-mount content")
            with patch.object(mod, "docker_read", side_effect=docker):
                result = mod.inspect_existing()
        self.assertEqual(len(commands), 2)
        self.assertEqual(result["source_origin"], "HOST_BIND_MOUNT_FILE_NOT_IMAGE_LAYER")
        self.assertEqual(result["source_mount_destination"], mod.PATHS[0])
        self.assertEqual(result["lychee888_tp1_loader"], "NOT_QUALIFIED")

    def test_unreadable_mounted_ple_never_falls_back_to_cp(self):
        image, container = identities()
        container["Mounts"].append({
            "Type": "bind", "Destination": mod.PATHS[0],
            "Source": "/definitely/nonexistent/ple.py", "RW": False,
        })
        calls = []
        def docker(*args):
            calls.append(args)
            return __import__("json").dumps(
                [image if args[:2] == ("image", "inspect") else container]
            ).encode()
        with patch.object(mod, "docker_read", side_effect=docker):
            with self.assertRaisesRegex(mod.AttestationError, "inaccessible or unsafe"):
                mod.inspect_existing()
        self.assertEqual(len(calls), 2)

    def test_tar_read_regular_only(self):
        self.assertIn("_get_ple_embedding_quant_method",
                      mod.source_from_cp(tar_source(code())))
        with self.assertRaisesRegex(mod.AttestationError, "one regular"):
            mod.source_from_cp(tar_source(code(), symlink=True))
        with self.assertRaisesRegex(mod.AttestationError, "unexpected/big"):
            mod.source_from_cp(tar_source(code(), filename="other.py"))

    def test_skinny_reference_probe_only_uses_bounded_copy(self):
        commands = []
        reference = mod.PATHS[0].replace(
            mod.SOURCE_RELATIVE, mod.SKINNY_GEMM_RELATIVE)
        def fake(*args):
            commands.append(args)
            if args == ("cp", f"{mod.MANAGED_CONTAINER}:{reference}", "-"):
                return tar_source("def enable_skinny(): pass\\n", filename="low_latency_gemm.py")
            raise AssertionError("Expected first exact built-in sentinel only")
        with patch.object(mod, "docker_read", side_effect=fake):
            state, path = mod.probe_layout()
        self.assertEqual(state, "SKINNY_GEMM_REFERENCE_READABLE")
        self.assertEqual(path, reference)
        self.assertEqual(len(commands), 1)

    def test_failure_classification_drops_raw_docker_stderr_paths(self):
        cases = (
            (b"Error: could not find the file /private/example", "SOURCE_PATH_NOT_FOUND"),
            (b"stat /home/a: no such file or directory", "SOURCE_PATH_NOT_FOUND"),
            (b"permission denied /home/otheruser", "PERMISSION_DENIED"),
            (b"Cannot connect to the Docker daemon at unix:///var/run/docker.sock",
             "DAEMON_UNAVAILABLE"),
            (b"custom unexpected error path=/etc/x", "COPY_FAILED_UNCLASSIFIED"),
        )
        for stderr, expected in cases:
            with self.subTest(stderr=stderr):
                self.assertEqual(mod.classify_copy_failure(stderr), expected)
        from types import SimpleNamespace
        def badrun(argv, **_):
            return SimpleNamespace(returncode=1, stdout=b"",
                                   stderr=b"permission denied secret:/path")
        with patch.object(mod.subprocess, "run", side_effect=badrun):
            with self.assertRaises(mod.DockerCopyError) as raised:
                mod.docker_read("cp", f"{mod.MANAGED_CONTAINER}:/etc/group", "-")
        self.assertEqual(raised.exception.reason, "PERMISSION_DENIED")
        self.assertNotIn("secret", str(raised.exception))

    def test_generic_small_tar_check_distinguishes_copy_transport(self):
        def good(*args):
            self.assertEqual(args, ("cp", f"{mod.MANAGED_CONTAINER}:/etc/group", "-"))
            return tar_source("root:x:0:\\n", filename="group")
        with patch.object(mod, "docker_read", side_effect=good):
            self.assertEqual(mod.probe_copy_transport(), "SMALL_REGULAR_TAR_READABLE")
        with patch.object(mod, "docker_read",
                          side_effect=mod.DockerCopyError("SOURCE_PATH_NOT_FOUND")):
            self.assertEqual(mod.probe_copy_transport(), "SOURCE_PATH_NOT_FOUND")
        with patch.object(mod, "docker_read", return_value=b"not a tar"):
            self.assertEqual(mod.probe_copy_transport(), "COPY_TAR_INVALID_OR_UNEXPECTED")

    def test_reason_counts_never_include_filesystem_names(self):
        kinds = {}
        for reason in ("SOURCE_PATH_NOT_FOUND", "SOURCE_PATH_NOT_FOUND",
                       "PERMISSION_DENIED"):
            mod._count_failure(kinds, mod.DockerCopyError(reason))
        self.assertEqual(mod.failure_summary(kinds),
                         "PERMISSION_DENIED:1,SOURCE_PATH_NOT_FOUND:2")

    def test_missing_ple_prints_conservative_diagnostic(self):
        image, container = identities()
        calls = []
        def fake(*args):
            calls.append(args)
            if args[:2] == ("image", "inspect"):
                return __import__("json").dumps([image]).encode()
            if args[:2] == ("container", "inspect"):
                return __import__("json").dumps([container]).encode()
            raise mod.AttestationError("Docker metadata or source unavailable")
        with patch.object(mod, "docker_read", side_effect=fake):
            d = {}
            with self.assertRaisesRegex(mod.AttestationError, "No known PLE loader path"):
                mod.inspect_existing(d)
        self.assertEqual(d["image_id"], IMAGE_ID)
        self.assertEqual(d["docker_cp_reference_state"], "SKINNY_GEMM_REFERENCE_UNAVAILABLE")
        self.assertEqual(d["ple_candidates_checked"], str(len(mod.PATHS)))
        self.assertEqual(d["ple_source_file"], "NOT_CAPTURED")
        self.assertEqual(d["docker_cp_small_file_state"], "COPY_FAILED_UNCLASSIFIED")
        self.assertEqual(d["docker_cp_ple_failure_kinds"],
                         "COPY_FAILED_UNCLASSIFIED:12")
        self.assertEqual(d["docker_cp_reference_failure_kinds"],
                         "COPY_FAILED_UNCLASSIFIED:12")
        self.assertTrue(all(args[:1] == ("cp",)
                            for args in calls[2:]))
        self.assertNotIn("run", repr(calls))

    def test_reference_present_does_not_create_false_ple_proof(self):
        image, container = identities()
        def fake(*args):
            if args[:2] == ("image", "inspect"):
                return __import__("json").dumps([image]).encode()
            if args[:2] == ("container", "inspect"):
                return __import__("json").dumps([container]).encode()
            if args[0] == "cp" and args[1].endswith(
                    "/low_latency_gemm.py"):
                return tar_source("def f(): pass\\n", filename="low_latency_gemm.py")
            raise mod.AttestationError("PLE missing")
        with patch.object(mod, "docker_read", side_effect=fake):
            d = {}
            with self.assertRaisesRegex(mod.AttestationError, "No known PLE loader"):
                mod.inspect_existing(d)
        self.assertEqual(d["docker_cp_reference_state"], "SKINNY_GEMM_REFERENCE_READABLE")
        self.assertEqual(d["ple_source_file"], "NOT_CAPTURED")
        self.assertEqual(d["docker_cp_small_file_state"], "COPY_FAILED_UNCLASSIFIED")

    def test_extended_python_versions_are_fixed_bounded_candidates(self):
        self.assertEqual(len(mod.PATHS), 12)
        self.assertIn(
            "/usr/local/lib/python3.14/dist-packages/" + mod.SOURCE_RELATIVE,
            mod.PATHS)
        self.assertIn(
            "/usr/local/lib/python3.15/site-packages/" + mod.SOURCE_RELATIVE,
            mod.PATHS)

    def test_native_fp8_only_does_not_qualify_lychee(self):
        record = mod.audit_source(code())
        self.assertEqual(record["fp8_ple_selection_source"], "NATIVE_FP8_CONFIG_ONLY_SOURCE")
        self.assertEqual(record["bf16_global_scale_registration_source"], "PRESENT")
        self.assertEqual(record["fp8_scale_multiply_source"], "PRESENT")
        self.assertEqual(record["lychee888_tp1_loader"], "NOT_QUALIFIED")

    def test_source_override_and_dtype_dispatch_are_distinct(self):
        override = code(
            '''if os.getenv("PLE_QUANT_OVERRIDE") == "fp8":
    return Qwen3_8FlashNextPLEFp8EmbeddingMethod()
return None''')
        dtype = code(
            '''if ple_embedding_dtype == "float8_e4m3fn":
    return Qwen3_8FlashNextPLEFp8EmbeddingMethod()
return None''')
        self.assertEqual(mod.audit_source(override)["fp8_ple_selection_source"],
                         "EXPLICIT_OVERRIDE_SOURCE_PRESENT")
        self.assertEqual(mod.audit_source(dtype)["fp8_ple_selection_source"],
                         "DTYPE_ROUTING_SOURCE_PRESENT")

    def test_dtype_or_override_string_mention_is_not_dispatch(self):
        source = code(
            '''note = "PLE_QUANT_OVERRIDE and ple_embedding_dtype"
if not isinstance(quant_config, Fp8Config):
    return None
return Qwen3_8FlashNextPLEFp8EmbeddingMethod()''')
        self.assertEqual(mod.audit_source(source)["fp8_ple_selection_source"],
                         "NATIVE_FP8_CONFIG_ONLY_SOURCE")

    def test_unrelated_multiplication_is_not_fp8_scale_consumption(self):
        source = code().replace(
            "return embeddings * weight_scale",
            "note = weight_scale\n    return embeddings * 2",
        )
        self.assertEqual(mod.audit_source(source)["fp8_scale_multiply_source"],
                         "NOT_PROVEN")

    def test_static_signatures_never_prove_scale_if_absent(self):
        record = mod.audit_source(code().replace("torch.bfloat16", "torch.float32")
                                  .replace("embeddings * weight_scale", "embeddings"))
        self.assertEqual(record["bf16_global_scale_registration_source"], "NOT_PROVEN")
        self.assertEqual(record["fp8_scale_multiply_source"], "NOT_PROVEN")

    def test_readonly_introspection_uses_existing_exact_container_only(self):
        image, container = identities()
        commands = []
        def docker(*args):
            commands.append(args)
            if args[:2] == ("image", "inspect"):
                return __import__("json").dumps([image]).encode()
            if args[:2] == ("container", "inspect"):
                return __import__("json").dumps([container]).encode()
            if args[:1] == ("cp",):
                return tar_source(code())
            raise AssertionError(args)
        with patch.object(mod, "docker_read", side_effect=docker):
            result = mod.inspect_existing()
        self.assertEqual(len(commands), 3)
        self.assertEqual(commands[2][0], "cp")
        self.assertEqual(result["image_id"], IMAGE_ID)
        self.assertEqual(result["lychee888_tp1_loader"], "NOT_QUALIFIED")


if __name__ == "__main__":
    unittest.main()
