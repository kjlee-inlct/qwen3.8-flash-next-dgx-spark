# mazinb benchmark readiness: exact-ID admission before any live start

## Physical DGX result — 2026-10-14 (A and B both historical)

The owner entered Wizard -> Benchmark -> 4. Actual Docker status was:

- `qwen38-mazinb-kv-a`: **exited**, exit **1**, OOMKilled **false**,
  old start `2026-10-02T12:15:53Z`, KV **24 GiB**.
- `qwen38-mazinb-kv-b`: **exited**, exit **0**, OOMKilled **false**,
  old start `2026-10-02T11:45:40Z`, KV **16 GiB**.
- Both used image tag `vllm-orcarouter-v029:v1`; managed service
  inactive and original canonical container exited.

This is historical metadata, **not** a new DGX model run and **not**
proof that B reached READY or passed host stability. Review the real
monitor/runtime-stop/kernel evidence before citing an outcome.

The evidence UX initially rejected input `2` because it accepted
only literal A/B. Corrected Wizard submenu **5: Evidence** now presents
**1=A, 2=B, 3=both, 0=back** and still accepts A/B shortcuts.
The corrected fresh-B admission menu **2** detects old B *before*
requesting full predecessor ID and explains it cannot reuse the
historical case name. No cleanup will be performed or requested to
bypass this gate. A new model launch needs a uniquely named, protected
M1 candidate instance and lifecycle recovery.

**Physically qualified now:** historical evidence review AND M1 read-only
preflight. M1 live-start is source-implemented but not physically
qualified; actual llama-benchy NOT_MEASURED, Docker cleanup forbidden.
The operator continues through `wizard.sh` only.

### Historical KV A/B evidence reviewed — 2026-10-14 (physical DGX)

Read-only Wizard **5 -> 5 -> 3** reviewed both **2026-10-02** experiments:
A / 24 GiB recorded five consecutive low-memory warnings, protected
stop at 21:27:23 KST, `STOP_REASON=memory-protection`, Docker exit 1,
`OOMKilled=false`; no matching filtered kernel RM/OOM lines displayed.
B / 16 GiB showed completed startup, **HTTP 200** from `/health` and
`/v1/models` at 20:57:42 KST, approximately **180 seconds** of
subsequent operation followed by orderly shutdown at 21:00:42 KST,
Docker exit 0, no protected-stop marker, and no matching filtered
RM/OOM lines. These observations support a historical **16 GiB safety
baseline**, **not** throughput or new live qualification.

The displayed B evidence lacks the raw `/v1/models` JSON identity and
the old runner's final RESULT line; do not invent an unconditional
FUNCTIONAL_PASS / HOST-STABILITY_PASS. Its `/v1/models` HTTP 200 and
the runner source's strict ID check are distinct pieces of evidence.
A's `KeyboardInterrupt: terminated` happened immediately after
protective stop and is not proof of a separate model root error.

Details and terminal-log SHA-256:
[`dgx-mazinb-kv-ab-wizard-readonly-20261014.md`](../scripts/benchmark/evidence/dgx-mazinb-kv-ab-wizard-readonly-20261014.md).

**Both A and B Docker objects still exist and are stopped.** A fresh
candidate must use a distinct M1-owned name with isolated exact-ID
watchdog and SSH-interruption recovery; there is no reason to delete
either historical trial to make room for it. The managed legacy
OrcaRouter image `vllm-skinny-tp1:v1` remains unchanged.

**Caution from pre-existing repository evidence:** [`mazinb-kv-ab-20261002.md`](../scripts/benchmark/evidence/mazinb-kv-ab-20261002.md) explicitly records two A-side NVIDIA RM `NV_ERR_NO_MEMORY` signals and the subsequent managed 16 GiB revalidation with one such RM event despite functional readiness. The fresh Wizard evidence menu's filtered kernel window being empty is not evidence that these archived RM findings did not occur. Historical isolated B PASS never guarantees strict future host RM PASS.

### ACTUAL DGX M1 read-only admission — 2026-10-14 PASS

