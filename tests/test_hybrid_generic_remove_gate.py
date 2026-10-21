"""Ensure the generic checkpoint removal path cannot erase Hybrid research stages.

Host-free source regression: does not launch Docker or remove files.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "scripts/manage-models.sh"


class HybridGenericRemoveGateTests(unittest.TestCase):
    def test_hybrid_guard_precedes_dry_run_and_actual_delete(self):
        source = MANAGER.read_text(encoding="utf-8")
        body = source.split("\nremove_model() {", 1)[1].split("\ncase \"${ACTION}\" in", 1)[0]
        self.assertIn('if [[ "${kind}" == hybrid ]]; then', body)
        self.assertIn("BLOCKED_HYBRID_DEPENDENCY_CLOSURE", body)
        self.assertLess(body.index('if [[ "${kind}" == hybrid ]]; then'),
                        body.index('if [[ "${DRY_RUN}" == 1 ]]'))
        self.assertLess(body.index('if [[ "${kind}" == hybrid ]]; then'),
                        body.index('rm -rf --one-file-system -- "${path}"'))


if __name__ == "__main__":
    unittest.main()
