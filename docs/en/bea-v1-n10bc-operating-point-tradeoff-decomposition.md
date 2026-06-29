# BEA-v1-N10BC Operating-Point Tradeoff Decomposition

Date: 2026-06-29

BEA-v1-N10BC is a direct empirical decomposition over the same scoped N1 span rows. It analyzes only the three named operating points authorized by N10BB: `low_cost=pm30`, `balanced=before25_after75`, and `max_recall=pm200`. It uses no new window sizes, no adaptive per-case selection, no runtime/default behavior, no retrieval/rerun/OpenLocus execution, no candidate generation/materialization, and no selector/reranker/P5/BEA-v1-A.

## Result

```text
status: operating_point_tradeoff_decomposition_complete_n10bd_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
usable span rows: 213
N10BD authorized: true
```

## Operating-point progression

| Step | Variant | Cumulative top10/top20 | Marginal top10/top20 | Marginal cost | Cost per new top10 bucket | Lost previous hits |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| baseline | baseline | 9 / 10 | +9 / +10 | 0 | baseline | 0 |
| low_cost | pm30 | 18 / 22 | +9 / +12 | 600 | low | 0 |
| balanced | before25_after75 | 20 / 24 | +2 / +2 | 400 | medium | 0 |
| max_recall | pm200 | 25 / 30 | +5 / +6 | 3000 | very_high | 0 |

## Mechanism buckets for new top10 hits

| Step | before-gold gap | after-gold gap | already-reachable-late-rank | other |
| --- | ---: | ---: | ---: | ---: |
| baseline -> low_cost | 8 | 1 | 0 | 0 |
| low_cost -> balanced | 2 | 0 | 0 | 0 |
| balanced -> max_recall | 3 | 2 | 0 | 0 |

N10BC finds that max-recall gains are the same before/after gold-window gap mechanism as the lower-cost operating points, not a qualitatively new mechanism. Candidate pool and candidate order remain unchanged.

## Boundary

N10BC is same-source N1 span-surface proxy decomposition only. It makes no heldout/generalization, N2-equivalent, runtime/default, method-winner, downstream-value, selector/reranker, P5/BEA-v1-A, retrieval/rerun, candidate-generation, new-variant, or adaptive-selection claim.

## Handoff

N10BC authorizes only `BEA-v1-N10BD Operating-Point Tradeoff Decomposition Audit Package`, a public package. It does not authorize private reads, runtime/default promotion, new variants, adaptive selection, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10bc_operating_point_tradeoff_decomposition.py`
- Report: `artifacts/bea_v1_n10bc_operating_point_tradeoff_decomposition/bea_v1_n10bc_operating_point_tradeoff_decomposition_report.json`