On verified SHA `2dfa74dacedfe50fe1c28ca309939ed9d61b8123`,
the owner used root Wizard Benchmark **6 plan**, **7 status**, and
**8 read-only preflight**. Plan showed KV 16 GiB and localhost 18889;
`M1_SESSION=ABSENT` preceded the preflight. The full old Docker ID
was confirmed and sudo kernel log read access approved.

Output: `M1_PREFLIGHT=PASS_READ_ONLY`, old container
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`,
immutable release `ff67bab3c94d6992f61b9535836df97f03b9c022`,
image ID `sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734`,
and `M1_CANDIDATE_START=NOT_PERFORMED`.

Physical evidence: [M1 read-only preflight](../scripts/benchmark/evidence/dgx-mazinb-m1-physical-readonly-preflight-20261014.md).

After this physical result, source was hardened to isolate each candidate's
HOME and vLLM/FlashInfer caches; re-check the newer SHA and pass CI before
an explicitly owner-approved live run. The preflight is not proof
of M1 READY, post-ready soak, strict live RM stability or llama-benchy.
### Second M1 read-only preflight — repeat PASS, no new model (2026-10-14)

User again selected Wizard Benchmark 5 -> 8 and received
`M1_PREFLIGHT=PASS_READ_ONLY`, unchanged old Docker ID, release and
image ID, and `M1_CANDIDATE_START=NOT_PERFORMED`. The follow-up
5 -> 5 -> 0 exited the historical evidence picker without an A/B
re-inspection. The second terminal excerpt does not itself show a
Git HEAD verification; re-verify exact SHA before first opt-in live
launch. Source CI for the cache-isolation change passed; actual
GPU load and any new M1 host-stability verdict remain NOT_RUN.
## Priority and sequencing (2026-10-14)

The next **actual DGX model test** should be mazinb; finishing the entire
`install.sh` installer-only refactor is **not** a prerequisite for a safe
isolated run. Current installed predecessor and evidence must survive. The
previous `mazinb-kv-ab.sh preflight` already passed once; that is an
historical read-only result, not current host acceptance.

### Stage M0 — new read-only identity/admission gate (implemented)

**Operator entry point is only `./wizard.sh`** (top-level menu 5: Benchmark).
Use submenu **4: Historical A/B status**, **5: Historical evidence A/B**
(1=A, 2=B, 3=both). Because historical B also exists, fresh-B submenu
**2: Guarded admission** is blocked until a separately named M1 path exists. The wizard itself inspects and displays
the original managed Docker ID, requires exact user acknowledgement, and
requires explicit default-NO consent for evidence review and read-only admission.
The script `scripts/wizard/mazinb-admission.sh` is an internal testable helper,
**not** an operator entry point. Never instruct an operator to use it directly
or invoke the legacy A/B runner directly.

The operator must supply the *currently inspected* full 64-character Docker
ID of the stopped predecessor; do not reuse an old snapshot without checking.
The helper:

- strictly parses the installation manifest without executing its content;
- requires installed OrcaRouter predecessor, managed service and monitor
  protection ON, exact stopped/clean Docker state and immutable image ID;
- checks operation-lock availability, interruption markers, systemd inactivity,
  immutable release pointer and the isolated B Docker namespace;
- accepts a *stopped* historical A container only after displaying the evidence
  through Wizard, exact 64-character A ID acknowledgement, and verification
  of its experiment and monitor log files; does not accept a running A,
  an occupied target B, or missing/unsafe historical evidence;
- reruns mazinb's existing preflight only after old-Docker identity is proved;
- rechecks predecessor identity, manifest SHA and release pointer for drift;
- makes **no** Docker lifecycle, systemd, checkpoint, release or manifest changes.

`MAZINB_ADMISSION=PASS_READ_ONLY` is a positive admission *snapshot*, **not**
authorization to start a model and **not** FUNCTIONAL/READY/HOST-STABILITY
or performance evidence. A failure is an actionable BLOCK, never a reason to
remove an old experimental container or disable protection automatically.

### Actual DGX feedback — 2026-10-14

The first physical attempt at the internal helper reached
`MAZINB_ADMISSION=BLOCKED reason=prior mazinb experiment object exists:
qwen38-mazinb-kv-a`. This **proves existence, not running state or
recoverability**. The helper's blanket refusal was too broad; it has been
replaced by reviewed, evidence-preserving historical A acceptance. Existing
A/B containers are never automatically removed. The operator should review
A via Wizard and re-run admission via Wizard. No actual model was started.

The previous operator used `set -Eeuo pipefail` interactively; any admission
nonzero exit can terminate that interactive SSH shell. Launch the Wizard with
`bash /path/to/verified-worktree/wizard.sh` from a normal shell instead,
without setting `errexit` globally.

### Stage M1 — protected isolated candidate runtime (SOURCE IMPLEMENTED; ACTUAL DGX NOT QUALIFIED)

A new controller (`scripts/runtime/mazinb-m1.py`) is source-implemented,
with plan/status/preflight and explicitly gated Wizard live-start menu.
It must still pass actual DGX read-only preflight and separately owner-
approved startup/rollback acceptance before any model success claim.
[New Wizard M1 guide](MAZINB-M1-WIZARD.md) details the safety contract.
The new controller is separate from the old KV A/B runner and is designed to
that holds exactly one lifecycle lock throughout setup, model start,
readiness, identity, benchmark and safe stop. Its protected start must
preserve exact managed Docker ID/status/image, require restart-policy=no
and loopback-only port, arm/watchdog **before** start, and treat monitor
loss as a candidate stop/failure. Maintain an explicit evidence journal
through SSH interruption. Prior mazinb experiments are historical
reference data, not permission to reuse or remove their containers.

**Why not launch with the existing `mazinb-kv-ab.sh run B`?** It
automatically stops the candidate at the end of its 180-second soak,
so it does not provide the required uninterrupted READY model for
llama-benchy; changing that stop behavior without lifecycle recovery
and exact-ID safety tests would violate the preservation contract.

### Stage M2 — actual benchmark (NOT PERFORMED)

The source-side B-terminal `scripts/benchmark/m1-benchmark-lock.sh` option now shares the lifecycle lock while holding an
exclusive benchmark lock and checking a pinned active M1 session before and
after the workload. This does not itself install or execute llama-benchy.

Once M1 is qualified by synthetic tests and DGX admission succeeds,
run one supervised smoke request, verify `/health` and exact
`/v1/models`, independently classify strict NVIDIA RM/monitor signals,
then run pinned `eugr/llama-benchy` with reproducible PP/TG,
TTFT/TTFR/context/concurrency workloads. Preserve original JSON,
Markdown, source/release/model/image/bench upstream SHAs, checksum,
logs, and a verified **off-host** copy before considering cleanup.

No current mazinb metrics can be reported. Any protection stop is
FUNCTIONAL incomplete and HOST-STABILITY inconclusive unless strict
RM failure is observed; a watchdog action is **not** automatically
`HOST-STABILITY PASS` or a proven RM OOM.

### Stage M3 — H6 and optional reclaim

Preserve the mazinb source until whole-chain H3/H4/H5/H6 reproduction
is validated. Only owner-approved, dependency-aware and independently
backed-up assets may be reclaimed. No deletion approval is implied.

## Acceptance ledger

| Gate | Status |
| --- | --- |
| Existing 2026-10-13 mazinb KV preflight | historical PASS |
| Historical A/B status and evidence in Wizard | actual-DGX historical review completed; A protect-stop, B HTTP READY observed |
| Legacy admission helper source | implemented; old B collision blocks this fixed-name path; new M1 has unique names |
| M1 protected stay-READY controller | SOURCE IMPLEMENTED; read-only DGX preflight PASS; live READY NOT_RUN |
| Historical B API HTTP readiness | observed 2026-10-02; exact served-name JSON absent from pasted output |
| ACTUAL DGX M1 read-only preflight | PASS_READ_ONLY on SHA 2dfa74d, no candidate started |
| Fresh M1 mazinb READY / served identity | NOT_MEASURED |
| Historical A/B filtered RM/monitor window | A protect-stop; B no protect stop, no matching RM lines; full current-host acceptance pending |
| Fresh M1 strict RM host stability | NOT_MEASURED |
| llama-benchy real data and external backup | NOT_MEASURED |
| Managed Docker / swap / release modification | NOT_PERFORMED |
