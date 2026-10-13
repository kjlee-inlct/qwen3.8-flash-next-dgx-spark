# Clean DGX Spark wizard — OrcaRouter runtime selection

**Goal:** On a DGX Spark with OS/GPU driver and Docker already installed but
with **no checkpoint, no vLLM image, no application state or release**,
a user runs the interactive wizard once; no separate model download,
Docker build, service scripts or raw experiment commands required.

```bash
git clone https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark.git
cd qwen3.8-flash-next-dgx-spark
git switch feat/h38-managed-integration
./install.sh
```

Select OrcaRouter (menu 1) for provisional baseline
`vllm-orcarouter-v029:v1`. Enter **L** in the model menu to
select `vllm-skinny-tp1:v1` instead. The final plan
shows selected image and the **equivalent CLI**; for legacy
this includes `--orcarouter-runtime legacy`.
Both variants build from included Dockerfiles automatically
when the image is absent. The wizard downloads the **pinned
OrcaRouter checkpoint** (requests the gated Hugging Face token),
prepares model config, sets up **128 GiB swap**, immutable
release and configured systemd/API, and offers optional runtime
start after plan confirmation. Monitor and protective stop are
enabled by default for fresh OrcaRouter unless explicitly
configured otherwise. Use `./install.sh --dry-run` to
preview everything with no model/Docker/manifest writes.

**Prerequisites** (not provisioned by this application):
DGX Spark Linux/NVIDIA GPU driver, functional Docker daemon
and GPU runtime, Git, Python 3, curl, sudo, disk space and
internet/model authorization. No claim of full real empty-host
installation or real model readiness yet: CI verifies source
and simulated previews, not physical GPU/RM acceptance.

On the **existing** protected DGX, do not use these instructions
to reinstall or restart: the installed legacy image and
historical exact stopped Docker predecessor must be preserved.
Use `./install.sh --dry-run` → **5** only to preview the
A/B comparison. The wizard-contained **isolated live A/B**
option is still unimplemented pending protection and exact-ID
validation. No real benchmark or cleanup authorized.

See [A/B protocol](DGX-ORCAROUTER-AB-BENCHMARK.md).
The experimental `vllm-orcarouter-v029-h38-decoder-scope:v1`
image is **not** the clean-install default; H38 requires
explicit separately gated migration.
