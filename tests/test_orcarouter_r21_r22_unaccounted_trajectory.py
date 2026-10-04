import pathlib
import subprocess
import tempfile
import unittest


SCRIPT = pathlib.Path("scripts/benchmark/compare-orcarouter-r21-r22-unaccounted-trajectory.py")


class UnaccountedTrajectoryTest(unittest.TestCase):
    def write_meminfo(self, path: pathlib.Path, memfree_mib: float, file_mib: float, anon_mib: float, swapfree_mib: float) -> None:
        values = {
            "MemFree": memfree_mib,
            "MemAvailable": memfree_mib - 1.0,
            "Active(anon)": anon_mib,
            "Inactive(anon)": 0.0,
            "Active(file)": file_mib,
            "Inactive(file)": 0.0,
            "Unevictable": 0.0,
            "Slab": 0.0,
            "KReclaimable": 0.0,
            "SReclaimable": 0.0,
            "PageTables": 0.0,
            "SecPageTables": 0.0,
            "KernelStack": 0.0,
            "SwapFree": swapfree_mib,
        }
        path.write_text("".join(f"{key}: {value * 1024:.0f} kB\n" for key, value in values.items()), encoding="utf-8")

    def make_run(self, root: pathlib.Path) -> None:
        (root / "poststop-after-compact").mkdir(parents=True)
        event = root / "allocator-state" / "events" / "rm-oom-01-1"
        event.mkdir(parents=True)
        self.write_meminfo(root / "poststop-after-compact" / "proc-meminfo.txt", 100.0, 0.0, 0.0, 100.0)
        self.write_meminfo(event / "proc-meminfo.txt", 20.0, 10.0, 5.0, 90.0)
        event.joinpath("meta.txt").write_text(
            "wall=2026-10-04T00:00:06+00:00\nmonotonic_ns=6000000000\n",
            encoding="utf-8",
        )
        root.joinpath("compact-complete-iso.txt").write_text("2026-10-04T00:00:00+00:00\n", encoding="utf-8")

        samples = []
        states = [
            (0, 100.0, 0.0, 0.0, 100.0),
            (1, 85.0, 1.0, 1.0, 99.0),
            (2, 70.0, 2.0, 2.0, 98.0),
            (3, 55.0, 3.0, 3.0, 97.0),
            (4, 40.0, 5.0, 4.0, 95.0),
            (5, 25.0, 8.0, 5.0, 92.0),
            (6, 20.0, 10.0, 5.0, 90.0),
        ]
        for seq, (second, free, file_mib, anon_mib, swapfree) in enumerate(states, start=1):
            samples.append(
                f"===== sample seq={seq} wall=2026-10-04T00:00:{second:02d}+00:00 monotonic_ns={second * 1000000000} =====\n"
            )
            samples.append("--- /proc/meminfo ---\n")
            temp = root / f"mem-{seq}.txt"
            self.write_meminfo(temp, free, file_mib, anon_mib, swapfree)
            samples.append(temp.read_text(encoding="utf-8"))
            temp.unlink()
            samples.append("\n--- /proc/vmstat ---\nnr_free_pages 1\n")
        (root / "allocator-state" / "fast-state.txt").write_text("".join(samples), encoding="utf-8")

    def test_reports_crossings_and_largest_increases(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            r21 = base / "r21"
            r22 = base / "r22"
            self.make_run(r21)
            self.make_run(r22)
            proc = subprocess.run(
                ["python3", str(SCRIPT), "--r21", str(r21), "--r22", str(r22)],
                check=True,
                text=True,
                capture_output=True,
            )
            out = proc.stdout
            self.assertIn("ORCA_R21_R22_UNACCOUNTED_TRAJECTORY=BEGIN", out)
            self.assertIn("unaccounted_window=R21", out)
            self.assertIn("unaccounted_window=R22", out)
            self.assertIn("unaccounted_crossing=R21 fraction=0.50", out)
            self.assertIn("unaccounted_crossing=R22 fraction=0.90", out)
            self.assertIn("unaccounted_largest_increase=R21 target_s=1 found=1", out)
            self.assertIn("unaccounted_largest_increase=R22 target_s=5 found=1", out)
            self.assertIn("ORCA_R21_R22_UNACCOUNTED_TRAJECTORY=END", out)


if __name__ == "__main__":
    unittest.main()
