# Physical DGX A5 wizard previews + original fourth-model L0 JSON: PASS (2026-10-13)

**Evidence class: ACTUAL_DGX, operator-provided terminal output.**
**Timestamp in log name:** 2026-10-13 11:37:21 KST, filename
`/home/inlc/dgx-wizard-a5-20261013-113721.log`; the actual
terminal transcript continued to the L0 command after the A5 log was
printed. The chat attachment is a 336-line pasted terminal transcript.
Its **uploaded text bytes** have SHA256
`98462852bff8cbd4586a512d2ce9cc008d0800a4458c5a062b9c48bbee355f0f`;
this is **not** an independently obtained hash of the on-host log file.

## Source and installed-state identities

- DGX Spark: one GB10, operator alone; checkout via **new detached worktree**
  `qwen38-wizard-a5-f2674f0a60682a62f6218c7bfbfc5e9e5d24e4b8`.
- Exact A5 HEAD: `f2674f0a60682a62f6218c7bfbfc5e9e5d24e4b8`,
  matching the completed-SUCCESS GitHub CI **38337033502**.
- Git fetch fast-forwarded the *origin remote-tracking ref* from
  `b35d0f3` to `f2674f0`; it did not switch the operator's original
  source checkout or installed release.
- Installed immutable `current`: `ff67bab3c94d6992f61b9535836df97f03b9c022`,
  unchanged before/after.
- Install manifest: `VALID`, `PHASE=complete`, profile `orcarouter`,
  image `vllm-skinny-tp1:v1`, protection and monitor **both 1**.
  Profile switch/runtime/update/release refresh all **IDLE**,
  stale artifacts **NONE**.
- Docker predecessor: `EXITED`. systemd: `INACTIVE`.
  `RUNTIME_ATTESTATION=MISSING`, actual API served model
  **NOT_VERIFIED** (expected for stopped runtime).
  Checkpoint status `MARKER_PRESENT_NOT_VERIFIED` in selected profile
  snapshot: A5 **did not** verify file content or live model readiness.

## Four preview paths + uninstall preview

```text
WIZARD_CHECK=model_inventory rc=0
WIZARD_CHECK=backend_inventory rc=0
WIZARD_CHECK=selected_profile_readonly rc=0
WIZARD_CHECK=installer_orcarouter-dry-run rc=0
WIZARD_CHECK=installer_nvidia-dry-run rc=0
WIZARD_CHECK=installer_mazinb-dry-run rc=0
WIZARD_CHECK=installer_orcarouter-hybrid-dry-run rc=0
WIZARD_CHECK=uninstall_preserve_dry_run rc=0
WIZARD_CHECK=uninstall_full_purge_preview_only rc=0
WIZARD_CHECK=fixture_test_wizard_ui.py rc=0
WIZARD_CHECK=fixture_test_wizard_menu_validation.py rc=0
WIZARD_CHECK=fixture_test_installer_profile_manager.py rc=0
WIZARD_CHECK=fixture_test_uninstall_wizard_preview.py rc=0
WIZARD_CHECK=fixture_test_lychee888_metadata.py rc=0
WIZARD_DGX_READONLY=PREVIEW_AND_FIXTURES_PASS
M1_LIVE=NOT_QUALIFIED
M2_DESTRUCTIVE=NOT_RUN
M3_LIVE_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
D0_DISPOSABLE=NOT_GRANTED
```

**14/14 read-only command blocks returned rc0; isolated unit test
subsets: 9 + 7 + 15 + 19 + 10 = 60/60.**
The previews confirm correctly targeted and displayed proposed
operations, not actual switching or deletion.

Selected inventory: OrcaRouter `installed/active`, NVIDIA
`absent/image absent`, mazinb `installed/image present`,
Hybrid H6 `installed/image present`; lychee888
`planned/not-installable`. The preview for NVIDIA therefore does
not imply offline/ready actual NVIDIA activation. Uninstall `--purge-all`
preview displayed an owned-image purge plan, but never executed it.

## Real host state preservation

```text
MANIFEST_SHA_BEFORE=68d56e776214d8df25bd98c632d9749e5e174c3b9f5c671b2db080035d582f0f
MANIFEST_SHA_AFTER =68d56e776214d8df25bd98c632d9749e5e174c3b9f5c671b2db080035d582f0f
OWNERSHIP_SHA_BEFORE=f127021e363d9441768d6e38017d77a785dbdd7305cd1d689a7520b935083b26
OWNERSHIP_SHA_AFTER =f127021e363d9441768d6e38017d77a785dbdd7305cd1d689a7520b935083b26
IMMUTABLE_CURRENT=ff67bab3c94d6992f61b9535836df97f03b9c022
```

A5 guard reports no changes to those three tracked identities. The
script is a targeted fingerprint audit, **not** a claim that literally
no other system process changed during the same interval.

## lychee888 L0 real-Hub JSON probe (independent, after A5)

The user then executed
`python3 -B scripts/model/inspect_lychee888_metadata.py` in the
same exact source worktree. It performed network retrieval of the
Hub immutable revision's API, config and index JSON, **not** a
model weight download.

```json
{
  "checkpoint": "lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE",
  "immutable_revision": "1b3c3cedc14fb3bee4294dea5e3515af74b8268a",
  "index_tensor_keys": 223047,
  "ple_weight_shards": 128,
  "ple_files": 10,
  "global_weight_scale_keys": 1,
  "config_ple_embedding_dtype": "float8_e4m3fn",
  "verdict": "INDEX_STRUCTURE_PASS_METADATA_ONLY"
}
```

**L0_INDEX_JSON=PASS** from actual remote Hub metadata;
safetensors header dtype/shape, BF16 scalar dtype, file hashes,
source/provenance equality, model data, one-GB10 TP1 loader compatibility,
functional quality and strict NVIDIA RM stability **NOT_VERIFIED**.
Do not declare full checkpoint/tensor qualification or enable
`lychee888` in the installer. No model download or GPU start occurred.

## Acceptance and next boundary

```text
A5_REAL_DGX_PREVIEWS=PASS
L0_LYCHEE888_REAL_REMOTE_INDEX_JSON=PASS
M1_REAL_RUNTIME=NOT_QUALIFIED
M2_REAL_DESTRUCTIVE=NOT_RUN
M3_REAL_PROFILE_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
D0_INDEPENDENT_DISPOSABLE=NOT_GRANTED
PR_259=DRAFT_OPEN_UNMERGED
```

**Immediate next action:** B5 read-only go/no-go for the installed
legacy OrcaRouter baseline, with its release-specific managed
start/commit/rollback mechanics and explicit owner decision on
retention/loss of exact stopped predecessor Docker container ID.
The old immutable service runner's successful commit deletes the
old rollback Docker object, and ordinary rollback can restart
the stopped predecessor. Neither A5 nor L0 authorizes silently
crossing that boundary. Keep `MONITOR_PROTECT=1` and
`MONITOR_ENABLED=1`. Actual model start requires separately bounded
permission and strict RM observation.
