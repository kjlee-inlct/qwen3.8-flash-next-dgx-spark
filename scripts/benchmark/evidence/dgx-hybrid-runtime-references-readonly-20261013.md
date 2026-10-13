# S3 actual DGX hybrid runtime-reference survey — 2026-10-13

**Evidence class:** `ACTUAL_DGX`. This record transcribes operator-supplied
terminal output. **Not** a GitHub CI or simulated-host execution.

- Source worktree SHA: `d14915549667e196356b8511526f9bfd4db42cd6`
- Same-SHA [GitHub Actions 38349291372](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38349291372): `SUCCESS`, **separate GITHUB_CI evidence**
- Host-local log path: `/home/inlc/dgx-hybrid-runtime-refs-20261013-141134.log`
- Actual model-root provenance: carried forward from the S2 audit: `/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models`. The S3 output does not print the model-root environment variable again.
- Tool: `inspect-hybrid-runtime-references.py` with the exact checkout SHA and explicit model root.

```text
S3_REFERENCE_SURVEY=BEGIN
SOURCE_SHA=d14915549667e196356b8511526f9bfd4db42cd6
HOST_MUTATION=NO
MODEL_START=NO
TENSOR_PAYLOAD_READ=NO
HOST_DANGLING_VIRTUAL_LINKS_ARE_NOT_AUTOMATIC_FAILURE=YES
REFERENCE_GAPS=0
BENCHMARK_BEFORE_RECLAIM=REQUIRED
MODEL_DELETION=BLOCKED_PENDING_EVIDENCE_AND_DEPENDENCY_REVIEW
S3_REFERENCE_SURVEY=COLLECTED_READ_ONLY
```

## Physical DGX observations

`INDEX_TENSORS` counts individual keys in each JSON `weight_map`;
`INDEX_SHARDS` counts distinct referenced safetensors filenames.
`VIRTUAL_CHAIN` means the inspection tool followed its source-declared
container alias map back to a regular host file; it does **not** certify
that a live Docker process has those exact mounts.

| Stage | Symlinks | Index tensor keys | Unique index shard filenames | DIRECT shard files | VIRTUAL_CHAIN |
|---|---:|---:|---:|---:|---:|
| OrcaRouter base | 0 | 223046 | 18 | 18 | 0 |
| mazinb | 0 | 296474 | 95 | 95 | 0 |
| H3 quant layout | 13 | 296474 | 66 | 63 | 3 |
| H4 Orca-all | 76 | 296474 | 81 | 15 | 66 |
| H5 neutral input | 91 | 296474 | 81 | 48 | 33 |
| H6 W4A16 | 139 | 296474 | 81 | 0 | 81 |
| **Total symlinks observed across H3-H6** | **319** | | | | |

All non-zero `LINK_TARGET_STAGE` alias classifications matched the
expected parent direction: H3 -> base (13), H4 -> H3 (76),
H5 -> H4 (91), H6 -> H5 (139).
Every *indexed safetensors shard filename* resolved according to the
tool's alias model; `REFERENCE_GAPS=0`. This is a successful
**index-linked-file reference survey**.

## Separate source review, not actual Docker proof

At the exact audited source revision, the `orcarouter-hybrid` branch
in `scripts/serve.sh` defines **read-only** bind-mount arguments:
H6 to `/model`, OrcaRouter base to `/base-model`, H3 to
`/h3-model`, H4 to `/h4-all`, H5 to `/h5-parent`.
The experiment entry `scripts/runtime/orcarouter-v029.sh` also defines
H6-specific ancestor mounts. These are **SOURCE_REVIEW** observations.
Neither the actual installed immutable release, current runtime container's
mounts, nor a successful H6 start was verified by S3.

S3 reports every symlink's alias **category**, but tests existence
and index reachability only for *indexed shard names*. It does not
follow/verify all non-shard symlink targets, payload bytes, tensor dtype,
reflink/CoW physical extents, snapshot retention, or benchmark records.
`du`-based 135.561 GiB H3+H4 figure from S2 is not certified
recoverable capacity. There was no Docker/model start/stop/remove.

## Gates after S3

- **S2:** PASS_READ_ONLY, as recorded in `dgx-hybrid-block-accounting-readonly-20261013.md`.
- **S3:** PASS_READ_ONLY at the exact SHA above.
- **S4:** NOT_RUN; proposed bounded check of *all* alias targets,
  source-declared mount contract, and filesystem capabilities. Not a
  live H6 acceptance certificate.
- **M1/M3:** NOT_QUALIFIED; **M4/H38:** BLOCKED.
- **M2 destructive/D0:** NOT_AUTHORIZED; **benchmarks:** 5/5 NOT_MEASURED.
- **Model/Docker deletion:** NOT_PERFORMED, explicitly blocked by evidence/dependencies.
- PR #259: Draft / Open / Unmerged at the time of this evidence.

Do not reinterpret S3 PASS as authorization to reclaim H3/H4, remove mazinb,
replace the stopped predecessor Docker object, or launch a model.
