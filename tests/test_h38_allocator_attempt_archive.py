"""Synthetic regressions for read-only H38 archive/offline attribution."""
from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import io
import pathlib
import tarfile
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "scripts/benchmark/analyze-h38-allocator-attempt-archive.py"
spec = importlib.util.spec_from_file_location("h38_archive_analysis", ANALYZER)
assert spec and spec.loader
h38 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h38)
UTC = dt.timezone.utc


def archive_fixture(path: pathlib.Path, *, corrupt_offset: bool = False) -> None:
    """Eight synthetic one-second samples, with a protected stop at T+5.5."""
    begin = dt.datetime(2026, 10, 8, tzinfo=UTC)
    event = begin + dt.timedelta(seconds=5, milliseconds=500)
    fields = [
        "source", "kind", "wall_utc", "offset_s", "normal_o4_mib",
        "normal_o4plus_mib", "unmovable_o4plus_mib", "movable_o4plus_mib",
        "memavailable_mib", "memfree_mib", "swapfree_mib",
        "psi_some_avg10", "psi_full_avg10",
    ]
    csv_io = io.StringIO()
    writer = csv.DictWriter(csv_io, fieldnames=fields)
    writer.writeheader()
    raw = []
    for i in range(8):
        when = begin + dt.timedelta(seconds=i)
        writer.writerow({
            "source": "h38", "kind": "fast", "wall_utc": when.isoformat(),
            "offset_s": -5.5+i + (1 if corrupt_offset and i == 1 else 0),
            "normal_o4_mib": 1,
            "normal_o4plus_mib": 100-i*10 if i <= 5 else 10000,
            "memavailable_mib": 200-i*10,
            "memfree_mib": 100-i*10,
            "swapfree_mib": 1000,
            "psi_some_avg10": .01,
            "psi_full_avg10": .01,
        })
        sample_time = when.isoformat()
        buddy = "0 0 0 0 1600 0"
        mem = {
            "MemFree": (100-i*10)*1024,
            "MemAvailable": (200-i*10)*1024,
            "SwapFree": 1000*1024,
            "Active(anon)": 2*1024,
            "Inactive(anon)": 1*1024,
            "Active(file)": (20+i*2)*1024,
            "Inactive(file)": 10*1024,
            "Unevictable": 0,
            "Slab": 1*1024,
            "KReclaimable": 2*1024,
            "SReclaimable": 2*1024,
            "PageTables": 1*1024,
            "SecPageTables": 0,
            "KernelStack": 1*1024,
        }
        raw.append(
            f"===== sample seq={i+1} wall={sample_time} monotonic_ns={i*1000000000+1} =====\n"
            f"--- /proc/buddyinfo ---\nNode 0, zone Normal {buddy}\n"
            "--- /proc/meminfo ---\n"
            + "\n".join(f"{k}: {v} kB" for k,v in mem.items())
            + "\n--- /proc/vmstat ---\nnr_free_pages 1000\n"
        )
    for i, val in [(0, 40), (5, 20), (7, 10000)]:
        when = begin + dt.timedelta(seconds=i)
        writer.writerow({
            "source": "h38", "kind": "slow",
            "wall_utc": when.isoformat(), "offset_s": -5.5+i,
            "unmovable_o4plus_mib": val, "movable_o4plus_mib": 10,
        })
    strings = {
        "allocator-trajectory.csv": csv_io.getvalue(),
        "allocator-analysis.txt": f"event_type=PROTECTED_STOP event_utc={event.isoformat()}\n",
        "startup-phase.txt": "\n".join(
            f"{(begin+dt.timedelta(seconds=i)).isoformat()} (Worker pid=1) "
            f"\rLoading safetensors checkpoint shards: 0% Completed | {count}/18"
            for i,count in ((0,0),(3,1),(6,2))
        ),
        "allocator-state/fast-state.txt": "\n".join(raw),
    }
    with tarfile.open(path, "w:gz") as handle:
        for name, value in strings.items():
            data = value.encode()
            member = tarfile.TarInfo(name)
            member.size = len(data)
            handle.addfile(member, io.BytesIO(data))


class H38ArchiveOfflineTests(unittest.TestCase):
    def test_parenthetical_meminfo_is_accounted_not_silently_dropped(self) -> None:
        mem = {name: 0 for name in h38.CORE}
        mem.update({"KReclaimable": 8, "SReclaimable": 5, "Active(file)": 100})
        self.assertEqual(h38.resident_core(mem), 103)

    def test_post_protection_samples_and_shards_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = pathlib.Path(tmp) / "fixture.tar.gz"
            archive_fixture(archive)
            result = h38.inspect(str(archive))
            self.assertEqual(result["samples"]["fast_pre_event"], 6)
            self.assertEqual(result["samples"]["fast_post_event_excluded"], 2)
            self.assertEqual(result["samples"]["slow_post_event_excluded"], 1)
            self.assertEqual(result["largest_normal_o4plus_drop_5s"]["delta_mib"], -50)
            self.assertEqual(result["normal_burst_aligned_metrics"]["core_mib_delta_mib"], 10)
            self.assertEqual(result["largest_core_residual_growth_5s"]["delta_mib"], 40)
            self.assertEqual(result["startup_progress"]["last_logged_before_protection"], 1)
            self.assertEqual(result["startup_progress"]["first_logged_after_protection"], 2)

    def test_csv_event_offset_mismatch_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = pathlib.Path(tmp) / "fixture.tar.gz"
            archive_fixture(archive, corrupt_offset=True)
            with self.assertRaisesRegex(ValueError, "offset/event time mismatch"):
                h38.inspect(str(archive))


if __name__ == "__main__":
    unittest.main()
