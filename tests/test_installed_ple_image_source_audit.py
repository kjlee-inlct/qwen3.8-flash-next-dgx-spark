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
    def test_isolated_source_preview_three_inspects_zero_copies(self):
        import json
        image, managed = identities()
        image["Size"] = 20629141958
        image["Config"] = {"Volumes": None}
        managed["HostConfig"] = {"ReadonlyRootfs": False}
        managed["State"] = {"Status": "exited"}
        managed["Mounts"] = [
            {"Destination": "/model", "Type": "bind", "RW": False,
             "Source": "/home/private/checkpoint"},
            {"Destination": "/model/config.json", "Type": "bind", "RW": False,
             "Source": "/home/private/config"},
        ]
        legacy = {
            "Id": "c" * 64, "Image": IMAGE_ID, "Name": "/qwen38-ab-legacy",
            "Config": {"Image": mod.IMAGE_TAG}, "State": {"Status": "exited"},
            "Mounts": list(managed["Mounts"]),
        }
        calls = []
        def read(*args):
            calls.append(args)
            if args == ("image", "inspect", mod.IMAGE_TAG):
                return json.dumps([image]).encode()
            if args == ("container", "inspect", mod.MANAGED_CONTAINER):
                return json.dumps([managed]).encode()
            if args == ("container", "inspect", mod.LEGACY_CONTAINER):
                return json.dumps([legacy]).encode()
            raise AssertionError("Unexpected Docker action")
        with patch.object(mod, "docker_read", side_effect=read):
            plan = mod.isolated_copy_preflight_plan()
        self.assertEqual(len(calls), 3)
        self.assertFalse(any("cp" in args or "create" in args for args in calls))
        self.assertEqual(plan["image_id"], IMAGE_ID)
        self.assertEqual(plan["image_size_bytes"], "20629141958")
        self.assertEqual(plan["managed_mount_topology"],
                         "MODEL_CONFIG_NESTED_RO_BINDS")
        self.assertEqual(plan["legacy_mount_topology"],
                         "MODEL_CONFIG_NESTED_RO_BINDS")
        self.assertEqual(plan["isolated_create_only_feasibility"],
                         "REVIEW_CANDIDATE_NOT_AUTHORIZED")
        self.assertEqual(plan["existing_container_copy_route"],
                         "BLOCKED_SAME_NESTED_RO_MOUNTS")
        self.assertEqual(plan["docker_cp_requests"], "0")
        self.assertEqual(plan["source_bytes_captured"], "NO")
        self.assertNotIn("/home/private", repr(plan))
        self.assertNotIn("Source", repr(plan))
        self.assertEqual(plan["lychee888_tp1_loader"], "NOT_QUALIFIED")

    def test_isolated_source_preview_image_volume_blocks_review(self):
        import json
        image, managed = identities()
        image["Size"] = 123456
        image["Config"] = {"Volumes": {"/data": {}}}
        managed["State"] = {"Status": "exited"}
        managed["Mounts"] = [
            {"Destination": "/model", "Type": "bind", "RW": False},
            {"Destination": "/model/config.json", "Type": "bind", "RW": False},
        ]
        legacy = {
            "Id": "c" * 64, "Image": IMAGE_ID, "Name": "/qwen38-ab-legacy",
            "Config": {"Image": mod.IMAGE_TAG}, "State": {"Status": "exited"},
            "Mounts": list(managed["Mounts"]),
        }
        def read(*args):
            return json.dumps([
                image if args[0] == "image" else
                managed if args[-1] == mod.MANAGED_CONTAINER else legacy
            ]).encode()
        with patch.object(mod, "docker_read", side_effect=read):
            plan = mod.isolated_copy_preflight_plan()
        self.assertEqual(plan["declared_image_volumes"], "PRESENT_BLOCK_REVIEW")
        self.assertEqual(plan["isolated_create_only_feasibility"], "STOP_UNQUALIFIED")

        legacy["Image"] = "sha256:" + "f" * 64
        with patch.object(mod, "docker_read", side_effect=read):
            with self.assertRaisesRegex(mod.AttestationError, "identity mismatch"):
                mod.isolated_copy_preflight_plan()

    def test_isolated_source_preview_unknown_state_fails_closed(self):
        import json
        image, managed = identities()
        image.update({"Size": 12345, "Config": {"Volumes": None}})
        managed["State"] = {"Status": "running"}
        legacy = {
            "Id": "c" * 64, "Image": IMAGE_ID, "Name": "/qwen38-ab-legacy",
            "Config": {"Image": mod.IMAGE_TAG}, "State": {"Status": "exited"},
            "Mounts": [{"Destination": "/model"}],
        }
        def read(*args):
            return json.dumps([
                image if args[0] == "image" else
                managed if args[-1] == mod.MANAGED_CONTAINER else legacy
            ]).encode()
        with patch.object(mod, "docker_read", side_effect=read):
            with self.assertRaisesRegex(mod.AttestationError, "not both stopped"):
                mod.isolated_copy_preflight_plan()

    def test_model_config_nested_mount_topology_never_exposes_host_paths(self):
        _image, container = identities()
        self.assertEqual(mod.model_config_mount_topology(container),
                         "NO_MODEL_CONFIG_NESTED_MOUNT")
        container["Mounts"][0] = {
            "Type": "bind", "Destination": "/model",
            "Source": "/private/important-checkpoint", "RW": False,
        }
        container["Mounts"].append({
            "Type": "bind", "Destination": "/model/config.json",
            "Source": "/private/secret-config", "RW": False,
        })
        self.assertEqual(mod.model_config_mount_topology(container),
                         "MODEL_CONFIG_NESTED_RO_BINDS")
        self.assertNotIn("/private/", mod.model_config_mount_topology(container))
        container["Mounts"][1]["RW"] = True
        self.assertEqual(mod.model_config_mount_topology(container),
                         "MODEL_CONFIG_NESTED_BINDS_RW_OTHER")
        container["Mounts"][1]["Type"] = "volume"
        self.assertEqual(mod.model_config_mount_topology(container),
                         "MODEL_CONFIG_NESTED_NONBIND")
        container["Mounts"].append(dict(container["Mounts"][1]))
        self.assertEqual(mod.model_config_mount_topology(container),
                         "AMBIGUOUS_MODEL_CONFIG_NESTING")

    def test_openat_model_config_readonly_categorized_without_leaking_path(self):
        raw = b"Error response from daemon: openat model/config.json: read-only file system"
        self.assertEqual(mod.classify_copy_failure(raw),
                         "FILESYSTEM_READ_ONLY")
        self.assertEqual(mod.docker_stderr_signals(raw),
                         "DOCKER_DAEMON_REPLY,FILESYSTEM")

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

    def test_unknown_copy_error_exposes_only_safe_signals_and_code(self):
        from types import SimpleNamespace
        msg = (b"Error response from daemon: archive extraction failed "
               b"at /home/private/session/foo with unrecognized fatal error")
        def fake_run(*_args, **_kwargs):
            return SimpleNamespace(returncode=37, stdout=b"", stderr=msg)
        with patch.object(mod.subprocess, "run", side_effect=fake_run):
            with self.assertRaises(mod.DockerCopyError) as raised:
                mod.docker_read("cp", f"{mod.MANAGED_CONTAINER}:/etc/group", "-")
        err = raised.exception
        self.assertEqual(err.reason, "COPY_FAILED_UNCLASSIFIED")
        self.assertEqual(err.exit_code, 37)
        self.assertEqual(err.stderr_bytes, len(msg))
        self.assertIn("DOCKER_DAEMON_REPLY", err.stderr_signals)
        self.assertIn("ARCHIVE", err.stderr_signals)
        self.assertNotIn("/home/private", repr(err))
        diagnostics = {}
        with patch.object(mod, "docker_read", side_effect=err):
            state = mod.probe_copy_transport(diagnostics)
        self.assertEqual(state, "COPY_FAILED_UNCLASSIFIED")
        self.assertEqual(diagnostics["docker_cp_small_file_exit_code"], "37")
        self.assertEqual(diagnostics["docker_cp_small_file_stderr_bytes"],
                         str(len(msg)))
        self.assertIn("ARCHIVE", diagnostics["docker_cp_small_file_stderr_signals"])
        self.assertNotIn("private", repr(diagnostics))

    def test_common_docker_copy_error_categories(self):
        cases = (
            (b"Error: no such container abc", "CONTAINER_MISSING_DURING_COPY"),
            (b"Error: container is paused", "CONTAINER_PAUSED"),
            (b"Error: container is not running", "CONTAINER_NOT_RUNNING"),
            (b"archive: unexpected EOF", "TAR_STREAM_ERROR"),
            (b"invalid argument for copy", "CLI_ARGUMENT_REJECTED"),
            (b"operation not permitted on filesystem", "OPERATION_NOT_PERMITTED"),
        )
        for raw, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(mod.classify_copy_failure(raw), reason)

    def test_managed_container_state_only_known_values(self):
        image, container = identities()
        container["State"] = {"Status": "exited", "Error": "sensitive-message"}
        def docker(*args):
            import json
            if args[:2] == ("image", "inspect"):
                return json.dumps([image]).encode()
            if args[:2] == ("container", "inspect"):
                return json.dumps([container]).encode()
            raise mod.DockerCopyError("COPY_FAILED_UNCLASSIFIED")
        d = {}
        with patch.object(mod, "docker_read", side_effect=docker):
            with self.assertRaises(mod.AttestationError):
                mod.inspect_existing(d)
        self.assertEqual(d["container_state"], "exited")
        self.assertNotIn("sensitive-message", repr(d))
        container["State"]["Status"] = "secret-host-status"
        d2 = {}
        with patch.object(mod, "docker_read", side_effect=docker):
            with self.assertRaises(mod.AttestationError):
                mod.inspect_existing(d2)
        self.assertEqual(d2["container_state"], "UNKNOWN")

    def test_readonly_copy_preflight_stops_before_all_model_copy_attempts(self):
        import json
        image, container = identities()
        container["State"] = {"Status": "exited"}
        container["HostConfig"] = {"ReadonlyRootfs": True}
        calls = []
        def fake(*args):
            calls.append(args)
            if args[:2] == ("image", "inspect"):
                return json.dumps([image]).encode()
            if args[:2] == ("container", "inspect"):
                return json.dumps([container]).encode()
            if args == ("cp", f"{mod.MANAGED_CONTAINER}:/etc/group", "-"):
                raise mod.DockerCopyError(
                    "FILESYSTEM_READ_ONLY", exit_code=1, stderr_bytes=76,
                    stderr_signals="DOCKER_DAEMON_REPLY,FILESYSTEM")
            raise AssertionError("No PLE/GEMM copies after blocked cp transport")
        with patch.object(mod, "docker_read", side_effect=fake):
            d = {}
            with self.assertRaisesRegex(mod.AttestationError,
                                        "read-only; source files NOT TESTED"):
                mod.inspect_existing(d)
        self.assertEqual(len(calls), 3)
        self.assertEqual(d["container_readonly_rootfs"], "TRUE")
        self.assertEqual(d["container_state"], "exited")
        self.assertEqual(d["docker_cp_small_file_state"], "FILESYSTEM_READ_ONLY")
        self.assertEqual(d["docker_cp_small_file_exit_code"], "1")
        self.assertEqual(d["ple_candidates_checked"], "0")
        self.assertEqual(d["docker_cp_ple_failure_kinds"], "NOT_ATTEMPTED_PRECHECK_BLOCK")
        self.assertEqual(d["docker_cp_reference_state"], "NOT_ATTEMPTED_PRECHECK_BLOCK")

    def test_readonly_rootfs_flag_alone_does_not_block_successful_source_reads(self):
        import json
        image, container = identities()
        container["HostConfig"] = {"ReadonlyRootfs": True}
        calls = []
        def fake(*args):
            calls.append(args)
            if args[:2] == ("image", "inspect"):
                return json.dumps([image]).encode()
            if args[:2] == ("container", "inspect"):
                return json.dumps([container]).encode()
            if args == ("cp", f"{mod.MANAGED_CONTAINER}:/etc/group", "-"):
                return tar_source("root:x:0:\\n", filename="group")
            if args == ("cp", f"{mod.MANAGED_CONTAINER}:{mod.PATHS[0]}", "-"):
                return tar_source(code())
            raise AssertionError(args)
        with patch.object(mod, "docker_read", side_effect=fake):
            d = {}
            result = mod.inspect_existing(d)
        self.assertEqual(d["container_readonly_rootfs"], "TRUE")
        self.assertEqual(d["docker_cp_small_file_state"], "SMALL_REGULAR_TAR_READABLE")
        self.assertEqual(result["source_audit"], "STATIC_ONLY_NOT_EXECUTION")
        self.assertEqual(len(calls), 4)
        self.assertEqual(result["lychee888_tp1_loader"], "NOT_QUALIFIED")

    def test_rootfs_error_is_distinct_from_host_filesystem_read_only(self):
        self.assertEqual(
            mod.classify_copy_failure(
                b"Error response from daemon: container rootfs is marked read-only"),
            "CONTAINER_ROOTFS_READ_ONLY",
        )
        self.assertEqual(
            mod.classify_copy_failure(b"overlay: read-only file system"),
            "FILESYSTEM_READ_ONLY",
        )

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
