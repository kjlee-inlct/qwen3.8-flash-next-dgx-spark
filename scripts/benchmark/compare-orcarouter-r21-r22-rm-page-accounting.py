#!/usr/bin/env python3
"""Compare R21/R22 physical-page accounting at post-compact and RM event.

This helper is read-only. It deliberately avoids summing overlapping meminfo
categories such as Cached with Active(file), or AnonPages with Active(anon).
The reported residual is an approximate/core-unexplained physical-page loss,
not an exact attribution to NVIDIA RM.
"""

from __future__ import annotations

import argparse
import pathlib
import re

MIB_PER_PAGE = 4.0 / 1024.0  # 4 KiB base pages on the measured DGX Spark host.

MEMINFO_KEYS = (
    "MemFree",
    "MemAvailable",
    "Active(anon)",
    "Inactive(anon)",
    "Active(file)",
    "Inactive(file)",
    "Unevictable",
    "Slab",
    "KReclaimable",
    "SReclaimable",
    "PageTables",
    "SecPageTables",
    "KernelStack",
    "CmaFree",
    "SwapFree",
)

VMSTAT_KEYS = (
    "nr_free_pages",
    "nr_active_anon",
    "nr_inactive_anon",
    "nr_active_file",
    "nr_inactive_file",
    "nr_unevictable",
    "nr_anon_pages",
    "nr_file_pages",
    "nr_shmem",
    "nr_page_table_pages",
    "nr_sec_page_table_pages",
    "nr_free_cma",
    "nr_kernel_misc_reclaimable",
    "nr_slab_reclaimable_b",
    "nr_slab_unreclaimable_b",
)


def parse_meminfo(path: pathlib.Path) -> dict[str, float]:
    if not path.is_file():
        raise SystemExit(f"missing meminfo snapshot: {path}")
    result: dict[str, float] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in raw:
            continue
        key, rest = raw.split(":", 1)
        parts = rest.split()
        if not parts:
            continue
        try:
            value = float(parts[0])
        except ValueError:
            continue
        # /proc/meminfo uses KiB for memory-valued fields.
        result[key] = value / 1024.0
    return result


def parse_vmstat(path: pathlib.Path) -> dict[str, float]:
    if not path.is_file():
        raise SystemExit(f"missing vmstat snapshot: {path}")
    result: dict[str, float] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = raw.split()
        if len(parts) != 2:
            continue
        try:
            result[parts[0]] = float(parts[1])
        except ValueError:
            continue
    return result


def parse_normal_zone(path: pathlib.Path) -> dict[str, float]:
    if not path.is_file():
        raise SystemExit(f"missing zoneinfo snapshot: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^Node\s+0,\s+zone\s+Normal\s*$", text, re.MULTILINE)
    if not match:
        raise SystemExit(f"node0 Normal zone not found in: {path}")
    tail = text[match.end() :]
    next_zone = re.search(r"^Node\s+\d+,\s+zone\s+\S+\s*$", tail, re.MULTILINE)
    block = tail[: next_zone.start()] if next_zone else tail
    result: dict[str, float] = {}
    for key in ("free", "managed", "present", "spanned"):
        field = re.search(rf"^\s+{key}\s+(\d+)\s*$", block, re.MULTILINE)
        if field:
            result[key] = float(field.group(1))
    if "free" not in result or "managed" not in result:
        raise SystemExit(f"node0 Normal free/managed fields missing in: {path}")
    return result


def event_dir(root: pathlib.Path) -> pathlib.Path:
    dirs = sorted(p for p in (root / "allocator-state" / "events").glob("rm-oom-*") if p.is_dir())
    if len(dirs) != 1:
        raise SystemExit(f"expected exactly one RM event directory under {root}, found {len(dirs)}")
    return dirs[0]


def load(root: pathlib.Path) -> dict[str, tuple[dict[str, float], dict[str, float]]]:
    event = event_dir(root)
    return {
        "meminfo": (
            parse_meminfo(root / "poststop-after-compact" / "proc-meminfo.txt"),
            parse_meminfo(event / "proc-meminfo.txt"),
        ),
        "vmstat": (
            parse_vmstat(root / "poststop-after-compact" / "proc-vmstat.txt"),
            parse_vmstat(event / "proc-vmstat.txt"),
        ),
        "zone": (
            parse_normal_zone(root / "poststop-after-compact" / "proc-zoneinfo.txt"),
            parse_normal_zone(event / "proc-zoneinfo.txt"),
        ),
    }


