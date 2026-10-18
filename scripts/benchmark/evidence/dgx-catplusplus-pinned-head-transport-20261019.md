# DGX Spark — catplusplus pinned Hub HEAD transport diagnosis

**Source:** owner-pasted physical Wizard 5 → 23 → 8 output, 2026-10-19 KST.
The upload in the conversation is an actual terminal excerpt, not a
synthetic test. No exact `git rev-parse HEAD` was printed in the
same excerpt; this is a physical observation but NOT a cryptographically
attested source commit.

```text
CATPLUSPLUS_TRANSPORT_PROBE=PINNED_TEXT_HEAD_HEADERS_ONLY
CATPLUSPLUS_TRANSPORT_CONFIG_RESOLVE_HTTP_STATUS=307
CATPLUSPLUS_TRANSPORT_CONFIG_RESOLVE_LOCATION_CLASS=HF_SAME_HOST
CATPLUSPLUS_TRANSPORT_CONFIG_RESOLVE_LOCATION_ROUTE=API_RESOLVE_CACHE
CATPLUSPLUS_TRANSPORT_CONFIG_RAW_HTTP_STATUS=200
CATPLUSPLUS_TRANSPORT_CONFIG_RAW_LOCATION_CLASS=NONE
CATPLUSPLUS_TRANSPORT_CONFIG_RAW_LOCATION_ROUTE=NONE
CATPLUSPLUS_TRANSPORT_LAUNCHER_RESOLVE_HTTP_STATUS=307
CATPLUSPLUS_TRANSPORT_LAUNCHER_RESOLVE_LOCATION_CLASS=HF_SAME_HOST
CATPLUSPLUS_TRANSPORT_LAUNCHER_RESOLVE_LOCATION_ROUTE=API_RESOLVE_CACHE
CATPLUSPLUS_TRANSPORT_LAUNCHER_RAW_HTTP_STATUS=200
CATPLUSPLUS_TRANSPORT_LAUNCHER_RAW_LOCATION_CLASS=NONE
CATPLUSPLUS_TRANSPORT_LAUNCHER_RAW_LOCATION_ROUTE=NONE
CATPLUSPLUS_TRANSPORT_REDIRECT_FOLLOWED=NO
CATPLUSPLUS_TRANSPORT_BODIES_READ=NONE
CATPLUSPLUS_TRANSPORT_SOURCE_DECLARATIONS=NOT_INSPECTED
CATPLUSPLUS_TRANSPORT_LIVE_ADMISSION=BLOCKED
CATPLUSPLUS_M1_SOURCE_AUDIT=NOT_PERFORMED
CATPLUSPLUS_M1_LIVE_ADMISSION=BLOCKED
```

The visible user excerpt ends with a truncated
`CATPLUSPLUS_M1_DOCKER_GPU_MODEL_DOWNLOAD=NOT_PERFORME`
line. No completed value is inferred from the truncated line.

**Interpretation:** Both `resolve/<pinned-sha>/...` HEAD requests
received same-Hugging-Face-host 307 redirects to
`/api/resolve-cache/...`, explaining why a conservative no-redirect
source GET might reject this transport. Both corresponding `raw`
HEAD requests returned HTTP 200 without redirects. This proves
**HEAD transport only**, not successful bounded GET or publisher
text content, ModelOpt-MIXED declarations, engine scale consumption,
GB10 memory residency, actual GPU start or benchmark.
No redirects followed or bodies fetched by the diagnostic.
No permissions to download catplusplus weights or launch a GPU
were issued. As requested by the owner, the next operational
priority is separately measured mazinb checkpoint restoration
and service/benchmark, while catplusplus remains blocked.
