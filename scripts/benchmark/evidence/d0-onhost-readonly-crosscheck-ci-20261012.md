# Independent D0 host read-only cross-check — fixture CI evidence (2026-10-12)

## Provenance and unchanged host scope

This is **GitHub CPU fixture-only verification**, not evidence that a new real disposable host was inspected. No operation on the sole protected DGX Spark, host runtime, GPU, model, Docker service, swap, monitor protection or live systemd occurred.

- Branch: `feat/h38-managed-integration`
- Feature commit: `b6d3188f9dcf37393c5c1fd03b76f325ba501e32`
- Corrective test commit: `b99b510e89cc08d99d683dcbf77c75bb55941b2c`
- First [CI #38218386709](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38218386709): **FAIL**, 824 methods executed, one fixture failure; ShellCheck/Bash/compilation PASS. The test fake raised `AssertionError` for an unavailable Docker command, while actual subprocess execution failures raise `OSError` (or yield nonzero status). This was a test-stub representation mismatch, **not** a successful runtime qualification and not proof of the collector's safety.
- Corrective [CI #38218663210](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38218663210): **SUCCESS, 824/824 full Python, 77/77 bounded synthetic**, 17/17 profile-switch, ShellCheck/Bash syntax/Python compile/whitespace PASS. `test_docker_outage_fails_closed` passed.
- The new 12 read-only cross-check tests are in the full unit suite. They are **not in the operator's 77-method synthetic allowlist**.
- Latest actual DGX isolated synthetic acceptance remains **77/77 at `1283b1a9252f1ff53d51659049ca42f9449e5ccd`**, not at either new code SHA.

## Read-only cross-check design

The source-only `disposable-d0-readonly-crosscheck.py` extends the offline `disposable-d0-preflight.py` policy parser. The command requires `--policy`, `--inventory`, and an explicit `--ack-independent-disposable-host`. This flag **is not proof of independence**; the exact machine ID hash from `/etc/machine-id` must also match inventory and differ from the protected-machine denyset, checked **before host command execution**.

The inspector only reads the current checkout and host metadata using fixed read-only arguments (Git HEAD/origin/status; Docker context/info/container listing; systemd `show` for the explicit `qwen38-d0-*.service` unit), bounded output/timeouts, filesystem realpaths, and `/proc/self/mountinfo`. It rejects a dirty or mismatched Git checkout, unknown or protected daemon identity, an already present Docker container or target service unit, path alias/symlink drift and mounts directly within designated disposable roots. The tested command probes use injectable fixtures, not actual daemons. No commands that install, start, stop, remove or change host resources are present.

The successful JSON report contains only verification status tokens, not raw host IDs, raw mount names, service logs, credentials or Docker payload. It always includes:
```text
scope=ON_HOST_READ_ONLY_ASSERTION_CROSSCHECK
independence=NOT_ATTESTED
d0_admission=NOT_GRANTED
d1_d5=NOT_AUTHORIZED
live_host_e2e=NOT_QUALIFIED
```

## Remaining D0 trust gaps

- Policy and inventory are supplied assertions. They are not signed by an independently trusted host owner; acknowledgement is not authorization.
- Only direct mounts at/inside three selected paths are rejected. Parent bind mounts, mount namespaces, shared volumes/remote storage, real Docker socket provenance, image consumers outside an empty local container listing, and credentials are not proven isolated.
- A `docker ps -a` empty result and unique daemon string do not prove that no external Docker users, remote contexts or shared daemons exist.
- Snapshot/restore mechanism, owner-exclusive destruction rights, actual service isolation, externally provisioned throwaway hardware/VM identity, and expected model fixture ownership are **not independently attested**.
- The command itself does not create an evidence file or admission token, and the positive exit code must not be interpreted as D0 pass. No live D1–D5 testing is authorized by this result.
- The protected single DGX must never be used to run the host inspector. Only an independently confirmed disposable test machine may undergo a separately reviewed read-only trial.

```text
D0_OFFLINE_POLICY=IMPLEMENTED
D0_HOST_CROSSCHECK_SOURCE=IMPLEMENTED
D0_CROSSCHECK_FIXTURE_TESTS=PASS_12_OF_12
GITHUB_CI_38218663210=SUCCESS_824_FULL_77_SYNTHETIC
ACTUAL_INDEPENDENT_HOST_CROSSCHECK=NOT_RUN
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
MERGE=BLOCKED
```

This evidence commit is a later documentation HEAD and needs its own GitHub CI result.
