from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "download-weights.sh"
HELPER = ROOT / "scripts" / "lib" / "hf_snapshot_download.py"


class DownloadWeightsTransportTests(unittest.TestCase):
    def test_container_snapshot_transport_is_present(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("download_missing_with_container()", script)
        self.assertIn("vllm-orcarouter-v029:v1", script)
        self.assertIn("HF_XET_HIGH_PERFORMANCE", script)
        self.assertIn("HF_DOWNLOAD_MAX_WORKERS", script)
        self.assertIn("hf_snapshot_download.py", script)
        self.assertIn("curl fallback", script)

    def test_existing_verified_files_are_excluded_from_missing_set(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("keep %s", script)
        self.assertIn("missing_names_file", script)
        self.assertIn("verified %s", script)

    def test_helper_uses_snapshot_download_allow_patterns(self) -> None:
        helper = HELPER.read_text(encoding="utf-8")
        self.assertIn("snapshot_download(", helper)
        self.assertIn("allow_patterns=patterns", helper)
        self.assertIn("max_workers=workers", helper)
        self.assertIn("local_dir=dest", helper)
        self.assertIn("hf_xet", helper)


if __name__ == "__main__":
    unittest.main()
