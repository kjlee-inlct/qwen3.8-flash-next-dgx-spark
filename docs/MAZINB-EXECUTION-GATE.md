# mazinb benchmark readiness: exact-ID admission before any live start

## Priority and sequencing (2026-10-14)

The next **actual DGX model test** should be mazinb; finishing the entire
`install.sh` installer-only refactor is **not** a prerequisite for a safe
isolated run. Current installed predecessor and evidence must survive. The
previous `mazinb-kv-ab.sh preflight` already passed once; that is an
historical read-only result, not current host acceptance.

### Stage M0 — new read-only identity/admission gate (implemented)

**Operator entry point is only `./wizard.sh`** (Benchmark menu, choice 5).
Use submenu **4: Historical A/B status**, **5: Historical evidence A/B**,
then **2: Guarded mazinb B admission**. The wizard itself inspects and displays
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

### Stage M1 — protected isolated candidate runtime (NOT IMPLEMENTED)

Build and qualify a separate controller (not just the old KV A/B runner)
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
| Historical A review in Wizard | source implemented; exact-DGX review pending |\n| New admission script source | implemented, needs current exact-DGX snapshot |
| M1 protected stay-READY controller | NOT_IMPLEMENTED |
| Actual mazinb READY / served identity | NOT_MEASURED |
| Actual RM host stability | NOT_MEASURED |
| llama-benchy real data and external backup | NOT_MEASURED |
| Managed Docker / swap / release modification | NOT_PERFORMED |
