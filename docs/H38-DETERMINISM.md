# H38 determinism repair status

This document is the concise operational status for the OrcaRouter NVFP4
determinism repair on one NVIDIA DGX Spark GB10 using vLLM v0.29.

The canonical experiment log remains `scripts/benchmark/README.md`. This file
summarizes the current supported conclusion, runtime roles, validation gates,
and known integration gap.

## Supported root-cause statement

Under the tested OrcaRouter NVFP4 / vLLM v0.29 / GB10 conditions, legal
physical within-expert routed-token ordering can vary, and the Marlin MoE output
is sensitive to that physical ordering.

Canonicalizing the valid routed-token ordering immediately after
`moe_align_block_size()` removes the captured local W13-to-final-MoE
divergence. The intervention changes ordering only; routed membership, expert
IDs, padding semantics, weights, and GEMM implementation remain unchanged.

Do not generalize this into claims that CUDA is racy or that every Marlin
kernel is intrinsically nondeterministic.

## Production scope decision

Matched scope validation completed for decoder-only and all-call
canonicalization.

Each scope passed:

- fresh-container cycle 1;
- fresh-container cycle 2;
- one isolated fresh-compile lifecycle;
- 1K / 128 x20 standalone;
- 32K / 128 x10 standalone;
- forward QSA sweep 1K -> 2K -> 4K -> 8K -> 32K, five repeats per size;
- reverse QSA sweep 32K -> 8K -> 4K -> 2K -> 1K, five repeats per size.

Every validated gate reported `unique_hashes=1` and every QSA sweep reported
`first_failure_tokens=null`.

Stable standalone hashes were the same across both scopes:

```text
1K:
44867e5c36d54b5bbec26f7c4f7c500783602a4bbc1b1545758929fc1c763670

32K:
d6fa888525cd888595d9c51c2a24aa248cce55cfd35d16bdc0ddbba0a8e78d39
```

No determinism advantage was observed for all-call canonicalization.
Decoder-only is therefore preferred under the minimum-change principle.

## Runtime role mapping

| Role | Runtime profile | Image | Scope |
|---|---|---|---|
| H38 production runtime | `hybrid-h38-deterministic` | `vllm-orcarouter-v029-h38-decoder-scope:v1` | decoder |
| decoder A/B control | `hybrid-h38-decoder-scope` | `vllm-orcarouter-v029-h38-decoder-scope:v1` | decoder |
| fallback/regression control | `hybrid-h38-all-scope` | `vllm-orcarouter-v029-h38-deterministic:v1` | all calls |

The profile names are runtime roles. The all-call image keeps its historical
name for regression continuity; do not infer its preferred production role from
the image tag.

## Production-alias gate — completed

The final promoted production-alias matrix completed on 2026-09-28 with:

```bash
bash scripts/benchmark/run-h38-production-gate.sh
```

The gate exercised:

