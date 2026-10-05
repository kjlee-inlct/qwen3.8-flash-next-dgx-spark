# OrcaRouter R30 — pre-w13 800 MiB boundary result — 2026-10-06

## Status

**COMPLETED — READ-ONLY POST-HOC PASS — EXACT W13/400 MATCH WITH IMMEDIATE PRECEDING 800 MIXED USERSPACE PLACEMENT**

R30 analyzed only preserved R28 evidence. It did not restart the managed model, launch a candidate, build an image, modify kprobes, or mutate evidence.

Strict discriminator:

`R30_EXACT_W13_400_WITH_IMMEDIATE_PRECEDING_800_MIXED_USERSPACE_PLACEMENT`

RM byte counts are logical allocation activity volume, not exact resident ownership. Marker alignment is temporal evidence, not causal ownership proof.

## Exact 400 MiB closure

The preserved constructor contains exactly 48 selected R26 w13 marker intervals and exactly 48 400 MiB RM requests:

```text
selected_w13_count=48
constructor_400_request_count=48
w13_exact_one_400_count=48
w13_missing_400_count=0
w13_multi_400_count=0
constructor_400_outside_w13_count=0
```

Therefore the 400 MiB RM family is closed event-by-event to the R26 packed-expert `w13_weight` allocation boundary: one and only one 400 MiB request occurs in every w13 interval and no constructor 400 MiB request lies outside those intervals.

This also explains the earlier aggregate R26 value exactly: `400 MiB * 48 = 19200 MiB = modelopt_w13.activity_mib`.

## Immediate preceding 800 MiB family

Every w13-associated 400 MiB request has an immediately preceding RM-stream request of exactly 800 MiB, and all 48 such 800 MiB requests occur before the corresponding w13-begin marker:

```text
w13_400_immediate_preceding_800_count=48
preceding_800_before_w13_begin_count=48
pair_800_to_400_delta_ms=min=24.518000 median=24.925000 max=27.840000
pair_800_to_w13_begin_ms=min=7.822797 median=8.100208 max=8.730840
pair_w13_begin_to_400_ms=min=16.114201 median=16.894804 max=19.422262
```

Thus the current w13 allocation itself cannot be assigned temporal ownership of the preceding 800 MiB event; that event is already present roughly 8.1 ms before the w13 marker begins.

## Userspace placement of the preceding 800 MiB events

The 48 preceding 800 MiB requests align to mixed R28 userspace boundaries:

```text
preceding_800_family_histogram=hyper_connection:32,linear_attn:1,outside_unquant:4,self_attn:11
preceding_800_dominant_family=hyper_connection
preceding_800_dominant_family_pct=66.666667
preceding_800_layer_relation_histogram=800_prev_layer:33,same_layer:15
```

No single userspace family reaches the 90% localization threshold. In particular, hyper-connection accounts for only two thirds of these events and therefore must not be promoted to causal owner of the 800 MiB family.

## Engineering interpretation

R30 closes two points:

1. the 400 MiB request family is exactly the R26 packed-w13 temporal boundary, one request per w13 interval across all 48 decoder layers;
2. each 400 MiB request has an immediately preceding 800 MiB RM request, but the 800 MiB events have mixed userspace placement and occur before the w13 marker begins.

The next smallest discriminator is not another model-prefix split. Existing R26 markers already provide a stronger boundary: `ModelOptNvFp4FusedMoE.create_weights()` BEGIN occurs before `W13_BEGIN`. R31 should classify each preceding 800 MiB event relative to the MoE-BEGIN and W13-BEGIN markers:

- before MoE BEGIN;
- inside MoE create_weights but before W13 BEGIN;
- at/inside W13 (which R30 already makes unlikely temporally).

If all or nearly all 800 MiB events occur before MoE BEGIN, the 800 and 400 families belong to adjacent construction phases and lower-level allocator work should be traced only after identifying the previous phase. If the 800 family lies consistently between MoE BEGIN and W13 BEGIN, the target becomes the early ModelOpt-MoE setup immediately before `w13_weight` allocation.

No R31 live run is authorized yet. H11 remains deferred. PR #244 remains open/unmerged.