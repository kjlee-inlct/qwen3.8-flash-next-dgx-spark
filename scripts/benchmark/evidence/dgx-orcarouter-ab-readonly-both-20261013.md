# Actual DGX OrcaRouter A/B read-only preflight — 2026-10-13

**Evidence class:** ACTUAL_DGX_OPERATOR_PASTED_OUTPUT / READ_ONLY.
**Physical source:** exact detached worktree SHA
`980e1001ed90ee0b08b14dfddcf26797909e10c0`.
The operator executed the following two wizard checks sequentially:

```bash
for CHOICE in 6 7; do
  LOG="$HOME/dgx-ab-preflight-${CHOICE}-$(date +%Y%m%d-%H%M%S).log"
  set +e
  printf '6\n%s\n%s\n' "$CHOICE" "$OLD_ID" | ./install.sh --dry-run 2>&1 | tee "$LOG"
  RC=${PIPESTATUS[1]}
  set -e
  echo "AB_PREFLIGHT_CHOICE=$CHOICE"
  echo "AB_PREFLIGHT_RC=$RC"
  echo "AB_PREFLIGHT_LOG=$LOG"
done
```

Both wizard starts showed: installed profile `orcarouter`,
management menu 6, submenus 6/7. Exact observed values:

| Field | Legacy A | v0.29 B |
| --- | --- | --- |
| `AB_PREFLIGHT` | `PASS_READ_ONLY` | `PASS_READ_ONLY` |
| `AB_PREFLIGHT_CHOICE` | 6 | 7 |
| `AB_PREFLIGHT_RC` | 0 | 0 |
| `AB_VARIANT` | `legacy` | `v029` |
| `AB_IMAGE` | `vllm-skinny-tp1:v1` | `vllm-orcarouter-v029:v1` |
| `AB_IMAGE_ID` | `sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4` | `sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734` |
| `AB_OLD_DOCKER_ID` | `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24` | same |
| `AB_MANIFEST_SHA256` | `68d56e776214d8df25bd98c632d9749e5e174c3b9f5c671b2db080035d582f0f` | same |
| `AB_RELEASE` | `/home/inlc/.local/share/qwen38-spark/releases/ff67bab3c94d6992f61b9535836df97f03b9c022` | same |
| `AB_TRIAL_PORT` | `127.0.0.1:18888` | same |
| `AB_MODEL_START` | `NOT_PERFORMED` | `NOT_PERFORMED` |
| `AB_HOST_RM_QUALIFICATION` | `NOT_PERFORMED` | `NOT_PERFORMED` |
| `AB_BENCHMARK` | `NOT_MEASURED` | `NOT_MEASURED` |

Physical local A log reported:
`/home/inlc/dgx-ab-preflight-6-20261013-171811.log`.
B final `AB_PREFLIGHT_LOG=...` line and final outer-loop
`OLD_DOCKER_UNCHANGED=YES`/
`INSTALL_MANIFEST_UNCHANGED=YES` markers were **not included in the
pasted output**. The matching old Docker ID, manifest checksum and
release are observed within both source-verified read-only checks;
do not invent absent log path or a separate external after-run check.

**Scope:** This evidence validates pre-start admission only. Neither
image was started, a model served, an API request handled, a strict
NVIDIA RM host observation completed, or any llama-benchy measured.
No Docker/image/model deletion, snapshot cleanup, release transition,
PR merge or benchmark was approved. Preserve old predecessor ID and
the current checkpoint for this test only (not a permanent
no-delete policy). **Source work should harden runtime watchdog
exit/error handling before a physical GPU launch**. Run a distinct
exact-SHA, read-only candidate launch review and obtain owner
approval before invoking wizard menu 6 / start actions 2 or 3.
