#!/usr/bin/env bash
# Read-only discovery of NVIDIA/UVM tracing hooks on the current host.
# Does not start vLLM and does not modify trace configuration.

set -Eeuo pipefail

OUT="${1:-/tmp/h6-rm-uvm-discovery-$(date +%Y%m%d)}"

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
    lsmod | grep -E '^nvidia|^uvm' || true

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

grep -Ei     'nvidia|uvm|gpu|fault|migration|migrate|mmu|iommu|dma'     "$OUT/all-trace-events.txt"     >"$OUT/relevant-trace-events.txt" || true

find "$TRACEFS/events"     -mindepth 2 -maxdepth 2 -type d -printf '%P\n' 2>/dev/null |
    sort >"$OUT/event-directories.txt"

grep -Ei     'nvidia|uvm|gpu|fault|migration|migrate|mmu|iommu|dma'     "$OUT/event-directories.txt"     >"$OUT/relevant-event-directories.txt" || true

: >"$OUT/nvidia-uvm-functions.txt"
: >"$OUT/allocation-function-candidates.txt"

if [[ -e "$TRACEFS/available_filter_functions" ]]; then
    sudo -n cat "$TRACEFS/available_filter_functions" |
        grep -Ei             'nvidia|uvm|(^|_)nv[_A-Za-z0-9]*|memdesc|mem_desc'         >"$OUT/nvidia-uvm-functions.txt" || true

    grep -Ei         'alloc|free|mem|page|phys|dma|map|fault|pin|migrat|reserve|commit|uvm|rm'         "$OUT/nvidia-uvm-functions.txt"         >"$OUT/allocation-function-candidates.txt" || true
fi

{
    echo "============================================================"
    echo "RM/UVM STATIC DISCOVERY SUMMARY"
    echo "============================================================"

    echo
    echo "trace-events=$(wc -l < "$OUT/relevant-trace-events.txt")"
    echo "event-directories=$(wc -l < "$OUT/relevant-event-directories.txt")"
    echo "nvidia-uvm-functions=$(wc -l < "$OUT/nvidia-uvm-functions.txt")"
    echo "allocation-function-candidates=$(wc -l < "$OUT/allocation-function-candidates.txt")"

    echo
    echo "=== relevant registered trace events ==="
    cat "$OUT/relevant-trace-events.txt"

    echo
    echo "=== allocation-related ftrace candidates ==="
    head -100 "$OUT/allocation-function-candidates.txt" || true

    echo
    echo "DISCOVERY_EVIDENCE=$OUT"
} | tee "$OUT/summary.txt"
