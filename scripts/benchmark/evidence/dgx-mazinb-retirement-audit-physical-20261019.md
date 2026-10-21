# Actual DGX Spark — mazinb post-retirement full read-only audit

**Evidence origin:** owner-pasted terminal session received 2026-10-19 KST,
original capture label `붙여넣은 텍스트(1)(20261018-225631).txt`.
This is **physical owner console evidence**, not a synthetic CI transcript.
The original upload is preserved in the conversation; the following is
a bounded exact-key excerpt, not a fabricated benchmark/run.

## Exact source acquisition (actual)

```text
BRANCH="feature/wizard-modular-phase1-20261014"
EXPECTED="5164042ed5d784fe3469ad0207e4d8ecf8d5869f"
...
 * branch            feature/wizard-modular-phase1-20261014 -> FETCH_HEAD
   14a44f0..5164042  feature/wizard-modular-phase1-20261014 -> origin/feature/wizard-modular-phase1-20261014
업데이트 중 14a44f0..5164042
Fast-forward
SOURCE_SYNC=VERIFIED
```

The owner's shell checked branch equality, clean worktree,
FETCH_HEAD equality, `git merge --ff-only` and resulting
HEAD equality before opening `./wizard.sh`.
No proof of a later source HEAD is provided by this transcript.

## Wizard 3 → 6: independent completed-retirement audit (actual)

```text
MAZINB_DOCKER_EVIDENCE=ORIGINAL_AND_REPOSITORY_SHA256_PASS
MAZINB_DOCKER_JOURNAL=STOPPED_EXACT_ID
MAZINB_DOCKER_HYBRID_STAGES=POST_RETIREMENT_NOT_REQUIRED
MAZINB_AUDIT_ARCHIVE=PASS_EXACT_FIVE_INSPECT_AND_LOG_PAIRS_SHA256
MAZINB_AUDIT_ORIGINAL_AND_GITHUB_BENCHMARK=SHA256_PASS
MAZINB_AUDIT_ARCHIVE_PATH=/home/inlc/.local/state/qwen38-spark/retirement-archives/mazinb-docker-20261014T103718Z-7e238b9aeb
MAZINB_AUDIT_DOCKER=EXACT_FIVE_ABSENT_NO_OTHER_MAZINB
MAZINB_AUDIT_PROTECTED_DOCKER=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24
MAZINB_AUDIT_SHARED_VLLM_IMAGE=PRESENT_PRESERVED
MAZINB_AUDIT_SYSTEMD_SYSTEM_DEDICATED=ABSENT
MAZINB_AUDIT_SYSTEMD_USER_DEDICATED=ABSENT
MAZINB_AUDIT_SHARED_UNIT=qwen38-flash-next.service load=not-found active=inactive PRESERVE
MAZINB_AUDIT_SHARED_UNIT=qwen38-openwebui-proxy.socket load=not-found active=inactive PRESERVE
MAZINB_AUDIT_SHARED_UNIT=qwen38-openwebui-proxy.service load=not-found active=inactive PRESERVE
MAZINB_AUDIT_SYSTEMD=NO_DEDICATED_MAZINB_UNIT_SYSTEM_OR_USER
MAZINB_AUDIT_M1_PORT_18889=NO_LISTENER
MAZINB_AUDIT_SHARED_PORT_8888=NO_LISTENER_NOT_A_MAZINB_DELETION_TARGET
MAZINB_AUDIT_SHARED_PORT_8000=NO_LISTENER_NOT_A_MAZINB_DELETION_TARGET
MAZINB_AUDIT_SHARED_PORT_8001=NO_LISTENER_NOT_A_MAZINB_DELETION_TARGET
MAZINB_AUDIT_HOST_PROCESSES=NO_KNOWN_MAZINB_WORKER_OR_WATCHDOG
MAZINB_RETIREMENT_AUDIT=PASS_READ_ONLY_DEDICATED_ARTIFACTS_ABSENT
MAZINB_RETIREMENT_SHARED_RUNTIME_AND_PROXY=REPORTED_NOT_DELETED
MAZINB_RETIREMENT_HOST_MUTATION=NONE
```

Result is scoped to those checks; absence of a model-serving
port and stopped old Docker alone do not prove unrelated host
services are idle.

## Wizard 3 → 5: repeated destructive retirement refused (actual)

```text
MAZINB_DOCKER_RETIRE=BLOCKED_HISTORICAL_MARKER_REVIEW_REQUIRED
! Historical retirement marker exists; do not rerun exact-five deletion.
ℹ  Marker alone is not verified proof. Select Models 3 -> 6 for read-only full retirement audit.
```

This reflects the new no-repeat-delete guard operating physically;
the actual independent 3→6 audit is the evidence of completed retirement.

## Wizard 5 → 7: archived M1 journal (actual)

```text
M1_SESSION_PHASE=stopped
M1_SESSION_NAME=qwen38-mazinb-m1-20261014013811-16ced779
M1_CONTAINER_ID=7af3966f3d0cae79f8277eaf9ad003fb04c1e15ea01f86574c2d8eeac396e7a1
M1_RUNNING=False
M1_EXIT_CODE=0
M1_STATE_DIR=/home/inlc/.local/state/qwen38-spark/mazinb-m1
M1_DOCKER_REMOVED=YES_ARCHIVED
M1_DOCKER_ARCHIVE_PATH=/home/inlc/.local/state/qwen38-spark/retirement-archives/mazinb-docker-20261014T103718Z-7e238b9aeb
```

## Qualification boundary

The current mazinb checkpoint was previously inventoried as
`CHECKPOINT=absent` with no registered model container;
this exact session did not reinstall or start it.
The archived mazinb M1 benchmark (2026-10-14) remains MEASURED,
but these read-only operations are **not a second model start,
a live API check or a new performance measurement**.

No model/Docker deletion, weight download, GPU startup, service change
or PR merge was authorized/executed by this evidence.
The original managed OrcaRouter image/profile and archived research
outputs remain protected.
