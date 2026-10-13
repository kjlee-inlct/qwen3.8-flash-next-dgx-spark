"""Synthetic S3 virtual-Docker-mount reference resolution tests; no model payloads."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/diagnostics/inspect-hybrid-runtime-references.py"
spec = importlib.util.spec_from_file_location("hybrid_runtime_refs", SCRIPT)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class HybridRuntimeReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.dirs = {}
        for stage in audit.TREE_NAMES:
            path = root / stage
            path.mkdir()
            self.dirs[stage] = path
        (self.dirs["base"] / "part-00001.safetensors").write_bytes(b"toy")
        (self.dirs["h3"] / "part-00001.safetensors").symlink_to("/base-model/part-00001.safetensors")
        (self.dirs["h4"] / "part-00001.safetensors").symlink_to("/h3-model/part-00001.safetensors")
        (self.dirs["h5"] / "part-00001.safetensors").symlink_to("/h4-all/part-00001.safetensors")
        (self.dirs["h6"] / "part-00001.safetensors").symlink_to("/h5-parent/part-00001.safetensors")

    def test_virtual_mount_symlink_chain_is_not_host_dangling_failure(self):
        self.assertEqual(audit.resolve_shard("h6", "part-00001.safetensors", self.dirs), "VIRTUAL_CHAIN")
        self.assertEqual(audit.resolve_shard("base", "part-00001.safetensors", self.dirs), "DIRECT")

    def test_actual_missing_target_detected(self):
        (self.dirs["base"] / "part-00001.safetensors").unlink()
        self.assertEqual(audit.resolve_shard("h6", "part-00001.safetensors", self.dirs), "MISSING")

    def test_unapproved_absolute_link_is_not_followed(self):
        link = self.dirs["h6"] / "part-00001.safetensors"
        link.unlink()
        link.symlink_to("/etc/passwd")
        self.assertEqual(audit.resolve_shard("h6", "part-00001.safetensors", self.dirs), "UNKNOWN_ALIAS")

    def test_rejects_traversal_and_index_escape(self):
        self.assertIsNone(audit.map_virtual_target("h6", "/h5-parent/../private"))
        self.assertEqual(audit.resolve_shard("h6", "../part-00001.safetensors", self.dirs), "INVALID_NAME")

    def test_unmapped_links_reported_for_review(self):
        aliases, count = audit.link_summary("h6", self.dirs["h6"])
        self.assertEqual(count, 1)
        self.assertEqual(aliases["h5"], 1)

    def test_non_mutating_contract(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for prohibited in ("docker run", "docker start", "docker rm", "systemctl start",
                           "unlink(", "rmtree(", "os.remove(", "swapoff", "git reset"):
            self.assertNotIn(prohibited, source)


if __name__ == "__main__":
    unittest.main()
