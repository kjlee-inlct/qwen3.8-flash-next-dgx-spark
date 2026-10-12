# D0 independent external evidence review — untrusted assertions

> **SOURCE/TESTS ONLY. No actual independent host was inspected.** Do not run
> the on-host crosscheck on the protected sole DGX Spark. This offline review
> cannot authorize D0 or the destructive D1–D5 lifecycle tests.

## Purpose

Combine three *separately collected* sources of D0 safety evidence with the
existing policy/inventory/crosscheck receipt. Hashes ensure the seven local
input files have not been accidentally mixed or swapped. They do not verify
a human's identity, machine ownership, external access or actual snapshot
restoration. The CLI never probes Git/Docker/systemd or writes to host state.

## Out-of-repository inputs

Keep real machine identities, daemon details, private socket/mount inventories
and proof artifacts outside Git history, CI artifacts and public logs.

- `policy.json`: strict original D0 policy (protected DGX denysets).
- `inventory.json`: exact untrusted disposable-host inventory assertions.
- `crosscheck.json`: previous read-only crosscheck receipt with policy and
  inventory SHA-256 fields.
- `external-manifest.json`: manifest with all file hashes and claimed actors.
- `owner-evidence`: independent owner-supplied file stating the permitted
  **read-only D0 review** scope only. It does not authorize D1–D5.
- `isolation-evidence`: independent, externally reviewed evidence about
  daemon exclusivity, external users, volume sharing and production secrets.
- `restore-evidence`: externally witnessed disposable-test-data restore
  drill report. Mere naming of a snapshot is insufficient.

## Manifest v1 example — purely synthetic

```json
{
  "schema_version": 1,
  "source_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "policy_sha256": "1111111111111111111111111111111111111111111111111111111111111111",
  "inventory_sha256": "2222222222222222222222222222222222222222222222222222222222222222",
  "receipt_sha256": "3333333333333333333333333333333333333333333333333333333333333333",
  "owner": {
    "actor": "owner-example",
    "host_machine_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "docker_daemon_id": "disposable-daemon",
    "disposable": true,
    "permitted_scope": "D0_READ_ONLY_REVIEW",
    "evidence_sha256": "4444444444444444444444444444444444444444444444444444444444444444"
  },
  "isolation": {
    "actor": "isolation-reviewer",
    "host_machine_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "docker_daemon_id": "disposable-daemon",
    "no_external_users": true,
    "no_shared_volumes": true,
    "no_production_credentials": true,
    "evidence_sha256": "5555555555555555555555555555555555555555555555555555555555555555"
  },
  "restore": {
    "actor": "restore-witness",
    "host_machine_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "restore_point": "snapshot-before-test",
    "test_data_only": true,
    "drill_result": "PASS_ASSERTED",
    "evidence_sha256": "6666666666666666666666666666666666666666666666666666666666666666"
  }
}
```

The sample hashes are placeholders, **not real evidence**. Exact SHA-256
values must be computed from each source's original file bytes. Each proof is
a different, nonempty, regular non-symlink local file of at most 1 MiB. All
three claimed actor identifiers must differ; this does **not** prove that
three separate people participated.

## Offline validation command

```bash
python3 scripts/lifecycle/disposable-d0-external-evidence-review.py \
  --policy /external/d0-policy.json \
  --inventory /external/d0-inventory.json \
  --crosscheck /external/d0-crosscheck.json \
  --manifest /external/d0-external-manifest.json \
  --owner-evidence /external/d0-owner-proof.txt \
  --isolation-evidence /external/d0-isolation-proof.txt \
  --restore-evidence /external/d0-restore-proof.txt
```

Do not run D0 host collection as a prerequisite on the protected sole DGX.
For a structurally consistent set of *untrusted* inputs, the output contains:

```text
D0_EXTERNAL_EVIDENCE_REVIEW=STRUCTURALLY_CONSISTENT_UNTRUSTED
D0_EXTERNAL_ROLES=CLAIMED_DISTINCT_NOT_AUTHENTICATED
D0_EXTERNAL_ARTIFACTS=BYTE_HASHES_MATCH
D0_OWNER_AUTHORIZATION=NOT_AUTHENTICATED
D0_DOCKER_EXCLUSIVITY=NOT_INDEPENDENTLY_VERIFIED
D0_RESTORE_EXECUTION=NOT_INDEPENDENTLY_VERIFIED
D0_EVIDENCE_FRESHNESS=NOT_VERIFIED
D0_ADMISSION=NOT_GRANTED
D1_D5=NOT_AUTHORIZED
```

Inconsistency or unreadable input returns exit 2 and `REFUSED`.
Exit 0 means **only internal structural consistency**. No tool or future
script may use it as an admission signal.

## Pending external assurance (separate human-controlled gate)

A human review must independently check actor identities and signatures
with a trusted verification channel, prove that the disposable machine/daemon
is outside the protected DGX's physical and logical resource domain,
inspect Docker users and mounts independently, and witness a bounded
throwaway restore operation. None can be established by these JSON claims.

If an independent host is later available, document the trusted reviewer,
verified ownership scope, protected denysets' source, daemon/external users,
shared-storage/mount checks, and controlled restore evidence. Keep the
case `BLOCKED` while any verification remains missing. An independent
authorization decision to execute D1–D5 is a separate future workflow;
it must not be generated by this tool.

The last *actual protected DGX local* 77/77 synthetic acceptance remains
at `1283b1a9252f1ff53d51659049ca42f9449e5ccd`, not this GitHub-only
source.
