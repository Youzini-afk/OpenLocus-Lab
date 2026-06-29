# BEA-v1-N10Y N1 Span-Surface Span-Level Utility Result Audit

Date: 2026-06-29

BEA-v1-N10Y is a public-only audit of the N10X span-level utility validation. It performs no private reads, no recompute, and no new experiment.

## Result

```text
status: n1_span_surface_span_level_utility_result_audit_complete
self-test: 13 / 13
forbidden scan: pass
N10X status: n1_span_surface_span_level_utility_validation_complete_below_threshold
span-evaluable denominator: 213
reachable file count: 52
span-reachable count: 12
best arm: span_extra_depth_promote_before_primary_prefix_4
best span-overlap top10/top20: 9 / 10
best file top10/top20: 34 / 44
delta span-overlap top10: 9
regressions: 0
threshold: 11 / 3
threshold passed: false
fallback to file-level: false
```

## Interpretation

N10Y confirms N10X is a complete below-threshold empirical result, not an infrastructure failure. The file-level proxy improvement does not pass the stricter span-level utility gate: best span-overlap top-10 gain is 9, below the threshold of 11.

## Boundary

N10Y reads public artifacts only. It does not read private rows, recompute outcomes, run retrieval, rerun P4L/N1/N2/N3, execute OpenLocus, generate/materialize candidates, search new arms, run selector/reranker logic, enter P5/BEA-v1-A, run counterfactuals, promote runtime/default behavior, or make method-winner/downstream-value claims.

## Decision

Because the span-level result is below threshold, N10Y authorizes only `BEA-v1-N10Z Span-Level Failure Decomposition Preflight` with no execution. Private reads, recompute, execution, runtime/default promotion, P5, BEA-v1-A, selector/reranker execution, retrieval/reruns, new-arm search, method-winner claims, and downstream-value claims remain unauthorized.

## Artifact

- Script: `eval/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit.py`
- Report: `artifacts/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit_report.json`