```text
hybrid-h38-deterministic/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

with the decoder-scope production image
`vllm-orcarouter-v029-h38-decoder-scope:v1`.

Recorded runtime controls included Marlin canonical order enabled with
scope `decoder`, exact QSA, MTP `k=2`, `max_model_len=262144`,
`max_num_batched_tokens=8192`, `max_num_seqs=3`, prefix caching disabled,
and PLE mmap enabled.

Results:

- 1K / 128 x20: PASS, `unique_hashes=1`;
- 32K / 128 x10: PASS, `unique_hashes=1`;
- forward QSA 1K -> 2K -> 4K -> 8K -> 32K x5: PASS at every size,
  `first_failure_tokens=null`;
- reverse QSA 32K -> 8K -> 4K -> 2K -> 1K x5: PASS at every size,
  `first_failure_tokens=null`.

The gate report identifies Git revision
`29ec139bf1de8c2fcc2cbfc2f348d0741c0c7fd0` and release ID
`1bdc6932067d3110531f5c76b10e2842a98a9bb5`. The detailed result and
per-gate hashes are recorded in `scripts/benchmark/README.md`.

Those gate hashes differ from the earlier matched scope-A/B regression markers
because the benchmark runner uses repository-root `README.md` as its default
corpus and PR #215 changed that corpus before the production-alias run. The
token-size targets match, but this is not a same-input hash comparison.

Therefore the H38 determinism repair is closed for the validated
`scripts/runtime/orcarouter-v029.sh` production runtime track. This closure
does not include the transactional installer/systemd managed-service path,
which remains a separate integration and lifecycle-qualification phase.

## Managed-service integration — candidate implemented, live qualification pending

> **Naming boundary:** installer profile `orcarouter-hybrid` is the generated
> H6 ModelOpt W4A16 checkpoint from the earlier checkpoint-isolation track. It
> is not the H38 decoder-only runtime repair.

The H38 runtime qualification above remains the historical qualification for
`scripts/runtime/orcarouter-v029.sh`. The current feature branch now wires the
same decoder-scope H38 image into the transactional `orcarouter` managed path,
but that managed promotion is **not qualified or complete yet**.

The candidate implementation covers:

- `scripts/model/model-profiles.sh`: the OrcaRouter profile default selects
  `vllm-orcarouter-v029-h38-decoder-scope:v1`;
- `scripts/runtime/prepare-h38-image.sh`: clean-host/reuse construction of the
  v0.29 -> H9 -> H10 -> H11 -> H12 -> H38 image chain with fail-closed label
  verification;
- `install.sh`: H38 image preparation and explicit
  `--refresh-profile-defaults` migration;
- `scripts/serve.sh`: H38 PLE-mmap, exact-QSA, decoder canonicalization and
  isolated compile-cache controls while retaining the managed 16 GiB KV
  resilience value;
- `scripts/runtime/preflight-runtime.sh` and `scripts/doctor.sh`: H38 image
  provenance/runtime-control checks;
- `scripts/model-assets.sh`: H38 managed image inventory;
- the existing service-runner/runtime-transition path remains the transactional
  replacement and attestation mechanism.

Existing OrcaRouter installs now use one explicit **atomic cross-release
same-profile refresh**. The retired sequence

`new immutable code -> persisted legacy CPU-offload READY -> H38 refresh`

must not be used: the matched PR-base-main control reproduced the same protected
legacy restart, so that intermediate is not a valid H38 discriminator.

The supported operator route is:

```bash
scripts/update-release.sh RELEASE_ID --refresh-profile-defaults
```

For live qualification, use the guarded exact-SHA migration wrapper documented in
`scripts/benchmark/evidence/orcarouter-h38-managed-integration-plan-20261007.md`.
Only after that migration gate passes should
`scripts/run-h38-managed-followup-gates.sh` run the managed-alias determinism,
matched >=90% decode-performance, managed restart/attestation, and strict RM follow-up
window against the same migration evidence baseline.

The transaction first qualifies the exact immutable target release and prepares the
H38 image, then activates the target release pointer plus H38 `service_ready`
manifest before the single managed-service replacement. Target READY/attestation does
not destroy the previous runtime immediately: the runtime rollback container remains
available until the outer release/profile transaction commits. Failure recovery binds
the exact predecessor container ID, release pointers, install manifest, service
attachment, and restored-release monitor policy. It does not require a new-code +
legacy-image READY state and does not unconditionally cold-start the legacy runtime.

Do not describe installer/systemd OrcaRouter as H38 production until the live
acceptance in
`scripts/benchmark/evidence/orcarouter-h38-managed-integration-plan-20261007.md`
passes lifecycle/restart/doctor, managed-alias determinism, performance, and
strict NVIDIA RM host-stability gates. FUNCTIONAL and HOST-STABILITY results
must be recorded separately.

Historical H38 runtime evidence and failed/superseded attempts remain unchanged.

## Remaining limitations

The supported conclusion is limited to:

- OrcaRouter checkpoint revision
  `c1209bda15a6bbc4c68b585e93d40c0d85f50306`;
- single DGX Spark GB10;
- vLLM v0.29;
- tested runtime controls including exact QSA, MTP k=2,
  `max_num_seqs=3`, prefix caching disabled, and PLE mmap;
- the benchmark matrix documented above.

It does not prove universal determinism across different checkpoints, GPUs,
vLLM versions, kernels, scheduling modes, or prompt distributions.

## Preserve for regression

Do not delete while the H38/H20 evidence remains operationally relevant:

- H12 base image;
- H20 diagnostic images and instrumentation;
- H38 decoder and all-call images;
- retained model directories and PLE files;
- prior benchmark reports and failed experiments.

Failed hypotheses, instrumentation failures, and superseded scope conclusions
remain part of the canonical history in `scripts/benchmark/README.md`.
