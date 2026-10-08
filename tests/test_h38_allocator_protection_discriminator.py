from __future__ import annotations

import csv
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
RUNNER = ROOT / "scripts/benchmark/run-h38-allocator-protection-discriminator.sh"
ANALYZER = ROOT / "scripts/benchmark/analyze-h38-allocator-protection-trajectory.py"


def fixture(root: Path, rm: bool = False) -> None:
    state = root / "allocator-state"
    (state / "events").mkdir(parents=True)
    fast, slow = [], []
    for i in range(4):
        wall = f"2026-10-08T00:00:{i:02d}+00:00"
        header = f"===== sample seq={i+1} wall={wall} monotonic_ns={1000000000+i*1000000000} ====="
        fast.extend([
            header, "--- /proc/buddyinfo ---",
            f"Node 0, zone Normal 0 0 0 0 {10-i} 2",
            "--- /proc/meminfo ---", "MemAvailable: 40960000 kB",
            "MemFree: 2048000 kB", "SwapFree: 139264000 kB",
            "--- /proc/pressure/memory ---",
            "some avg10=0.20 avg60=0.10 avg300=0.05 total=1234",
            "full avg10=0.01 avg60=0.00 avg300=0.00 total=10",
        ])
        slow.extend([
            header, "--- /proc/pagetypeinfo ---",
            f"Node 0, zone Normal, type Unmovable 0 0 0 0 {6-i} 2",
            "Node 0, zone Normal, type Movable 0 0 0 0 10 2",
        ])
    (state / "fast-state.txt").write_text("\n".join(fast) + "\n")
    (state / "slow-state.txt").write_text("\n".join(slow) + "\n")
    (root / "memory-monitor.log").write_text(
        "2026-10-08 09:00:03 PROTECT stopping qwen38-h38-allocator-protection gracefully\n"
    )
    if rm:
        event = state / "events" / "rm-oom-01-1234"
        event.mkdir()
        (event / "meta.txt").write_text(
            "wall=2026-10-08T00:00:02+00:00\nmonotonic_ns=3000000000\n"
        )


