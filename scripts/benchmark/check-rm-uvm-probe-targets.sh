#!/usr/bin/env bash
# Validate exact RM/UVM ftrace probe targets on the current host.
# Read-only: does not enable tracing or create dynamic probes.

set -Eeuo pipefail

OUT="${1:-/tmp/h6-rm-uvm-probe-targets-$(date +%Y%m%d)}"

if [[ -e "$OUT" ]]; then
    echo "PROBE_TARGET_OUTPUT_ALREADY_EXISTS=$OUT"
    exit 2
fi

mkdir -p "$OUT"

TRACEFS="/sys/kernel/tracing"
if [[ ! -e "$TRACEFS/available_filter_functions" ]]; then
    TRACEFS="/sys/kernel/debug/tracing"
fi

AFF="$OUT/available-filter-functions.txt"
sudo -n cat "$TRACEFS/available_filter_functions" >"$AFF"

targets=(
    "nv_alloc_pages:nvidia:rm-sysmem-dispatch"
    "nv_alloc_system_pages:nvidia:rm-sysmem-noncontig"
    "nv_alloc_contig_pages:nvidia:rm-sysmem-contig"
    "rm_gpu_ops_pma_alloc_pages:nvidia:rm-pma-boundary"
    "nvUvmInterfacePmaAllocPages:nvidia:uvm-to-rm-pma-boundary"
    "uvm_gpu_dma_alloc:nvidia_uvm:uvm-dma-allocation"
    "uvm_mem_alloc:nvidia_uvm:uvm-memory-allocation"
    "uvm_pmm_gpu_alloc_kernel:nvidia_uvm:uvm-pmm-allocation"
    "replayable_faults_isr_bottom_half:nvidia_uvm:uvm-fault-context"
)

printf '%-38s %-14s %-8s %s\n' FUNCTION MODULE STATUS ROLE     | tee "$OUT/summary.txt"
printf '%-38s %-14s %-8s %s\n' "--------------------------------------" "--------------" "--------" "----"     | tee -a "$OUT/summary.txt"

for item in "${targets[@]}"; do
    IFS=: read -r fn mod role <<<"$item"

    if grep -Eq "^\\Q$fn\\E( |$).*\\[$mod\\]$" "$AFF" 2>/dev/null; then
        status="PRESENT"
    elif grep -Eq "^$fn( |$).*\\[$mod\\]$" "$AFF"; then
        status="PRESENT"
    else
        status="MISSING"
    fi

    printf '%-38s %-14s %-8s %s\n' "$fn" "$mod" "$status" "$role"         | tee -a "$OUT/summary.txt"
done

{
    echo
    echo "tracefs=$TRACEFS"
    [[ -e "$TRACEFS/kprobe_events" ]] && echo "kprobe_events=YES" || echo "kprobe_events=NO"
    [[ -e "$TRACEFS/fprobe_events" ]] && echo "fprobe_events=YES" || echo "fprobe_events=NO"
    echo "PROBE_TARGET_EVIDENCE=$OUT"
} | tee -a "$OUT/summary.txt"
