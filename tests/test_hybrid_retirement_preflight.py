"""Read-only Hybrid retirement orchestration contract."""
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/model/hybrid-retirement-preflight.sh"

class HybridRetirementPreflightTests(unittest.TestCase):
    def test_all_stages_exact_archive_and_identity_checks(self):
        s = SOURCE.read_text()
        for marker in ("verify-hybrid-retirement-evidence.py",
                       "hybrid-container-evidence.py",
                       "hybrid-retirement-audit.sh",
                       "qwen3.8-hybrid-quant-layout",
                       "qwen3.8-h4-orca-all",
                       "qwen3.8-h5-neutral-input-scale",
                       "qwen3.8-h6-modelopt-w4a16",
                       "HYBRID_RETIREMENT_DELETE=NOT_AUTHORIZED",
                       "OFF_HOST_BACKUP=NOT_VERIFIED"):
            self.assertIn(marker, s)
        for forbidden in ("docker rm", "docker stop", "docker start", "rm -rf", "shutil.rmtree"):
            self.assertNotIn(forbidden, s)

if __name__ == "__main__":
    unittest.main()
