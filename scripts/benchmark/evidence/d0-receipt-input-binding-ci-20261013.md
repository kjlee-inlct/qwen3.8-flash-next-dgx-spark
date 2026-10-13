# D0 exact-input receipt binding — GitHub source CI evidence (2026-10-13)

## Immutable source and CI identity

- Integration branch: `feat/h38-managed-integration`
- Source commit: `e41a34f06887f526d0a7ac7cb605d263c226f8f6`
- Exact-source [GitHub Actions #38316973840](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38316973840): **COMPLETED SUCCESS**
- Full Python unittest discovery: **845/845 PASS**. Compared to previous 834, adds **10** offline receipt verification tests and **one** strict JSON input-byte SHA256 test. The 22 on-host D0 mocked crosscheck tests remain part of the full Python suite.
- Existing seven-module bounded DGX-oriented synthetic subset: **77/77 PASS**, including 17 profile-switch tests. The 11 new tests are **outside** this bounded subset.
- Bash syntax, ShellCheck, Python compilation, whitespace: **PASS** in GitHub CI.
- **Latest observed actual DGX-local** bounded synthetic result is **77/77 PASS at `1283b1a9252f1ff53d51659049ca42f9449e5ccd`**. All new D0 code is GitHub-tested only; neither the sole protected DGX nor any independent real disposable host executed these scripts.

## Defect addressed: plausible stale crosscheck mixed with another input

Earlier read-only `disposable-d0-readonly-crosscheck.py` reported safe statuses and a Git SHA, but did not bind the result to the **exact policy and inventory bytes**. An older crosscheck result could be mistakenly presented alongside a different policy/inventory while still looking superficially valid. A matching Git SHA alone is insufficient: the protected denylist, model fixture claims, Docker daemon claims or restoration hints could change without changing the Git SHA.

At the same time, the earlier strict `read_json()` checked `lstat()` and then opened a path, with a path swap window where a symlink could replace the checked path before open.

The new `disposable-d0-preflight.py` function `read_json_with_digest()`:
- Reads bounded JSON from a descriptor opened with Linux `O_NOFOLLOW` and `O_NONBLOCK`, checks regular file type and the initial device/inode, refuses duplicate JSON keys and oversize inputs.
- Returns the parsed object **and SHA256 of those same validated bytes**; the compatibility `read_json()` shares this parser.
- Is not a privileged file-integrity monitor; concurrent writes to the *same* inode are not cryptographically prevented by a descriptor.

The read-only crosscheck now includes `policy_sha256` and `inventory_sha256` in successful JSON results. It does **not** include raw host IDs or secret contents; it continues to report `independence=NOT_ATTESTED`, `d0_admission=NOT_GRANTED`, `d1_d5=NOT_AUTHORIZED`.

The new `disposable-d0-receipt-review.py` is an **entirely offline** CLI that reads only three bounded local JSON files, verifies original policy/inventory validity, exact receipt keys, literal non-admission status claims, Git SHA and both byte digests. Invalid/mismatched evidence fails closed. Matching evidence is reported as `D0_RECEIPT_REVIEW=CONSISTENT_UNTRUSTED` with `D0_ADMISSION=NOT_GRANTED`.

## Fixture coverage (10 receipt + 1 JSON reader tests)

The 10 receipt tests verify: consistent-but-untrusted output; policy SHA drift; inventory SHA drift; Git source mismatch; forged D0/host/D1-D5 positive claims; missing/extra/invalid receipt fields; duplicate JSON keys and symlinked receipts; invalid protective policy; sanitized refusal without sensitive content; and the explicit fact that matching unchanged bytes do **not** establish freshness. One additional test validates SHA256 of the same parsed JSON bytes.

The prior D0 crosscheck tests continue passing. No Docker/systemd socket, GPU runtime, production checkpoint, swap or managed service was accessed during this code verification.

## Remaining D0 trust and authorization barriers

- Byte hashes establish **input/result consistency only**. They do not establish that a crosscheck was actually performed on a particular host, when it ran, who controlled the host, or who approved destruction.
- A malicious actor can forge the policy/inventory and crosscheck receipt together; no independent signatures or trusted measurement attestation are present.
- Matching unchanged bytes allow **replay of a stale receipt**, so `D0_RECEIPT_FRESHNESS=NOT_VERIFIED` is mandatory even when the offline check returns success.
- External proof of independent host ownership, Docker exclusivity, absence of external users and shared volumes, restore drill, mount origin, service resource isolation and explicit owner approval is still absent.
- Older read-only crosscheck JSON lacking the new digest fields is intentionally incompatible with the receipt reviewer. Do not fabricate missing fields or re-run the on-host tool on the sole protected DGX.

```text
D0_OFFLINE_POLICY=IMPLEMENTED
D0_CROSSCHECK_INPUT_BINDING=SOURCE_IMPLEMENTED
D0_RECEIPT_CHAIN_REVIEW=SOURCE_IMPLEMENTED
GITHUB_CI_38316973840=SUCCESS_845_FULL_77_SELECTED
NEW_RECEIPT_FIXTURES=PASS_10_OF_10
NEW_READJSON_DIGEST_FIXTURE=PASS_1_OF_1
ACTUAL_DGX_LAST_SYNTHETIC=PASS_77_AT_1283B1A
ACTUAL_INDEPENDENT_HOST_D0_OBSERVATION=NOT_RUN
D0_INDEPENDENT_OWNER_ATTESTATION=NOT_VERIFIED
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

This is the exact-source CI evidence. Its permanent-document commit has a newer SHA and must undergo its own CI; no local DGX acceptance or real-host D0 promotion is implied.
