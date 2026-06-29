# BEA-v1-N10AD Independent Recompute Fixed Span-Window Repair Smoke

Date: 2026-06-29

BEA-v1-N10AD independently recomputes the N10AB fixed span-window repair smoke over the same scoped recovered N1 span rows. It implements its own row parsing, best-arm ordering, and fixed-window overlap evaluation, and uses N10AB/N10AC public artifacts only for aggregate comparison.

## Result

```text
status: independent_recompute_fixed_span_window_repair_smoke_pass_n10ae_authorized
self-test: 17 / 17
forbidden scan: pass
private span rows read: 213
baseline unexpanded top10/top20 span overlap: 9 / 10
pm20 top10/top20 expanded span overlap: 15 / 19
pm50 top10/top20 expanded span overlap: 19 / 23
pm100 top10/top20 expanded span overlap: 21 / 25
pm50 delta top10 vs unexpanded: 10
original span hit lost count: 0
aggregate comparison to N10AB: match
N10AB code call count: 0
```

## Boundary

N10AD reads exactly the scoped private N1 span-row input and no other private files. It does not import or call the N10AB evaluator or its transform functions. It does not run retrieval/reruns, OpenLocus execution, candidate generation/materialization, candidate add/remove, new arms, selector/reranker, P5, BEA-v1-A, runtime/default promotion, method-winner claims, or downstream-value claims.

## Decision

The independent recompute matches N10AB exactly for baseline, pm20, pm50, and pm100 aggregate metrics. N10AD authorizes only `BEA-v1-N10AE Fixed Span-Window Repair Replication Package`, a public package with no private-read or execution authorization.

## Artifact

- Script: `eval/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke.py`
- Report: `artifacts/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke_report.json`
