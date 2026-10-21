"""Host-free regression for immutable Hybrid evidence verification."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/model/verify-hybrid-retirement-evidence.py"
spec = importlib.util.spec_from_file_location("hybrid_evidence_verifier", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class HybridEvidenceVerifyTests(unittest.TestCase):
    def test_expected_file_set_and_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in ("a.json", "b.log"):
                (root / name).write_bytes(name.encode())
            (root / "SHA256SUMS.txt").write_text("".join(
                hashlib.sha256(name.encode()).hexdigest() + "  " + name + "\n"
                for name in ("a.json", "b.log")
            ))
            self.assertEqual(mod.verify(root, "SHA256SUMS.txt", ("a.json", "b.log")), (True, "PASS"))
            (root / "b.log").write_text("modified")
            self.assertEqual(mod.verify(root, "SHA256SUMS.txt", ("a.json", "b.log"))[1], "CHECKSUM_MISMATCH")

    def test_rejects_extra_and_missing_and_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a").write_text("a")
            (root / "SHA256SUMS.txt").write_text(hashlib.sha256(b"a").hexdigest() + "  a\n")
            self.assertEqual(mod.verify(root, "SHA256SUMS.txt", ("a", "b"))[1], "INCOMPLETE_FILE_SET")
            (root / "b").symlink_to(root / "a")
            self.assertEqual(mod.verify(root, "SHA256SUMS.txt", ("a",))[0], True)
            (root / "a").unlink()
            (root / "a").symlink_to(root / "b")
            self.assertEqual(mod.verify(root, "SHA256SUMS.txt", ("a",))[1], "MISSING_OR_SYMLINK_FILE")

    def test_no_mutation_or_deletion_authorization(self):
        source = SOURCE.read_text()
        self.assertIn("OFF_HOST_BACKUP=NOT_VERIFIED", source)
        self.assertIn("HYBRID_DELETE_AUTHORIZATION=NO", source)
        for token in ("unlink(", "rmtree(", "docker rm", "docker start", "docker stop"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
