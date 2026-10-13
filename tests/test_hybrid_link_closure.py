"""S4 all-link resolver synthetic fixtures; host and Docker are never touched."""
from __future__ import annotations
from pathlib import Path
import runpy
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MOD = runpy.run_path(str(ROOT / "scripts/diagnostics/inspect-hybrid-link-closure.py"))

class S4AllLinkClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dirs = {}
        for stage in ("base", "mazinb", "h3", "h4", "h5", "h6"):
            root = Path(tmp.name) / stage
            root.mkdir()
            self.dirs[stage] = root
        (self.dirs["base"] / "tokenizer.json").write_text("{}", encoding="utf-8")
        (self.dirs["h3"] / "tokenizer.json").symlink_to("/base-model/tokenizer.json")
        (self.dirs["h4"] / "tokenizer.json").symlink_to("/h3-model/tokenizer.json")
        (self.dirs["h5"] / "tokenizer.json").symlink_to("/h4-all/tokenizer.json")
        (self.dirs["h6"] / "tokenizer.json").symlink_to("/h5-parent/tokenizer.json")

    def test_nonindex_alias_chain(self) -> None:
        self.assertEqual(MOD["resolve_link"]("h6", "tokenizer.json", self.dirs), "REGULAR_FILE")
        self.assertEqual(MOD["count_links"]("h6", self.dirs["h6"], self.dirs)["REGULAR_FILE"], 1)

    def test_missing_target_fails(self) -> None:
        (self.dirs["base"] / "tokenizer.json").unlink()
        self.assertEqual(MOD["resolve_link"]("h6", "tokenizer.json", self.dirs), "MISSING")

    def test_unrecognized_absolute_path_fails_closed(self) -> None:
        link = self.dirs["h6"] / "tokenizer.json"
        link.unlink()
        link.symlink_to("/etc/passwd")
        self.assertEqual(MOD["resolve_link"]("h6", "tokenizer.json", self.dirs), "UNRECOGNIZED_ALIAS")

    def test_directory_target(self) -> None:
        (self.dirs["base"] / "subdir").mkdir()
        (self.dirs["h3"] / "subdir").symlink_to("/base-model/subdir", target_is_directory=True)
        self.assertEqual(MOD["resolve_link"]("h3", "subdir", self.dirs), "DIRECTORY")

    def test_builder_and_serving_mount_source_in_sync(self) -> None:
        MOD["check_source_contract"](ROOT)

    def test_source_never_runs_models_or_deletes_assets(self) -> None:
        text = (ROOT / "scripts/diagnostics/inspect-hybrid-link-closure.py").read_text()
        for forbidden in ("docker run", "docker start", "docker rm", "systemctl start",
                          "swapoff", "git reset", "rmtree(", "os.remove("):
            self.assertNotIn(forbidden, text)

if __name__ == "__main__":
    unittest.main()
