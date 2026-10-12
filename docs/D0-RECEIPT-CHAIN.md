# Independent D0 receipt chain — untrusted offline evidence review

> **SOURCE AND FIXTURE TESTS ONLY.** This workflow never grants D0 acceptance or
> authorization to execute D1–D5. Do not invoke the on-host collector on the
> protected sole DGX Spark.

## Purpose and evidence boundaries

The offline D0 policy and inventory must be internally consistent, the
read-only observer result must refer to the exact same **JSON file bytes**, and
the reported Git source SHA must match the policy. Matching data is merely
`CONSISTENT_UNTRUSTED`, not an externally attested host or valid snapshot.
No service or host mutation is performed by the reviewer.

## Source files

- `scripts/lifecycle/disposable-d0-preflight.py`: strict JSON and same-read SHA256.
- `scripts/lifecycle/disposable-d0-readonly-crosscheck.py`: opt-in, read-only
  observation on a **separately confirmed disposable machine only**, where
  owner consent and protected-host exclusion have been checked independently.
  A successful JSON report now includes `policy_sha256` and
  `inventory_sha256`, in addition to non-admission markers.
- `scripts/lifecycle/disposable-d0-receipt-review.py`: fully offline, local,
  non-mutating comparison of a previously collected receipt and policy/inventory.

## Offline review command

Use existing **operator-supplied**, out-of-repository files on a safe review
workstation. Never commit real host identities, private sockets, secrets or
raw inventory details to Git:

```sh
python3 scripts/lifecycle/disposable-d0-receipt-review.py \
  --policy /safe/external/path/d0-policy.json \
  --inventory /safe/external/path/d0-inventory.json \
  --crosscheck /safe/external/path/d0-readonly-crosscheck.json
```

The reviewer **does not launch** the on-host collector or read the live machine.
It accepts only regular non-symlink JSON files of bounded size. Successful
static consistency prints:

```text
D0_RECEIPT_REVIEW=CONSISTENT_UNTRUSTED
D0_RECEIPT_INPUT_DIGESTS=MATCH
D0_EXTERNAL_ATTESTATION=NOT_VERIFIED
D0_RECEIPT_FRESHNESS=NOT_VERIFIED
D0_ADMISSION=NOT_GRANTED
D1_D5=NOT_AUTHORIZED
```

Bad schema, mismatched source SHA, swapped policy/inventory bytes, forged
admission claims or unreadable files print `D0_RECEIPT_REVIEW=REFUSED`
and `D0_ADMISSION=NOT_GRANTED`, returning code 2. Exit 0 is **not** an
admission token; it means only byte-level consistency and expected refusal
claims. This is no proof of signature authenticity or anti-replay freshness.

## Independent D0 requirements still unverified

1. Independent owner authorizes the machine, Docker socket, volume mounts,
   test accounts and throwaway resources; policy denysets have an independent
   protected-DGX source.
2. A separate trusted operator confirms Docker daemon/host identity and
   absence of external users, production mounts, production credentials or
   shared service units **from outside the tested host's own assertions**.
3. Restore mechanism is demonstrated on an isolated throwaway snapshot; record
   verified recovery, not a self-declared restore-point string.
4. Any future D1–D5 live E2E must have separate explicit operator authorization.
   None is implied by receipt review, mocked CI, a passing exit code or a
   GitHub PR. Keep PR #259 Draft/Open/Unmerged while M1–M4 remain unmet.

Latest DGX-local isolated synthetic acceptance remains **77/77 at
`1283b1a9252f1ff53d51659049ca42f9449e5ccd`**. New D0 receipt
code has only GitHub fixture CI, not live host validation.
