# D0 parent mount / Docker endpoint and Git observation hardening — 2026-10-12

## Provenance and exact CI

GitHub-only source-fixture evidence for the D0 read-only collector. **No independently owned disposable host or protected DGX Spark was inspected or mutated.**

- Branch: `feat/h38-managed-integration`
- Initial hardening source SHA: `4dfc2aed238ce96be0b5f3970256b8a2ce8cadf8`
- [GitHub CI #38266470002](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38266470002): **SUCCESS, 828/828 full Python tests, 77/77 bounded synthetic tests**, Bash syntax/ShellCheck/Python compile/whitespace PASS
- Follow-up Git index observation source SHA: `b65c0142340d90d681c8f82d05294bb72d813687`
- [GitHub CI #38267015272](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38267015272): **SUCCESS, 829/829 full Python tests, 77/77 bounded synthetic**, ShellCheck/Bash/Python compilation/whitespace PASS. The new `test_git_optional_locks_disabled_for_all_readonly_probes` passed.
- Previously existing 12 fixture methods + four new trust-boundary methods + one Git-lock method = **17/17 D0 read-only crosscheck synthetic methods** in full CI only. The bounded 77-case DGX-oriented verifier remains unchanged.
- **Latest actual DGX-local synthetic source:** `1283b1a9252f1ff53d51659049ca42f9449e5ccd`, **77/77 PASS**. The newer D0 code has **NOT** run locally on the DGX.

## Defect 1: parent mount coverage

The initial read-only crosscheck rejected mounts **at or beneath** each proposed disposable work/model/log root, but did not reject a bind mount on a non-root ancestor such as `/srv`. That could make all three proposed roots aliases of an externally mounted filesystem while the earlier scanner incorrectly reported no mounts inside them.

The new check rejects a mountpoint that overlaps a candidate root in **either direction** (excluding the filesystem's unavoidable `/` root mount), before accessing any Docker daemon. A fixture exercises `/srv` above `/srv/d0-model` and proves fail-closed refusal before Docker commands.

## Defect 2: Docker context name was insufficient

The initial collector checked a Docker context name and daemon ID but did not inspect the context's actual endpoint. A non-default context can still point to a **shared** default Unix socket or to TCP/SSH remote Docker.

The new logic:
- Refuses populated `DOCKER_HOST`, `DOCKER_CONTEXT`, `DOCKER_TLS_VERIFY`, `DOCKER_CERT_PATH`, `DOCKER_CONFIG` and `DOCKER_API_VERSION` overrides before Docker commands.
- Performs a bounded, fixed-template context-endpoint read and allows only a **real, non-symlinked Unix socket**, refusing TCP/SSH, known default paths `/var/run/docker.sock` and `/run/docker.sock`, path traversal and socket aliases.
- Pins subsequent `docker info` / `docker ps -a` read-only invocations to the exact verified context using the Docker CLI's explicit `--context` flag.
- Exercises remote/default/aliased/unavailable sockets, environment override and positive pinned-command assertions in disposable mocked host fixtures.

**This is a stronger refusal rule, not proof of physical Docker isolation.** A private-looking socket may still proxy a protected daemon; source ownership and external user access require independent host/owner corroboration. Parent mount refusal does not establish remote/shared block-device provenance or mount namespace integrity.

## Defect 3: Git observation side effects

The collector's Git commands now set `GIT_OPTIONAL_LOCKS=0` to suppress optional index locking/index refresh during inspection, including `git status`. The new fixture regression checks this environment is supplied to all command probes. This does not constitute a full operating-system no-write sandbox.

## Admission and evidence interpretation

The positive collector report stays:
```text
scope=ON_HOST_READ_ONLY_ASSERTION_CROSSCHECK
independence=NOT_ATTESTED
d0_admission=NOT_GRANTED
d1_d5=NOT_AUTHORIZED
live_host_e2e=NOT_QUALIFIED
```

Protected machine-ID denyset and explicit independent-host acknowledgement remain mandatory before the observer contacts Docker. All input inventory/policy may still be forged; the read-only collector is not a trusted attestation authority or destructive test-run authorization.

```text
D0_OFFLINE_POLICY=IMPLEMENTED
D0_HOST_CROSSCHECK_SOURCE=HARDENED
D0_CROSSCHECK_FIXTURE_TESTS=PASS_17_OF_17
GITHUB_CI_38267015272=SUCCESS_829_FULL_77_SYNTHETIC
ACTUAL_DGX_LAST_SYNTHETIC=PASS_77_AT_1283B1A
INDEPENDENT_HOST_D0_OBSERVATION=NOT_RUN
D0_LIVE_ADMISSION=NOT_GRANTED
D1_D5=NOT_RUN
M1_HOST_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
HOST_STABILITY=INCONCLUSIVE
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN_UNMERGED
READY_FOR_REVIEW=BLOCKED
MERGE=BLOCKED
```

The documentation-only commit that introduces this evidence has a newer HEAD than the source run and must receive its own CI; the prior exact-source results must not be transferred without that check.
