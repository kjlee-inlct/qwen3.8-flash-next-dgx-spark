# Managed uninstall fail-closed ownership purge preflight — 2026-10-12

## Change boundaries

This record documents **GitHub-only source and synthetic fixture checks**;
nothing here was installed, removed, restarted or executed against the actual
single DGX Spark host.

- `uninstall.sh` now captures an ordered `plan-purge` successfully under
  its staged registry preflight, before original registry publication,
  service teardown, container removal, or model/image deletion. Nonzero
  plan-generator status (even after partial stdout) stops the operation.
  The one checked snapshot is reused while per-asset registry entries are
  forgotten; no mid-delete process-substitution plan regeneration.
- External Docker image-consumer discovery now checks `docker ps -a`
  completion **before** treating any results as authoritative.
  A partial list with nonzero Docker exit is a refusal, both for
  `--purge-image` and `--purge-all`.
- the asset-ownership Python helper (`asset_ownership.py`) treats only an explicit Docker
  `No such image` or `No such object` response as absence. Missing Docker
  executable, command timeout, daemon error, empty successful image-ID
  response, or other unexpected error is an ownership-check error.
- `uninstall.sh` independently checks image presence/absence before and
  after teardown. A daemon failure during final image removal no longer
  silently forgets its ownership record.
- The fail-closed checks may intentionally block maintenance under an
  unexpected Docker CLI/error-language response. Such a block requires
  diagnosis, **not bypassing safeguards**.

## Synthetic fault-injection coverage

`tests/test_uninstall_wizard_preview.py` gained:
1. partial `plan-purge` stdout followed by nonzero exit; original
   manifest/registry/model/release preserved and no teardown.
2. partial Docker `ps` stdout followed by daemon failure, for both
   image-selective and full purge; no original ownership publication.
3. image `inspect` outage, for selective/full purge; no deletion.
`tests/test_asset_ownership.py` also rejects a failing Docker
image inspection before creating an owned record.

Historical CI results, retained rather than hidden:
- First stage [CI #38196333974](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38196333974):
  **SUCCESS** — 790/790 full tests, 58/58 bounded synthetic tests.
- Expanded policy [CI #38196589215](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38196589215):
  **FAILED 1/792**, an old synthetic Docker stub returned an unclassified
  exit-1 rather than explicit not-found on idempotent retry.
- First fixture correction [CI #38196733837](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38196733837):
  **FAILED at Python compile**, test stub's shell `$` expansion conflicted
  with Python f-string braces.
- Corrected [CI #38196834096](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38196834096):
  **SUCCESS — 792/792 full unit tests, 60/60 bounded synthetic tests**,
  ShellCheck, Bash syntax, Python compilation and whitespace PASS.
  Includes the existing SIGKILL/missing-marker and interrupted swap
  recovery tests.

## Qualification and next execution boundary

These are synthetic-only regression findings. They do not prove real Docker
daemon-loss timing, disk write durability, host PID/process-group kill
semantics, correct systemd ownership, or full actual install→uninstall→
reinstall behavior. See
[the independent disposable-host lifecycle E2E plan](../../../docs/DISPOSABLE-LIFECYCLE-E2E-PLAN.md).

`DGX_LOCAL_SYNTHETIC=PASS` remains supported only at the previously
operator-executed `87fb463...` SHA (56/56 at that revision). Latest
changes are **not pulled/tested on the actual DGX**. No live H38,
runtime/protection or model intervention; PR #259 remains Draft/Open,
M1/M2/M3/M4 remain unqualified/blocked.
