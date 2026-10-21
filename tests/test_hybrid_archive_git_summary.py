"""Regression rules for read-only Git-safe Hybrid provenance output."""
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / "scripts/model/hybrid-archive-git-summary.py"

class GitSummarySourceTests(unittest.TestCase):
    def test_safe_and_verifiable(self):
        text = SRC.read_text()
        for marker in ("sha256_manifest", "files_verified", "containers_verified",
                       "raw_logs_in_git", "sha256(path) != digest", "len(ids) != 17",
                       "json.loads", "protected"):
            self.assertIn(marker, text)
        for forbidden in ("docker rm", "unlink(", "rmtree(", "subprocess.", "open('w'"):
            self.assertNotIn(forbidden, text)

if __name__ == "__main__":
    unittest.main()
