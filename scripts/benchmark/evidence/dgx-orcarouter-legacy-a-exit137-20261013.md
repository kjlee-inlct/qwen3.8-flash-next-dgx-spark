# Physical DGX OrcaRouter Legacy A failure — 2026-10-13

**ACTUAL_DGX / operator-pasted diagnostic**; source SHA for actual
launch `48c517357cef2182be986c298a86ddfa1f4c74b0`.
This extends [first real startup](dgx-orcarouter-legacy-a-actual-start-20261013.md).
Status is **DOCKER_STARTED_THEN_EXITED_137 / MODEL_NOT_READY**,
not a successful model or llama-benchy result.

| Evidence | Observation |
| --- | --- |
| Original managed Docker | `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`; exited, OOMKilled=false, ExitCode=0, same image |
| New Legacy A Docker | `57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56`; exited, ExitCode=137, OOMKilled=false |
| Image ID both | `sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4` |
| Watchdog | `WATCHDOG_AGE_SECONDS=1028`; armed ID equals new candidate |
| API | `/health` & `/v1/models` Connection refused |
| Runtime | vLLM `v0.1.dev20073+g8e685d198`, CPU PLE offload, MTP=2, managed KV 16 GiB |
| Weight loading | 170.88 GiB on EXT4, 38.68 GiB RAM available when load began; only ~2/18 main, ~1/18 PLE shard loading observed |
| After exit | `free -h`: ~118 GiB available RAM, ~1 GiB used swap; NVIDIA GPU idle |
| Kernel journal grep | no RM/Xid/OOM matches in displayed excerpt, not complete proof of absence |
| llama-benchy | **NOT_MEASURED** |

**Root cause not established.** ExitCode 137 indicates SIGKILL,
not necessarily Docker OOM. Docker `OOMKilled=false`
contradicts asserting recorded Docker OOM.
The captured `monitor.log` tail includes a long copy of
vLLM loader logs; monitor source only copies such logs into its
output after `PROTECT stopping` when low non-CMA
margin repeats, making protective stop a **strong hypothesis**,
not confirmed. A Docker stop timeout can escalate to SIGKILL.
No `monitor/runtime-stop.env` or initial monitor warning
lines were provided, so do not claim memory-protection is proven.

Before any B trial, collect the following **read-only**:
```bash
TRIAL="$HOME/.local/state/qwen38-spark/ab-trials/legacy-1791881886"
docker inspect --format '{{.Id}}|{{.State.Status}}|{{.State.StartedAt}}|{{.State.FinishedAt}}|{{.State.ExitCode}}|{{.State.OOMKilled}}' 57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56
grep -nE 'monitor started|WARNING memory margin|PROTECT stopping|TRIAL WATCHDOG EXIT|TRIAL_RUNTIME_LIMIT|HEARTBEAT healthy|ERROR' "$TRIAL/monitor.log" | tail -n 100 || true
if [[ -f "$TRIAL/monitor/runtime-stop.env" ]]; then cat "$TRIAL/monitor/runtime-stop.env"; else echo STOP_REASON_ABSENT; fi
cat "$TRIAL/record.json"
```

Stop/abort/deletion and new model installs are **not authorized**
by this document. Never substitute raw Docker START, manual
monitor disabling, or managed service restart for the wizard.
The evidence must remain for diagnostics, PR #259 Draft.