class H38AllocatorRunnerTests(unittest.TestCase):
    def test_runner_executable_and_valid_shell(self) -> None:
        self.assertTrue(RUNNER.stat().st_mode & stat.S_IXUSR)
        result = subprocess.run(["bash", "-n", str(RUNNER)], cwd=ROOT,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_runner_preserves_identity_protection_and_safety(self) -> None:
        content = RUNNER.read_text()
        for item in (
            "H38_ALLOCATOR_DISCRIMINATOR_TARGET_SHA",
            "status --porcelain=v1 --untracked-files=all",
            "assert_idle", "assert_post_protection_baseline",
            "SPEC=mtp", "NSPEC=2", "KV_MEM=",
            "EXECUTOR=mp", "BATCHED_TOKENS=8192", "QSA_DET_TOPK=0",
            '"VLLM_QSA_DET_TOPK=0"', '"--distributed-executor-backend"',
            'spec != {"method": "mtp", "num_speculative_tokens": 2}',
            "VLLM_PLE_MMAP=1", "VLLM_QSA_EXACT_TOPK=1",
            "QWEN38_MARLIN_CANONICAL_ORDER=1",
            "QWEN38_MARLIN_CANONICAL_SCOPE=decoder",
            "VLLM_PLE_CPU_OFFLOAD=1", "IDENTITY_VALIDATED=1",
            "--min-available-gib 6", "--min-free-gib 2",
            "--free-gate-gib 10", "--min-swap-free-gib 8",
            "--swap-activity-gate-mib 256", "--consecutive 5",
            "--interval 2", "--protect", "collect-linux-allocator-state.py",
            "--fast-interval 1 --slow-interval 5",
            "collector_healthy=", "analysis_rc=", "run_completed=",
            "HOST_STABILITY=", 'RESULT="INVALID"',
            "NV_ERR_NO_MEMORY|_memdescAllocInternal",
            "Managed predecessor remains in its original stopped post-protection state.",
            "RUN_COMPLETED=1", "finish_collector", "if ! python3 -",
            "run-h38-allocator-protection-discriminator.sh",
            "COLLECTOR_HEALTHY", "ANALYSIS_RC", "KERNEL_WINDOW_RC",
        ):
            self.assertIn(item, content, item)
        for item in (
            "SPEC=none", "update-release.sh", "install.sh",
            "systemctl start ", "systemctl stop ",
            "drop_caches", "compact_memory", "sysctl -w", "<<'PY' ||",
        ):
            self.assertNotIn(item, content, item)


class H38AllocatorAnalyzerTests(unittest.TestCase):
    def run_analysis(self, evidence: Path, reference: Path | None = None):
        csv_path = evidence / "out.csv"
        report_path = evidence / "out.txt"
        args = ["python3", str(ANALYZER), "--evidence", str(evidence),
                "--csv", str(csv_path), "--report", str(report_path)]
        if reference:
            args.extend(["--reference", str(reference)])
        return subprocess.run(args, text=True, capture_output=True, check=False), csv_path, report_path

    def test_protected_stop_with_rm_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, reference = Path(temp) / "h38", Path(temp) / "r22"
            fixture(evidence)
            fixture(reference, rm=True)
            rc, csv_path, report_path = self.run_analysis(evidence, reference)
            self.assertEqual(rc.returncode, 0, rc.stderr)
            report = report_path.read_text()
            for item in (
                "event_type=PROTECTED_STOP", "reference_type=RM_EVENT",
                "h38_fast=T+0 coverage=OBSERVED",
                "h38_slow=T-60 coverage=MISSING",
                "RESERVOIR_CLASSIFICATION=UNDETERMINED",
                "COMPARISON_VERDICT=UNDETERMINED",
            ):
                self.assertIn(item, report)
            with csv_path.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 16)
            self.assertEqual(rows[0]["normal_o4plus_mib"], "0.875")
            self.assertEqual(rows[0]["psi_some_avg10"], "0.2")

    def test_rm_has_event_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp)
            fixture(evidence, rm=True)
            rc, _, report = self.run_analysis(evidence)
            self.assertEqual(rc.returncode, 0, rc.stderr)
            self.assertIn("event_type=RM_EVENT", report.read_text())

    def test_event_boundary_never_uses_rollback_recovered_samples(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root, rm=True)
            event = root / "allocator-state" / "events" / "rm-oom-01-1234" / "meta.txt"
            event.write_text(
                "wall=2026-10-08T00:00:02.800000+00:00\nmonotonic_ns=3800000000\n"
            )
            fast = root / "allocator-state" / "fast-state.txt"
            fast.write_text(
                fast.read_text().replace(
                    "Node 0, zone Normal 0 0 0 0 7 2",
                    "Node 0, zone Normal 0 0 0 0 7777 2",
                )
            )
            rc, _, path = self.run_analysis(root)
            self.assertEqual(rc.returncode, 0, rc.stderr)
            report = path.read_text()
            self.assertIn("ALIGNMENT=AT_OR_BEFORE_TARGET_ONLY", report)
            self.assertIn(
                "h38_fast=T+0 coverage=OBSERVED actual_offset_s=-0.800 "
                "normal_o4_mib=0.500 normal_o4plus_mib=0.750",
                report,
            )
            self.assertIn("h38_fast=T-60 coverage=MISSING", report)

    def test_incomplete_pagetype_is_not_falsely_zero_reservoir(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root)
            slow = root / "allocator-state" / "slow-state.txt"
            slow.write_text(
                slow.read_text().replace(
                    "Node 0, zone Normal, type Unmovable 0 0 0 0 6 2",
                    "Node 0, zone Normal, type Unmovable UNAVAILABLE",
                )
            )
            rc, _, _ = self.run_analysis(root)
            self.assertNotEqual(rc.returncode, 0)
            self.assertIn("pagetype has no order-4 column", rc.stderr)

    def test_missing_psi_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root)
            fast = root / "allocator-state" / "fast-state.txt"
            fast.write_text(
                fast.read_text().replace(
                    "some avg10=0.20 avg60=0.10 avg300=0.05 total=1234",
                    "some unavailable"
                )
            )
            rc, _, _ = self.run_analysis(root)
            self.assertNotEqual(rc.returncode, 0)
            self.assertIn("required meminfo or PSI", rc.stderr)

    def test_missing_slow_samples_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp)
            fixture(evidence)
            (evidence / "allocator-state" / "slow-state.txt").unlink()
            rc, _, _ = self.run_analysis(evidence)
            self.assertNotEqual(rc.returncode, 0)
            self.assertIn("missing collector sample file", rc.stderr)


if __name__ == "__main__":
    unittest.main()
