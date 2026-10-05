from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNNER = ROOT / "scripts" / "benchmark" / "run-orcarouter-managed-rmsys-r10b.sh"


class OrcaRouterRmSysR10bTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = RUNNER.read_text(encoding="utf-8")

    def test_child_runs_with_explicit_clean_environment(self) -> None:
        self.assertIn("/usr/bin/env -i", self.text)
        self.assertIn('PATH="${FIXED_PATH}"', self.text)
        self.assertIn('HOME="${RUN_HOME}"', self.text)
        self.assertIn('SUDO_USER="${RUN_USER}"', self.text)
        self.assertIn('/bin/bash "${CHILD_WRAPPER}"', self.text)

    def test_child_exit_is_separate_from_trace_cmd_exit(self) -> None:
        self.assertIn("managed-command.rc", self.text)
        self.assertIn('MANAGED_RC="$(<"${CHILD_RC_FILE}")"', self.text)
        self.assertIn('printf \'managed_rc=%s\\n\'', self.text)
        self.assertIn('"${MANAGED_RC}" != 0', self.text)

    def test_validity_requires_real_container_replacement(self) -> None:
        self.assertIn("container-id-before.txt", self.text)
        self.assertIn("container-id-after.txt", self.text)
        self.assertIn("restart-observed.txt", self.text)
        self.assertIn('"${POST_CONTAINER_ID}" != "${PRE_CONTAINER_ID}"', self.text)
        self.assertIn('"${RESTART_OBSERVED}" != 1', self.text)
        self.assertIn("run-valid.txt", self.text)

    def test_r10b_preserves_r9_allocator_boundary(self) -> None:
        for token in (
            "nv_alloc_pages_entry",
            "nv_alloc_pages_ret",
            "nv_alloc_system_pages_entry",
            "nv_alloc_system_pages_ret",
            "page_count=$arg2:u32",
            "page_size=$arg3:u64",
            "mm_page_alloc -f 'order == 4'",
            "mm_page_free -f 'order == 4'",
            "mm_page_alloc_extfrag -f 'alloc_order >= 4'",
        ):
            self.assertIn(token, self.text)

    def test_invalid_r10_output_is_not_reused(self) -> None:
        self.assertIn("orcarouter-managed-rmsys-r10b-20261003", self.text)
        self.assertNotIn("ORCA_R10_OUT", self.text)


if __name__ == "__main__":
    unittest.main()
