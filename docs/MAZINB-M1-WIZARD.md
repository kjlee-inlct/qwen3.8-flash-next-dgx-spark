# mazinb M1: Wizard-owned isolated session — source implementation

**2026-10-14** · Target DGX Spark / Qwen3.8 Flash Next · Branch
`feature/wizard-modular-phase1-20261014` / Draft PR #261.

## Implementation status and non-negotiable limits

The code implements an **opt-in** isolated M1 path under root `wizard.sh` ->
**5 Benchmark** -> **6 plan / 7 status / 8 current-host read-only preflight /
9 experimental physical start**. Menu 9 defaults to **NO**, requires
the complete inspected managed-Docker 64-character ID, a second exact
`START_MAZINB_16G` phrase, and sudo kernel evidence access. There is
**no automatic model start** from this repository change or from CI.

The source implementation is **NOT ACTUAL_DGX_LIVE_QUALIFIED**.
**Actual DGX M1 read-only preflight PASS** on 2026-10-14 at source SHA
`2dfa74dacedfe50fe1c28ca309939ed9d61b8123`, with protected Docker
ID and immutable release/image. Live launch, READY and llama-benchy remain
NOT_RUN; the next cache-isolation commit needs its own Git SHA verification
and source CI before any opt-in GPU load. Failures must be
documented without deleting prior A/B, models, managed Docker or evidence.

An M1 candidate is uniquely named
`qwen38-mazinb-m1-YYYYMMDDHHMMSS-8hex`, does NOT reuse either old
`qwen38-mazinb-kv-a` / `qwen38-mazinb-kv-b` and does not reuse
`qwen38-flash-next`. It runs on loopback **127.0.0.1:18889**, with
`vllm-orcarouter-v029:v1`, KV pool **16 GiB**, `MAXLEN=262144`,
MTP k=2, `MAXSEQS=3`, exact QSA, restart policy `no`.
Fresh attempts are independently named; all previous containers and
record JSON files remain preserved. The subsequent source hardening gives
each candidate a unique per-trial HOME for vLLM and FlashInfer host caches
rather than touching the user's existing canonical/experiment cache files.

See [physical M1 preflight evidence](../scripts/benchmark/evidence/dgx-mazinb-m1-physical-readonly-preflight-20261014.md).

## Safety contract — inspect code before first physical attempt

1. `preflight` validates strictly parsed managed manifest, completed
   OrcaRouter, monitor/protect ON, exact unchanged stopped old Docker
   and immutable image, immutable release, inactive systemd, idle
   lifecycle transaction, present mazinb checkpoint+image+swap, unique
   loopback port, no other *running* mazinb historical/M1 trial and
   sudo-available kernel log, then revalidates old identity.
2. The model is provisioned with `TRIAL_CREATE_ONLY=1`; the helper
   enforces a unique name and mazinb-specific Docker provenance labels
   and uses `docker create`, not `docker run`.
3. The independent exact-ID `monitor-runtime.sh` is detached,
   **armed before Docker start**, writes arm/heartbeat/stop evidence and
   protects memory. A monitor *catchable* exit stops only the exact
   labeled candidate. Its hard TTL is **7200 s**; process/host SIGKILL
   and power loss remain inherent unattended-recovery limitations
   requiring physical verification.
4. The foreground M1 supervisor holds a **shared lifecycle lock**
   for its entire session; lifecycle mutation commands require
   **exclusive** lock and cannot overlap. A separate B-terminal
   benchmark uses the explicit `m1-benchmark-lock.sh`
   shared-lifecycle / exclusive-benchmark pair after independent
   source-level `bench-admission` identity and current-host checks.
5. Before READY: strict `/health` HTTP 200, *exact one* expected
   `/v1/models` ID and **180-second post-ready soak**. Any sampled
   `NV_ERR_NO_MEMORY` / `_memdescAllocInternal`, stale watchdog
   heartbeat, triggered protection, identity drift, stop or failing
   sudo kernel collection fails closed and stops only the new candidate.
