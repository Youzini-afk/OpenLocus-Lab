# BEA-v1-N10CC Observable Span-Shape Gated Expansion Smoke

日期：2026-06-29

BEA-v1-N10CC 是 fixed-window 与 cluster-bridge families 之外的 direct empirical same-source smoke。它只使用 observable policy inputs：original evidence span-length bucket 与 candidate position bucket。它读取同一个 scoped N1 span rows，保持 candidate pool/order 不变，并且 gold 只用于 evaluation。

## 结果

```text
status: observable_span_shape_gated_expansion_smoke_complete_n10cd_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
variant count: 12
cost-efficient preserve-anchor variants: 0
recall-improves-anchor variants: 4
N10CD authorized: true
```

## Key findings

Cost80 anchor 仍为 top10/top20 `20 / 24`，top10 cost `800`。pm200 anchor 为 `25 / 30`，top10 cost `4000`。

Observable span-shape gate 找到了 recall-improving same-source variants，但没有找到 lower-cost anchor-preserving variant：

- `short_only_before50_after150`：`22 / 27`，delta `+2 / +3`，top10 cost `2000`，lost anchor hits `0`。
- `short_medium_before50_after150`：`22 / 27`，delta `+2 / +3`，top10 cost `2000`，lost anchor hits `0`。
- `top10_short_only_before50_after150`：`22 / 23`，delta `+2 / -1`，top10 cost `2000`，lost anchor hits `0`。
- `anchor_pm200_all_spans_before200_after200`：`25 / 30`，delta `+5 / +6`，top10 cost `4000`，lost anchor hits `0`。

没有 variant 满足 `cost_efficient_preserve_anchor`：lower/top-k gated variants 要么以不降成本的方式保持 anchor，要么以更高成本提升 recall，要么丢失 anchor coverage。

## Boundary

允许的 policy inputs 仅为 observable original span-length buckets 与 candidate position buckets。Gold paths/lines、file-hit/span-overlap outcomes、before/after-gold direction、file identity as public subgroup 与 content/snippets 均未作为 policy inputs。N10CC 仅为 same-source N1 proxy research；不是 heldout validation，不是 runtime/default behavior，不是 method winner，也不是 downstream-value evidence。

## Handoff

N10CC 只授权 `BEA-v1-N10CD Observable Span-Shape Gated Expansion Audit Package`，即 public audit/package。它不授权 private reads、new variants、runtime/default promotion、heldout/generalization claims、retrieval/rerun、candidate generation/add/remove/reorder、cluster/bridge execution、adaptive tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10cc_observable_span_shape_gated_expansion_smoke.py`
- Report: `artifacts/bea_v1_n10cc_observable_span_shape_gated_expansion_smoke/bea_v1_n10cc_observable_span_shape_gated_expansion_smoke_report.json`
