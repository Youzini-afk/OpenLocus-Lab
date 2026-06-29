# BEA-v1-N10AW Cost-Sensitive Span-Window Frontier Mechanism Decomposition

Date: 2026-06-29

BEA-v1-N10AW decomposes the locked N10AV/N10AS/N10AU span-window frontier by marginal cost tier. It reads exactly the scoped private N1 span rows and public N10AV/N10AU/N10AS/N10Z artifacts. It does not add variants, tune adaptively, rerun retrieval, execute OpenLocus, generate/materialize candidates, alter candidate pools, sweep rank/order arms, or make heldout, runtime/default, method-winner, or downstream-value claims.

## Result

```text
status: cost_sensitive_span_window_frontier_mechanism_decomposition_complete_n10ax_authorized
self-test: 14 / 14
forbidden scan: pass
private span rows read: 213
frontier chain consistent: true
result accounting valid: true
```

## Frontier tier accounting

| Tier | Cumulative top10 span hits | Cumulative top20 span hits | New top10 hits vs previous | Lost previous hits | Marginal cost | Marginal cost / new hit bucket |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| baseline | 9 | 10 | 9 | 0 | 0 | baseline |
| pm30 | 18 | 22 | 9 | 0 | 600 | low |
| before25_after75 | 20 | 24 | 2 | 0 | 400 | medium |
| pm75 | 21 | 25 | 1 | 0 | 500 | high |
| pm200 | 25 | 30 | 4 | 0 | 2500 | very_high |

## Mechanism buckets for newly recovered top10 span hits

| Transition | before_gold_gap | after_gold_gap | already_reachable_late_rank | other_bucketed |
| --- | ---: | ---: | ---: | ---: |
| baseline -> pm30 | 8 | 1 | 0 | 0 |
| pm30 -> before25_after75 | 2 | 0 | 0 | 0 |
| before25_after75 -> pm75 | 0 | 1 | 0 | 0 |
| pm75 -> pm200 | 3 | 1 | 0 | 0 |

The max-recall gains are therefore still bucketed as wider recovery of same-file before/after gold-window misses, not a qualitatively different late-rank mechanism in this scoped same-source proxy.

## Handoff

N10AW authorizes only `BEA-v1-N10AX Cost-Sensitive Frontier Claim Package`, a public package only. It does not authorize private reads, recompute, new variants, adaptive tuning, heldout/generalization claims, runtime/default changes, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition.py`
- Report: `artifacts/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition_report.json`
