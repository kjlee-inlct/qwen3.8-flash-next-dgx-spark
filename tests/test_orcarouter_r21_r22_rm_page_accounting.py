import pathlib
import subprocess
import tempfile
import unittest


SCRIPT = pathlib.Path("scripts/benchmark/compare-orcarouter-r21-r22-rm-page-accounting.py")


MEMINFO_POST = """MemFree:       102400 kB
MemAvailable:  92160 kB
Active(anon):   1024 kB
Inactive(anon): 1024 kB
Active(file):   1024 kB
Inactive(file): 1024 kB
Unevictable:       0 kB
Slab:            512 kB
KReclaimable:    256 kB
SReclaimable:    256 kB
PageTables:      128 kB
SecPageTables:    64 kB
KernelStack:      64 kB
CmaFree:        4096 kB
SwapFree:      65536 kB
"""

MEMINFO_EVENT = """MemFree:        51200 kB
MemAvailable:   46080 kB
Active(anon):    2048 kB
Inactive(anon):  1024 kB
Active(file):    3072 kB
Inactive(file):  5120 kB
Unevictable:        0 kB
Slab:            1024 kB
KReclaimable:     256 kB
SReclaimable:     256 kB
PageTables:       256 kB
SecPageTables:    128 kB
KernelStack:      128 kB
CmaFree:         4096 kB
SwapFree:       61440 kB
"""

VMSTAT_POST = """nr_free_pages 25600
nr_active_anon 256
nr_inactive_anon 256
nr_active_file 256
nr_inactive_file 256
nr_unevictable 0
nr_anon_pages 256
nr_file_pages 512
nr_shmem 0
nr_page_table_pages 32
nr_sec_page_table_pages 16
nr_free_cma 1024
nr_kernel_misc_reclaimable 0
nr_slab_reclaimable_b 262144
nr_slab_unreclaimable_b 262144
"""

VMSTAT_EVENT = """nr_free_pages 12800
nr_active_anon 512
nr_inactive_anon 256
nr_active_file 768
nr_inactive_file 1280
nr_unevictable 0
nr_anon_pages 512
nr_file_pages 2048
nr_shmem 0
nr_page_table_pages 64
nr_sec_page_table_pages 32
nr_free_cma 1024
nr_kernel_misc_reclaimable 0
nr_slab_reclaimable_b 262144
nr_slab_unreclaimable_b 786432
"""

ZONE_POST = """Node 0, zone   Normal
  pages free     25600
        min      10
        low      20
        high     30
        spanned  40000
        present  40000
        managed  39000
"""

ZONE_EVENT = """Node 0, zone   Normal
  pages free     12800
        min      10
        low      20
        high     30
        spanned  40000
        present  40000
        managed  39000
"""


class PageAccountingTest(unittest.TestCase):
    def make_run(self, root: pathlib.Path) -> None:
        post = root / "poststop-after-compact"
        event = root / "allocator-state" / "events" / "rm-oom-01-test"
        post.mkdir(parents=True)
        event.mkdir(parents=True)
        (post / "proc-meminfo.txt").write_text(MEMINFO_POST)
        (event / "proc-meminfo.txt").write_text(MEMINFO_EVENT)
        (post / "proc-vmstat.txt").write_text(VMSTAT_POST)
        (event / "proc-vmstat.txt").write_text(VMSTAT_EVENT)
        (post / "proc-zoneinfo.txt").write_text(ZONE_POST)
        (event / "proc-zoneinfo.txt").write_text(ZONE_EVENT)

    def test_reports_residual_zone_and_vmstat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            r21 = base / "r21"
            r22 = base / "r22"
            self.make_run(r21)
            self.make_run(r22)
            proc = subprocess.run(
                ["python3", str(SCRIPT), "--r21", str(r21), "--r22", str(r22)],
                check=True,
                capture_output=True,
                text=True,
            )
        out = proc.stdout
        self.assertIn("ORCA_R21_R22_RM_PAGE_ACCOUNTING=BEGIN", out)
        self.assertIn("page_accounting=R21", out)
        self.assertIn("core_unexplained_loss_mib=", out)
        self.assertIn("page_zone=R22 node=0 zone=Normal", out)
        self.assertIn("free_delta_pages=-12800", out)
        self.assertIn("managed_delta_pages=+0", out)
        self.assertIn("page_vmstat=R21 key=nr_free_pages", out)
        self.assertIn("page_vmstat=R22 key=nr_slab_unreclaimable_b", out)
        self.assertIn("ORCA_R21_R22_RM_PAGE_ACCOUNTING=END", out)


if __name__ == "__main__":
    unittest.main()
