from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
QUALIFIER = ROOT / "scripts" / "lifecycle" / "qualify-release.sh"


class QualifyReleaseEnvironmentTests(unittest.TestCase):
    def test_unit_tests_do_not_inherit_outer_operation_lock_context(self) -> None:
        script = QUALIFIER.read_text(encoding="utf-8")
        for name in (
            "QWEN38_OPERATION_LOCK_HELD",
            "QWEN38_OPERATION_LOCK_FILE",
            "QWEN38_OPERATION_LOCK_OWNER_PID",
        ):
            self.assertIn(f"-u {name}", script)


if __name__ == "__main__":
    unittest.main()
