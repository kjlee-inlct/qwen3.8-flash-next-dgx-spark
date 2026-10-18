# Actual DGX OrcaRouter C peer host inventory (read-only, 2026-10-18)

**Source:** operator-supplied terminal from the physical `lc-gx10-pc`, not an image/third-party/CI simulation. **No host write, service or container mutation, model load or GPU benchmark.** Timestamp is the operator conversation date; the exact terminal wall-clock instant was not printed.

## Running Docker processes

```text
docker ps --format '{{.ID}} | {{.Names}} | {{.Image}} | {{.Ports}} | {{.Status}}'
9219d017e6ca | open-webui | ghcr.io/open-webui/open-webui:main | 0.0.0.0:3000->8080/tcp, [::]:3000->8080/tcp | Up 2 weeks (healthy)
360cc353a945 | portainer | portainer/portainer-ce:latest | 8000/tcp, 9000/tcp, 0.0.0.0:9443->9443/tcp, [::]:9443->9443/tcp | Up 2 weeks
```

These are **short** Docker ID prefixes, not full immutable IDs. `docker ps` shows running containers **only**; prior full protected ID/state verification remains in the image-pull and preflight receipts. Do not imply these two containers are inert: Open WebUI and Portainer are running and must not be disturbed.

## C local port

Command `ss -H -ltn '( sport = :18891 )'` produced **no output**. At this inspection instant the command found no listening TCP socket for port `18891`. This is a point-in-time observation, **not a reservation** of this port and not proof against later races or non-TCP listeners.

## Swap and raw physical memory fields

```text
swapon --show
NAME          TYPE SIZE    USED PRIO
/swap-ple.img file 128G 1020.3M   10
/swap.img     file  16G      0B   -2

grep -E '^(MemAvailable|MemFree|CmaFree|SwapFree|SwapTotal):' /proc/meminfo
MemFree:        119400264 kB
MemAvailable:   123921280 kB
SwapTotal:      150994936 kB
SwapFree:       149950172 kB
CmaFree:           69320 kB
```

Interpretation (Linux `/proc/meminfo` kB converted by 1048576 per GiB):
- Non-CMA **free** = `MemFree-CmaFree = 119330944 kB`, approximately **113.8 GiB**.
- Non-CMA **available** = `MemAvailable-CmaFree = 123851960 kB`, approximately **118.1 GiB**.
- Swap free approximately **143.0 GiB**, PLE swap device active with existing **1020.3M** used, *not zero usage*.
- The current resources are ample for a **source-only readiness snapshot**, not evidence a 95+GiB checkpoint will safely initialize in the pinned official ARM64 image.

## Qualification boundary

- Running Docker currently has no listed AI-serving candidate; managed/legacy A/v0.29 B are separately known preserved stopped from earlier exact identity checks.
- `qwen38-flash-next.service` was earlier independently observed `LoadState=not-found`, `ActiveState=inactive`, `SubState=dead` in **both** system and user managers. This does not rule out other systemd units or non-Docker processes.
- The official pinned C ARM64 image and OCI Entrypoint were independently verified, the earlier source-only preflight exited 0. **No C Docker object exists in this terminal evidence, no vLLM wheel source was attested, and no model inference or throughput was run.**
- Recheck all dynamic safety gates *immediately before* an independent C trial: exact protected Docker IDs/images/states, run/port collisions, memory and swap, phase journal, watchdog readiness, image and weights, and host kernel NVRM/RM baseline. Such a launch would require separate owner approval and must be under an exact-ID armed protective monitor.
