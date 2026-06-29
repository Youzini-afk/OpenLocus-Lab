# BEA-v1-N10BE Cost-Aware Operating-Point Decision Smoke

Date: 2026-06-29

BEA-v1-N10BE is a direct empirical research decision smoke over the same scoped N1 span rows. It evaluates predeclared budget buckets and named operating points only. It is not a runtime/default recommendation, not a method-winner claim, not heldout/generalization evidence, and not downstream-value evidence.

## Result

```text
status: cost_aware_operating_point_decision_smoke_complete_n10bf_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
usable span rows: 213
N10BF authorized: true
```

## Budget decisions

| Budget bucket | Rule | Selected operating point | Variant | top10/top20 | Delta vs baseline | Cost proxy | Cost bucket |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| strict_budget | max cost <= 600 | low_cost | pm30 | 18 / 22 | +9 / +12 | 600 | low |
| moderate_budget | max cost <= 1000 | balanced | before25_after75 | 20 / 24 | +11 / +14 | 1000 | medium |
| recall_budget | max cost <= 4000 | max_recall | pm200 | 25 / 30 | +16 / +20 | 4000 | very_high |

Candidate pool and order remain unchanged. The decision buckets use no new window sizes and no adaptive per-case selection.

## Boundary

N10BE is a same-source N1 span-surface proxy research decision smoke only. It does not recommend a runtime/default policy. It does not authorize method-winner, downstream-value, heldout/generalization, retrieval/rerun, candidate generation/materialization, selector/reranker, P5/BEA-v1-A, new-variant, or adaptive-selection claims.

## Handoff

N10BE authorizes only `BEA-v1-N10BF Cost-Aware Operating-Point Decision Smoke Audit Package`, a public package. It does not authorize additional private reads, runtime/default recommendation, new variants, adaptive selection, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10be_cost_aware_operating_point_decision_smoke.py`
- Report: `artifacts/bea_v1_n10be_cost_aware_operating_point_decision_smoke/bea_v1_n10be_cost_aware_operating_point_decision_smoke_report.json`
