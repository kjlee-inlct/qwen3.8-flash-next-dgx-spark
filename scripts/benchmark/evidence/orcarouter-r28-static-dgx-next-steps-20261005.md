# OrcaRouter R28 — static DGX next steps — 2026-10-05

R28 repository implementation is closed PASS. No live R28 measurement is authorized yet.

The next DGX action is static-only:

1. fast-forward the branch;
2. record managed container ID and StartedAt;
3. build `vllm-orcarouter-v029-r28-unquant-linear-marker:v1` from `scripts/Dockerfile.v029-r28-unquant-linear-markers` using `scripts/` as the Docker build context;
4. run `scripts/benchmark/check-orcarouter-r28-unquant-linear-image.sh`;
5. prove managed container ID / StartedAt and exact OrcaRouter model identity remain unchanged;
6. run `scripts/benchmark/run-orcarouter-r28-unquant-linear-boundary.sh --preflight` only;
7. verify that neither the fresh R28 evidence path nor experiment container was created by preflight.

Expected fresh live-only resources, which must remain absent during preflight:

- evidence: `/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005`
- container: `qwen38-hybrid-r28-unquant-linear-marker`
- kprobe group after preflight: none (`r28_rm` must not remain stale)

Do not set `ORCA_R28_LIVE_ACK=YES` yet. Do not run the R28 harness in `run` mode yet. Do not apply H11 yet.
