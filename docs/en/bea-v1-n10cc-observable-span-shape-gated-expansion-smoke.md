# BEA-v1-N10CC Observable Span-Shape Gated Expansion Smoke

Date: 2026-06-29

BEA-v1-N10CC is a direct empirical same-source smoke outside the fixed-window and cluster-bridge families. It uses only observable policy inputs: original evidence span-length bucket and candidate position bucket. It reads the same scoped N1 span rows, keeps candidate pool/order unchanged, and uses gold only for evaluation.

## Result

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

The cost80 anchor remains top10/top20 `20 / 24` with top10 cost `800`. The pm200 anchor is `25 / 30` with top10 cost `4000`.

The observable span-shape gate found recall-improving same-source variants, but not a lower-cost anchor-preserving variant:

- `short_only_before50_after150`: `22 / 27`, delta `+2 / +3`, top10 cost `2000`, lost anchor hits `0`.
- `short_medium_before50_after150`: `22 / 27`, delta `+2 / +3`, top10 cost `2000`, lost anchor hits `0`.
- `top10_short_only_before50_after150`: `22 / 23`, delta `+2 / -1`, top10 cost `2000`, lost anchor hits `0`.
- `anchor_pm200_all_spans_before200_after200`: `25 / 30`, delta `+5 / +6`, top10 cost `4000`, lost anchor hits `0`.

No variant satisfied `cost_efficient_preserve_anchor`: lower/top-k gated variants either preserved the anchor without cost reduction, improved recall with higher cost, or lost anchor coverage.

## Boundary

Allowed policy inputs were observable original span-length buckets and candidate position buckets. Gold paths/lines, file-hit/span-overlap outcomes, before/after-gold direction, file identity as a public subgroup, and content/snippets were not used as policy inputs. N10CC is same-source N1 proxy research only; it is not heldout validation, not runtime/default behavior, not a method winner, and not downstream-value evidence.

## Handoff

N10CC authorizes only `BEA-v1-N10CD Observable Span-Shape Gated Expansion Audit Package`, a public audit/package. It does not authorize private reads, new variants, runtime/default promotion, heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/reorder, cluster/bridge execution, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10cc_observable_span_shape_gated_expansion_smoke.py`
- Report: `artifacts/bea_v1_n10cc_observable_span_shape_gated_expansion_smoke/bea_v1_n10cc_observable_span_shape_gated_expansion_smoke_report.json`
