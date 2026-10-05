# OrcaRouter R23 RM/UVM ownership probe preflight result — 2026-10-04

## Classification

R23 probe-only preflight is **PASS**.

Live R23 ownership tracing has **not** been run yet. Current state is therefore:

**PREFLIGHT PASS / LIVE TEST NOT YET RUN**

The validated repository head was:

`05fa0b532847f89e30f499c78dfb498cba32ef08`

Host evidence directory:

`/tmp/orcarouter-r23-ownership-probe-preflight-20261004-221456`

The preflight explicitly reported:

- `R23_PROBE_PREFLIGHT=PASS`
- `tracefs=/sys/kernel/tracing`
- `probe_group=r23_own`
- `target_count=6`
- `event_count=12`
- `model_restart=NO`
- `persistent_vm_tuning=NO`

## Validated trace targets

All six selected ownership-boundary functions were ftrace-visible on the DGX Spark host:

- `nv_alloc_pages [nvidia]`
- `nv_alloc_system_pages [nvidia]`
- `nvUvmInterfacePmaAllocPages [nvidia]`
- `uvm_gpu_dma_alloc [nvidia_uvm]`
- `uvm_mem_alloc [nvidia_uvm]`
- `uvm_pmm_gpu_alloc_kernel [nvidia_uvm]`

No planned R23 boundary had to be dropped or replaced.

## Materialized dynamic events

All twelve entry/return events materialized successfully under `r23_own`:

- `nv_alloc_pages_entry`
- `nv_alloc_pages_ret`
- `nv_alloc_system_pages_entry`
- `nv_alloc_system_pages_ret`
- `pma_alloc_entry`
- `pma_alloc_ret`
- `uvm_dma_alloc_entry`
- `uvm_dma_alloc_ret`
- `uvm_mem_alloc_entry`
- `uvm_mem_alloc_ret`
- `uvm_pmm_alloc_entry`
- `uvm_pmm_alloc_ret`

The probe-format checks and trace-cmd smoke record completed successfully, followed by cleanup of the temporary dynamic probes.

## Consequence for R23 design

The initial R23 live probe set is now frozen to these six boundaries / twelve events. There is no evidence-based reason to broaden the first live run with page alloc/free, compaction/reclaim/extfrag, scheduler, function-graph, or all-driver tracing.

The next repository step is to implement and CI-validate:

1. a managed OrcaRouter runner using the established R21 conditioning/protection harness;
2. a narrow trace window of approximately startup `+20 s` through `+70 s`;
3. an analyzer that pairs entry/return events with trace-window boundary awareness, reports task/PID and request-shape activity, and aligns the driver activity with allocator-state residual formation;
4. strict FUNCTIONAL vs HOST-STABILITY classification unchanged from R9–R22.

Only after those pieces are green should the live R23 restart be executed.
