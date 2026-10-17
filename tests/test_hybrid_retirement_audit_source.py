"""Source-level regression for read-only Hybrid retirement inventory."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/model/hybrid-retirement-audit.sh"


class HybridRetirementAuditSourceTests(unittest.TestCase):
    def test_scans_all_containers_and_profiles_without_mutation(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for token in ("docker ps -aq", "docker inspect", "model_asset_profiles",
                      "PROFILE_ALIAS=", "DOCKER_REFERENCE=", "READ_ONLY_NOT_DELETE_AUTHORIZATION",
                      "BLOCKED_DOCKER_INSPECT_FAILED"):
            self.assertIn(token, source)
        for unsafe in ("docker rm ", "docker rmi ", "rm -rf ", "docker stop ", "docker start "):
            self.assertNotIn(unsafe, source)


if __name__ == "__main__":
    unittest.main()
