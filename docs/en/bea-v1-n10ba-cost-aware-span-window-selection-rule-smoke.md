# BEA-v1-N10BA Cost-Aware Span-Window Selection Rule Smoke

Date: 2026-06-29

BEA-v1-N10BA is a direct empirical smoke over the same scoped N1 span rows using predeclared cost-aware operating points. It evaluates named operating points only, not runtime defaults. It uses no new window sizes, no adaptive per-case selection, no retrieval/rerun/OpenLocus execution, no candidate generation/materialization, no selector/reranker, and no P5/BEA-v1-A.

## Result

```text
status: cost_aware_span_window_selection_rule_smoke_complete_n10bb_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
operating points: 3
new window sizes: 0
adaptive per-case selection: 0
N10BB authorized: true
```

## Operating point results

| Operating point | Variant | top10/top20 span overlap | Delta top10/top20 vs baseline | Cost proxy | Lost previous hits |
| --- | --- | ---: | ---: | ---: | ---: |
| low_cost | pm30 | 18 / 22 | +9 / +12 | 600 (`low`) | 0 |
| balanced | before25_after75 | 20 / 24 | +11 / +14 | 1000 (`medium`) | 0 |
| max_recall | pm200 | 25 / 30 | +16 / +20 | 4000 (`very_high`) | 0 |

Candidate pool and candidate order are unchanged for all operating points.

## Boundary

N10BA is a same-source N1 span-surface proxy smoke. The three operating points are named choices for evaluation only; they are not default/runtime behavior. N10BA makes no heldout/generalization, method-winner, downstream-value, selector/reranker, P5/BEA-v1-A, retrieval/rerun, or runtime/default claim.

## Handoff

N10BA authorizes only `BEA-v1-N10BB Cost-Aware Span-Window Selection Rule Smoke Audit Package`, a public-only audit/package. It does not authorize private reads beyond the same scoped rows, runtime/default promotion, new variants, adaptive selection, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke.py`
- Report: `artifacts/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke_report.json`
