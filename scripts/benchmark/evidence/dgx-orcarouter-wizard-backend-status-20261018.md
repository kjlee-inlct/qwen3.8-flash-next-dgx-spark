# ACTUAL DGX Wizard OrcaRouter backend qualification screen — 2026-10-18

**Source:** operator-pasted actual DGX `wizard.sh` interactive terminal,
not a CI synthetic test. No `git rev-parse HEAD` was included in this
terminal excerpt; do not claim the DGX was on a particular commit.
The shown screen implements the nested route introduced in
source `7ae1608a555228406c8220f71ed684a6828c9219`, whose
Push and PR GitHub CI both passed.

## Main-menu physical observation

```text
Qwen3.8 Flash Next — DGX Spark Manager
Manifest: valid (phase=complete)
Profile : orcarouter
Image   : vllm-skinny-tp1:v1
Runtime : NOT_PROBED (use Diagnostics / Runtime menu)
```

**Critical discrepancy from earlier source-only wording:**
the actual installed **manifest image** was
`vllm-skinny-tp1:v1`, which is the legacy skinny TP1 image
reference, **NOT** `vllm-orcarouter-v029:v1`. The candidate
registry's v0.29 implementation entry must never be displayed
as the currently installed or running backend. Manifest-image
identity is not proof a container with that image is currently
running or serving correctly; main menu explicitly said
`Runtime : NOT_PROBED`.

## Operator navigation and read-only result

Physical operator entered:
Model management `3` -> Candidate metadata `7` ->
OrcaRouter backend qualification `5`. Screen returned:

```text
OrcaRouter backend compatibility / 실행 백엔드 호환성
Registry configured backend: vllm-orcarouter-v029:v1 (implementation entry exists).
A registry entry does not prove the currently installed runtime is READY.
Official ARM64 C: image digest/package versions verified; CPU-only CLI help failed before printing options.
Failure: DeviceConfig could not infer GPU type in deliberately GPU-hidden probe.
CLI options, PLE, KV16GiB, MTP, model READY and host stability remain UNQUALIFIED.
Official C cannot be selected for ordinary install/switch; historical A/B preserved.
ORCAROUTER_PROFILE=orcarouter
ORCAROUTER_V029_BACKEND=REGISTRY_IMPLEMENTED_NOT_LIVE_ATTESTED_HERE
ORCAROUTER_OFFICIAL_ARM64_C=BLOCKED_PRE_RUNTIME_DEVICE_INFERENCE_CPU_ONLY
ORCAROUTER_OFFICIAL_ARM64_C_INSTALL_SWITCH=DISABLED_UNQUALIFIED
WIZARD_MUTATION=NONE
```

After this output the Wizard safely returned to the parent
Candidate metadata menu and remained at its selection prompt.
The tested route is interactive/read-only. No source evidence
supports a new Docker create/start/stop, GPU load, service change,
model download/deletion, benchmark or runtime READY claim.
Do not infer all protected A/B Docker IDs were independently
rechecked by this particular Wizard screen: the previous exact-ID
checks are separate physical observations.

## Corrective source work following this physical receipt

The stored installed manifest and registry status were conflated
at the presentation level. Subsequent GitHub source now uses
`wizard_read_manifest` (existing strict
`scripts/lib/state_file.py install-maintenance` parser; never
source arbitrary `install.env`) in the read-only backend view.
New output distinguishes `ORCAROUTER_MANIFEST_STATE`,
`ORCAROUTER_CONFIGURED_PROFILE`, `ORCAROUTER_CONFIGURED_IMAGE`,
`ORCAROUTER_CONFIGURED_VARIANT`,
`ORCAROUTER_LIVE_RUNTIME=NOT_PROBED` and the separate v0.29
registry candidate. Exact known manifest image
`vllm-skinny-tp1:v1` is labeled
`LEGACY_SKINNY_MANIFEST_IMAGE`; unknown/invalid/missing
manifests remain unclassified. C remains disabled.

New synthetic test file
`tests/test_orcarouter_wizard_installed_backend.py` covers
legacy, v0.29, custom, symlink/invalid and absent manifests.
**Source-only until CI on the final SHA and owner DGX sync**;
the newly corrected read-only output has NOT yet been seen
on the physical DGX.

## Later physical DGX confirmation: corrected configured-versus-registry UI actually rendered

The owner posted a **second actual DGX Wizard backend-screen output** after the source-side repair. This physical output explicitly confirmed that the strict installed-manifest result and registry candidate are shown separately:

```text
OrcaRouter backend compatibility / 실행 백엔드 호환성
P0: choose model and backend through the install/switch Wizard after qualification.
Configured in installed manifest / 설치 매니페스트: profile=orcarouter, image=vllm-skinny-tp1:v1
Configured variant / 기록된 백엔드: LEGACY_SKINNY_MANIFEST_IMAGE
Configured image is NOT evidence that any runtime is currently running or READY.
Registry default candidate / 레지스트리 기본 후보: vllm-orcarouter-v029:v1
Registry candidate differs from installed configuration unless exact image names match.
Official ARM64 C: pinned image/packages verified, but CLI help failed before options were printed.
Cause: DeviceConfig could not infer GPU type in the deliberately GPU-hidden CPU-only probe.
C options, PLE, KV16GiB, MTP, model READY and host stability remain UNQUALIFIED.
Official C install/switch is DISABLED. Protected managed/A/B Docker objects are not changed.
Saved C diagnostic / 저장 로그: Advanced -> Official ARM64 C saved CLI result (read-only).
ORCAROUTER_PROFILE=orcarouter
ORCAROUTER_MANIFEST_STATE=valid
ORCAROUTER_CONFIGURED_PROFILE=orcarouter
ORCAROUTER_CONFIGURED_IMAGE=vllm-skinny-tp1:v1
ORCAROUTER_CONFIGURED_VARIANT=LEGACY_SKINNY_MANIFEST_IMAGE
ORCAROUTER_LIVE_RUNTIME=NOT_PROBED
ORCAROUTER_V029_BACKEND=REGISTRY_IMPLEMENTED_NOT_LIVE_ATTESTED_HERE
ORCAROUTER_OFFICIAL_ARM64_C=BLOCKED_PRE_RUNTIME_DEVICE_INFERENCE_CPU_ONLY
ORCAROUTER_OFFICIAL_ARM64_C_INSTALL_SWITCH=DISABLED_UNQUALIFIED
WIZARD_MUTATION=NONE
```

**Physical acceptance now:** exact configured manifest image and version classification, distinct registry candidate, unqualified official C and read-only/no-mutation marker were visually observed on real DGX. The prior note saying this corrective screen was source-only is **superseded** by this second physical evidence.

**Remaining limits:** operator did not paste a `git rev-parse HEAD` in the second screen, so an exact physical Git SHA is **NOT ATTESTED** by this snippet, although the strings match the earlier source changes. This screen does not query running Docker, infer API READY, prove any image's loaded weights or show actually completed model switching. Old managed/A/B Docker identities were not independently rechecked in this UI turn.