6. After READY: Terminal A remains supervising, repeatedly checking
   Docker/monitor/kernel/immutable managed identity. **Type STOP**
   to end. STOP is deferred if Terminal B holds the benchmark lock.
   Session ends automatically no later than **5400 s of post-start
   supervision**, under the 7200-second watchdog maximum.
7. On normal STOP/error/interactive SIGHUP or SIGTERM, only the
   **exact pinned candidate ID** may be stopped. No `docker rm`,
   `docker image rm`, `docker system prune`, swap changes or
   protected managed service actions are implemented. Records are
   preserved under `~/.local/state/qwen38-spark/mazinb-m1/`.

**Limitations:** The Python supervisor and detached watchdog are
not equivalent to a boot-persistent independent systemd service.
If *both* are SIGKILLed, the host resets or Docker becomes unreachable,
the process-local guarantee cannot apply. A later separate recovery
implementation must classify orphan/stale sessions and enforce a
reboot-safe policy before declaring unattended operation qualified.
Do not treat M1 as proof of strict host stability without **physical**
qualification and complete NVIDIA RM inspection.

## Actual DGX read-only sequence — operator terminal A only

Verify the source tree SHA and run *only* the root Wizard.
In the Benchmark submenu choose **6** to review the plan,
**7** to inspect preserved active M1 state and **8** for the exact
managed predecessor ID/read-only M1 preflight. **Do not select 9**
until the verified preflight and owner-authorized physical window.

When the owner *does* explicitly select **9**, the prompt describes
real GPU load, defaults to NO and requires exact predecessor identity
and typed start phrase. Terminal A must remain connected and supervises
the candidate until it displays `M1_READY_FOR_BENCH`. No other
lifecycle, model-switch, uninstall, swap, prune or cleanup actions
may run during this session.

## Terminal B — after actual M1 READY only

Do not infer benchmark eligibility from historical 2026-10-02 trial B.
The B-terminal execution wrapper is:

```bash
bash scripts/wizard/m1-benchmark-lock.sh -- COMMAND [ARGS...]
```

`COMMAND` must be the separately verified pinned `llama-benchy`
invocation against `http://127.0.0.1:18889` for the exact
`mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4` ID. No unverified
upstream CLI flags are asserted in this document. The wrapper checks
the active session and revalidates it after the command. Terminal A
rejects voluntary STOP while B holds its exclusive benchmark lock.
The physical approval for any benchmark is separate from merely
starting M1; raw JSON/Markdown, SHA256, memory and kernel evidence,
source/model/image hashes and verified off-host backup remain mandatory.

## Historical warning — controlled vs managed B

The older source
`scripts/benchmark/evidence/mazinb-kv-ab-20261002.md`
explicitly states historical *isolated* 16 GiB B achieved
**FUNCTIONAL PASS / HOST-STABILITY PASS**, with API identity and
180-second soak. It also says a subsequent **managed** 16 GiB run
was **FUNCTIONAL PASS / HOST-STABILITY FAIL** after a startup
`NV_ERR_NO_MEMORY` event. This controlled-run success is *not*
a universal 16 GiB host stability guarantee. Strict RM policy
must remain on during M1.

## Acceptance ledger

| Gate | Current classification |
| --- | --- |
| New names/create-only labels/source controller | SOURCE IMPLEMENTED, CI validation required |
| Safe default NO / two-step live approval | SOURCE IMPLEMENTED |
| Foreground shared lifecycle lock / benchmark exclusive lock | SOURCE IMPLEMENTED |
| Exact-ID detached watchdog with bounded TTL | SOURCE IMPLEMENTED; boot-persistent guarantee NOT_PROVEN |
| Actual DGX M1 read-only preflight | PASS_READ_ONLY on original SHA 2dfa74d; retest later hardening commit |
| Actual DGX new M1 model start and exact API READY | NOT_RUN |
| Actual DGX fresh 180s soak / strict RM stability | NOT_RUN |
| Pinned llama-benchy JSON/report/SHA256/off-host backup | NOT_MEASURED / NOT_VERIFIED |
| A/B historical and managed Docker removal | FORBIDDEN / NOT_PERFORMED |