def delta(before: dict[str, float], after: dict[str, float], key: str) -> float:
    return after.get(key, 0.0) - before.get(key, 0.0)


def core_accounting(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    memfree_loss = -delta(before, after, "MemFree")
    lru_growth = sum(
        delta(before, after, key)
        for key in (
            "Active(anon)",
            "Inactive(anon)",
            "Active(file)",
            "Inactive(file)",
            "Unevictable",
        )
    )
    slab_growth = delta(before, after, "Slab")
    # KReclaimable contains SReclaimable. Only count the non-slab excess once.
    non_slab_kreclaimable_growth = delta(before, after, "KReclaimable") - delta(
        before, after, "SReclaimable"
    )
    pagetable_growth = delta(before, after, "PageTables") + delta(
        before, after, "SecPageTables"
    )
    kernelstack_growth = delta(before, after, "KernelStack")
    explained = (
        lru_growth
        + slab_growth
        + non_slab_kreclaimable_growth
        + pagetable_growth
        + kernelstack_growth
    )
    residual = memfree_loss - explained
    return {
        "memfree_loss": memfree_loss,
        "lru_growth": lru_growth,
        "slab_growth": slab_growth,
        "non_slab_kreclaimable_growth": non_slab_kreclaimable_growth,
        "pagetable_growth": pagetable_growth,
        "kernelstack_growth": kernelstack_growth,
        "core_explained_growth": explained,
        "core_unexplained_loss": residual,
        "memavailable_loss": -delta(before, after, "MemAvailable"),
        "cmafree_delta": delta(before, after, "CmaFree"),
        "swapfree_delta": delta(before, after, "SwapFree"),
    }


def emit_vmstat(run: str, before: dict[str, float], after: dict[str, float]) -> None:
    for key in VMSTAT_KEYS:
        if key not in before and key not in after:
            continue
        raw_delta = delta(before, after, key)
        if key.endswith("_b"):
            mib_delta = raw_delta / (1024.0 * 1024.0)
            unit = "bytes"
        else:
            mib_delta = raw_delta * MIB_PER_PAGE
            unit = "pages"
        print(
            f"page_vmstat={run} key={key} raw_delta={raw_delta:+.0f} "
            f"assumed_unit={unit} approx_mib_delta={mib_delta:+.3f}"
        )


def emit_run(run: str, loaded: dict[str, tuple[dict[str, float], dict[str, float]]]) -> None:
    mem_before, mem_after = loaded["meminfo"]
    vm_before, vm_after = loaded["vmstat"]
    zone_before, zone_after = loaded["zone"]
    acc = core_accounting(mem_before, mem_after)
    print(
        "page_accounting=" + run
        + " "
        + " ".join(f"{key}_mib={value:+.3f}" for key, value in acc.items())
    )
    free_delta_pages = delta(zone_before, zone_after, "free")
    managed_delta_pages = delta(zone_before, zone_after, "managed")
    print(
        f"page_zone={run} node=0 zone=Normal "
        f"free_post_pages={zone_before['free']:.0f} free_event_pages={zone_after['free']:.0f} "
        f"free_delta_pages={free_delta_pages:+.0f} free_delta_mib={free_delta_pages * MIB_PER_PAGE:+.3f} "
        f"managed_post_pages={zone_before['managed']:.0f} managed_event_pages={zone_after['managed']:.0f} "
        f"managed_delta_pages={managed_delta_pages:+.0f}"
    )
    emit_vmstat(run, vm_before, vm_after)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r21", required=True)
    parser.add_argument("--r22", required=True)
    args = parser.parse_args()

    roots = {"R21": pathlib.Path(args.r21), "R22": pathlib.Path(args.r22)}
    print("ORCA_R21_R22_RM_PAGE_ACCOUNTING=BEGIN")
    for run in ("R21", "R22"):
        emit_run(run, load(roots[run]))
    print("ORCA_R21_R22_RM_PAGE_ACCOUNTING=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
