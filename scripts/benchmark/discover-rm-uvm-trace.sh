#!/usr/bin/env bash
# Read-only discovery of NVIDIA RM/UVM tracing hooks on the current host.
# Does not start vLLM and does not modify trace configuration.
#
# The important distinction here is module ownership:
# available_filter_functions normally annotates loadable-module symbols as:
#   function_name [module_name]
# We therefore filter exact [nvidia] / [nvidia_uvm] tags instead of matching
# generic strings such as "nvidia", which also catches unrelated nvmem/nvdimm
# and platform-driver symbols.

set -Eeuo pipefail

OUT="${1:-/tmp/h6-rm-uvm-discovery-v2-$(date +%Y%m%d)}"

if [[ -e "$OUT" ]]; then
    echo "DISCOVERY_OUTPUT_ALREADY_EXISTS=$OUT"
    exit 2
fi

mkdir -p "$OUT"

TRACEFS="/sys/kernel/tracing"
if [[ ! -d "$TRACEFS/events" ]]; then
    TRACEFS="/sys/kernel/debug/tracing"
fi

echo "tracefs=$TRACEFS"

{
    echo "=== uname ==="
    uname -a

    echo
    echo "=== NVIDIA ==="
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader || true

    echo
    echo "=== modules ==="
    lsmod | grep -E '^nvidia(_uvm|_modeset|_drm|_peermem)?\b' || true

    echo
    echo "=== nvidia ==="
    modinfo nvidia 2>/dev/null |
        grep -E '^(filename|version|srcversion|vermagic):' || true

    echo
    echo "=== nvidia_uvm ==="
    modinfo nvidia_uvm 2>/dev/null |
        grep -E '^(filename|version|srcversion|vermagic):' || true
} >"$OUT/host.txt"

sudo -n trace-cmd list -e >"$OUT/all-trace-events.txt"

# Registered NVIDIA/UVM trace events only. Keep generic VM/DMA events separate
# so they are not confused with driver-owned instrumentation.
grep -Ei '^(nvidia|nvidia_uvm|uvm):'     "$OUT/all-trace-events.txt"     >"$OUT/nvidia-uvm-trace-events.txt" || true

grep -Ei     '^(dma|iommu|gpu_mem|compaction|migrate|vmscan|kmem|filemap):'     "$OUT/all-trace-events.txt"     >"$OUT/supporting-vm-trace-events.txt" || true

: >"$OUT/nvidia-module-functions.txt"
: >"$OUT/nvidia-uvm-module-functions.txt"
: >"$OUT/rm-allocation-candidates.txt"
: >"$OUT/uvm-allocation-candidates.txt"

if [[ -r "$TRACEFS/available_filter_functions" ]]; then
    sudo -n cat "$TRACEFS/available_filter_functions"         >"$OUT/available-filter-functions.txt"

    # Exact module ownership.
    grep -E '\[nvidia\]$'         "$OUT/available-filter-functions.txt"         >"$OUT/nvidia-module-functions.txt" || true

    grep -E '\[nvidia_uvm\]$'         "$OUT/available-filter-functions.txt"         >"$OUT/nvidia-uvm-module-functions.txt" || true

    # High-signal candidate names only. Preserve full original line including
    # module tag so the owner remains explicit.
    grep -Ei         'alloc|free|mem(desc)?|page|phys|dma|map|pin|reserve|commit|heap|contig|sysmem'         "$OUT/nvidia-module-functions.txt"         >"$OUT/rm-allocation-candidates.txt" || true

    grep -Ei         'alloc|free|mem|page|phys|dma|map|fault|pin|migrat|va_|gpu_va|range|block|tracker'         "$OUT/nvidia-uvm-module-functions.txt"         >"$OUT/uvm-allocation-candidates.txt" || true
else
    echo "AVAILABLE_FILTER_FUNCTIONS_NOT_READABLE"         >"$OUT/available-filter-functions.txt"
fi

{
    echo "============================================================"
    echo "RM/UVM STATIC DISCOVERY V2 SUMMARY"
    echo "============================================================"

    echo
    echo "nvidia-uvm-trace-events=$(wc -l < "$OUT/nvidia-uvm-trace-events.txt")"
    echo "nvidia-module-functions=$(wc -l < "$OUT/nvidia-module-functions.txt")"
    echo "nvidia-uvm-module-functions=$(wc -l < "$OUT/nvidia-uvm-module-functions.txt")"
    echo "rm-allocation-candidates=$(wc -l < "$OUT/rm-allocation-candidates.txt")"
    echo "uvm-allocation-candidates=$(wc -l < "$OUT/uvm-allocation-candidates.txt")"

    echo
    echo "=== NVIDIA/UVM registered trace events ==="
    cat "$OUT/nvidia-uvm-trace-events.txt"

    echo
    echo "=== RM allocation candidates ==="
    head -120 "$OUT/rm-allocation-candidates.txt" || true

    echo
    echo "=== UVM allocation/fault candidates ==="
    head -160 "$OUT/uvm-allocation-candidates.txt" || true

    echo
    echo "DISCOVERY_EVIDENCE=$OUT"
} | tee "$OUT/summary.txt"
