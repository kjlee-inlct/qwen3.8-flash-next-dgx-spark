from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
CHECKER = ROOT / "scripts" / "model" / "checkpoint_integrity.py"


class CheckpointIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.model = Path(self.tmp.name) / "model"
        self.model.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_index(self, weight_map: dict[str, object]) -> None:
        (self.model / "model.safetensors.index.json").write_text(
            json.dumps({"weight_map": weight_map}),
            encoding="utf-8",
        )

    def run_checker(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(CHECKER), str(self.model)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_accepts_complete_referenced_shards(self) -> None:
        self.write_index({"a": "model-00001-of-00002.safetensors",
                          "b": "model-00002-of-00002.safetensors"})
        (self.model / "model-00001-of-00002.safetensors").write_bytes(b"a")
        (self.model / "model-00002-of-00002.safetensors").write_bytes(b"b")

        result = self.run_checker()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 referenced shard(s)", result.stdout)

    def test_rejects_missing_referenced_shard(self) -> None:
        self.write_index({"a": "model-00001-of-00002.safetensors",
                          "b": "model-00002-of-00002.safetensors"})
        (self.model / "model-00001-of-00002.safetensors").write_bytes(b"a")

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("model-00002-of-00002.safetensors", result.stderr)

    def test_rejects_dangling_symlink(self) -> None:
        self.write_index({"a": "model-00001-of-00001.safetensors"})
        os.symlink(self.model / "missing-blob", self.model / "model-00001-of-00001.safetensors")

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing, dangling, or empty", result.stderr)

    def test_accepts_valid_symlinked_huggingface_style_shard(self) -> None:
        blobs = Path(self.tmp.name) / "blobs"
        blobs.mkdir()
        blob = blobs / "abc"
        blob.write_bytes(b"payload")
        self.write_index({"a": "model-00001-of-00001.safetensors"})
        os.symlink(blob, self.model / "model-00001-of-00001.safetensors")

        result = self.run_checker()

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_empty_shard(self) -> None:
        self.write_index({"a": "model-00001-of-00001.safetensors"})
        (self.model / "model-00001-of-00001.safetensors").touch()

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing, dangling, or empty", result.stderr)

    def test_rejects_invalid_or_traversing_shard_path(self) -> None:
        self.write_index({"a": "../outside.safetensors"})

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid shard path", result.stderr)

    def test_doctor_invokes_checkpoint_integrity_checker(self) -> None:
        doctor = (ROOT / "scripts" / "doctor.sh").read_text(encoding="utf-8")
        self.assertIn('model/checkpoint_integrity.py', doctor)
        self.assertIn('python3 "${CHECKPOINT_INTEGRITY}" "${MODEL_DIR}"', doctor)

    def test_rejects_malformed_index(self) -> None:
        (self.model / "model.safetensors.index.json").write_text("{", encoding="utf-8")

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read safetensors index", result.stderr)


if __name__ == "__main__":
    unittest.main()
