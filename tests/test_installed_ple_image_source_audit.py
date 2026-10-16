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

    def test_refuses_overridden_source_mount(self):
        img, c = identities()
        c["Mounts"].append({"Destination": "/usr/local/lib/python3.12/dist-packages/vllm"})
        with self.assertRaisesRegex(mod.AttestationError, "Mounted vLLM source"):
            mod.validate_identity(img, c)

    def test_no_container_or_image_source_remains_inconclusive(self):
        with patch.object(mod, "docker_read", side_effect=mod.AttestationError("absent")):
            self.assertEqual(mod.main(), 2)

    def test_tar_read_regular_only(self):
        self.assertIn("_get_ple_embedding_quant_method",
                      mod.source_from_cp(tar_source(code())))
        with self.assertRaisesRegex(mod.AttestationError, "one regular"):
            mod.source_from_cp(tar_source(code(), symlink=True))
        with self.assertRaisesRegex(mod.AttestationError, "unexpected/big"):
            mod.source_from_cp(tar_source(code(), filename="other.py"))

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
