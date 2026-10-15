## 2026-10-15 — Whole-Docker physical inventory: 17 Hybrid references

Operator ran the maintained read-only Hybrid Docker inventory command after
fast-forward to `c93b074`. It returned
`HYBRID_RESEARCH_DOCKER_CANDIDATES=17` and
`HYBRID_DOCKER_INVENTORY=PASS_READ_ONLY`; all 17 were `exited`.
Exactly six belong to the previously SHA256-checked local six-container
archive. **Eleven more historical Docker objects need their evidence
preservation reviewed**; the six-container archive does not cover them:

| Additional historical Docker object | Full observed Docker ID |
|---|---|
| qwen38-h6-kv16-control | `10f8645adee052bd7506f1237e4064bcbbfb189caaeacbb9759981eaa33b32a5` |
| qwen38-h6-kv16-rmuvm-r8 | `2ea2a61cb2e07df79044280ac1c65ffa5bda8fb3084501ea87853b7d6fbf20e1` |
| qwen38-h6-kv8-instrumented-r2 | `3b7e6badbd653f38f18e884c287b96c3c37cf005822cbc9ccb03f741d7421254` |
| qwen38-h6-kv8-control | `569f2720593f4d0f768342c1417a9d2363fba894fd7f83a8de8a5df0dd2a9d51` |
| qwen38-h6-kv145-trace-r5 | `586fb729f12cfb8971ba5ed21ef4fdff4845505d132511cfcacb269c77e045a0` |
| qwen38-h6-kv8-instrumented | `7a871dfd8c7dbc63f7e3943a7261003e9564442a28c486b6cd6b3b8bf672cc45` |
| qwen38-h6-kv15-trace-r6 | `ba4029544a1ef39ffc2ab316da9ceb4cb975e845344c6be9bf683fc50db2ca5a` |
| qwen38-h6-kv16-rmsys-r9 | `c14af278cc738258a8fda1d686595864f845ff11cf4b223e8c1f48d92be06ca1` |
| qwen38-h6-kv14-control | `df2787a3fab4ef0d6d953e62ba4f7af380eebc46bf220734804b993cec5ac21b` |
| qwen38-h6-kv12-control | `e029767f2882aa50636bcabf55a55d4adda0c3b25c4d41c2b58d8d0b0f915a1c` |
| qwen38-h6-kv16-trace-r7 | `efa06c76207540a3ffa034e1e8d21156565a458be91486b5bac1208bbe9a1aec` |

These additional eleven bind historical `/home/inlc/models/` paths;
the operator confirmed it was a symlink to the project model assets
although the link is now absent. All 17 are **research inventory
candidates**, not individually approved removal IDs. No raw logs,
environment/secrets, or full inspect configs were committed. Neither
Docker removal nor checkpoint reclamation has happened.

# DGX Hybrid local research retirement — operator scope and immutable inventory

## Provenance and policy (2026-10-15)

Operator explicitly clarified: local Hybrid checkpoint/research resources may be
removed after the experiment records are preserved in Git. **The checkpoint
weight bytes do not need an independent off-host backup.** Removing the bytes
is irreversible without reconstructing the checkpoints from source inputs;
the Git evidence is not a weight backup. This record is a **non-destructive
evidence inventory**, not consent to execute an unreviewed deletion command.

Original OrcaRouter source checkpoint (~171G), managed runtime/container,
PLE swap, mazinb physical M1 benchmark originals, model switching/install
capacity and all non-Hybrid project resources are excluded from retirement.

## Verified physical observations

- Four local Hybrid stages: H3 `qwen3.8-hybrid-quant-layout` (~73G),
  H4 `qwen3.8-h4-orca-all` (~64G), H5
  `qwen3.8-h5-neutral-input-scale` (~43M), and H6
  `qwen3.8-h6-modelopt-w4a16` (~34M). Total allocated
  approximately **136G**, but post-deletion `df` recovery is not yet measured.
- Exact six historical Hybrid Docker objects were confirmed exited, name and
  64-hex ID checked, and their selected logs plus sanitized metadata were
  archived locally; manifest 7/7 SHA256 PASS. Full immutable IDs:

| Container | Docker ID |
|---|---|
| H6 physical M1 | `e526189f1093e95d81568d82eb10b8beaeb6227adca49029f241634769e6cbc7` |
| R28 unquant linear | `e2b000b28d5e71922e20d59f9725c8ebe54c5794349a20515343302f8d608e2a` |
| R27 linear | `43afd5055614c273181bd8f91d251ab19ac88d49080f3362cf7bcc31143c5c65` |
| R26 construction | `bd6886aa4499f14e12e8ce3e49c2400ec2a0d940bf4e0d03a0d8fe3d1d5ba14c` |
| R25b initialization | `6484fdf56ffbec15d76333bda1a36f05ca50b9f17841b37e41e0781343a8b2e0` |
| R24 KV16 | `e937e0f23e45ba4ee8851e79e60eaefc509367b74a021e67a74fea098ad17f62` |

- Original H6 2026-10-14 archive was located at
  `~/h6-m1-evidence-20261014.dvQmt6eq`, archive ~108K:
  `active.json`, `trial.json`, `monitor.log`,
  `runtime-stop.env`, `docker-inspect.json`, `docker.log`,
  `kernel-window.log` all passed SHA256 against the existing local manifest
  on 2026-10-15. Zero-byte `kernel.log` was not part of that manifest.
- Separate exact-six evidence archive at
  `~/.local/state/qwen38-spark/hybrid-retirement-evidence` was ~756K,
  metadata and six timestamped rendered Docker logs, manifest 7/7 PASS.
  These are local archives, not independently duplicated raw bytes in Git.
- H6 direct physical M1 completed first 81/81 safetensors progress in
  577.40s but entered a second pass and was stopped by watchdog memory
  protection. **Not READY, inference PASS, or benchmark measured.**
  Detailed normalized-log event chronology and safety limits remain in
  [the canonical immutable physical H6 report](dgx-hybrid-h6-m1-protection-stop-physical-20261014.md).
- The six exited objects each bind H3-H6 and OrcaRouter, and registry
  aliases include H7 and H20 against H6. Additional exited
  `qwen38-h6-kv16-rmsys-r9` Docker ID
  `c14af278cc738258a8fda1d686595864f845ff11cf4b223e8c1f48d92be06ca1`
  binds historical paths `/home/inlc/models/qwen3.8-h*`.
  Operator established that `/home/inlc/models` was a symlink to the
  project `models` root; although it no longer exists, its historical
  Docker mount string is a **real research dependency**, not a distinct
  safe directory. No automatic addition to the six-container delete set.

## Record preservation boundary

This Git document deliberately contains no raw Docker inspect JSON
(which can expose secrets or environment), unreviewed raw logs, model weights,
or caches. The detailed physical report linked above remains part of Git;
the 7+7 archived payloads are **still on the DGX** and must not be misrepresented
as Git-hosted copies. Before deleting the only raw copies, produce a redacted
or reviewed portable Git evidence bundle or explicitly decide which raw bytes
are not required. The existing repository docs alone are not proof that the
raw logs and Docker inspect payloads have been uploaded.

Current stage: `GIT_SUMMARY_COMMITTED` when this document reaches HEAD,
`GIT_RAW_EVIDENCE=NOT_ARCHIVED`, `DELETE_EXECUTED=NO`.
Exact-target staged removal and Docker alias/profile dependency handling,
including verification of the protected OrcaRouter, require a separate
explicit reviewed operation and measured filesystem recovery.
