# BEA-v1-N10X N1 Span-Surface Span-Level Utility Validation

Date: 2026-06-29

BEA-v1-N10X is a direct empirical validation of the N1 span-surface proxy at span level. It uses the same four N10T/N10V proxy arms and the same recovered N1 span rows, but the primary metric is overlap with private gold line ranges rather than file-level reach.

## Result

```text
status: n1_span_surface_span_level_utility_validation_complete_below_threshold
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
span-evaluable denominator: 213
reachable file count: 52
span-reachable count: 12
best arm: span_extra_depth_promote_before_primary_prefix_4
best span-overlap top10: 9
best span-overlap top20: 10
best file top10/top20: 34 / 44
best delta span-overlap top10 vs baseline: 9
regressions: 0
threshold: delta >= 11 and regressions <= 3
threshold passed: false
```

## Interpretation

The N10T file-level proxy gain is real as a file-reach signal, but the stricter span-level utility gate does not pass: the best arm improves span-overlap top-10 by 9 cases, below the required threshold of 11. This is not a method-winner or runtime/default result.

## Boundary

N10X reads exactly the scoped recovered N1 span rows and no other private files. It does not publish private paths, file names, contents, gold line ranges, spans, snippets, candidate lists, exact ranks, source hashes, provider payloads, or raw rows. It does not run retrieval, rerun P4L/N1/N2/N3, execute OpenLocus, generate/materialize candidates, add/remove candidates, search new arms, run selector/reranker logic, run support labeling, enter P5/BEA-v1-A, run counterfactuals, or promote policy/runtime/default behavior.

## Decision

Because the validation completed below threshold, N10X authorizes only `BEA-v1-N10Y N1 Span-Surface Span-Level Utility Result Audit`. It does not authorize runtime/default promotion, P5, BEA-v1-A, selector/reranker execution, retrieval/reruns, new arms, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10x_n1_span_surface_span_level_utility_validation.py`
- Report: `artifacts/bea_v1_n10x_n1_span_surface_span_level_utility_validation/bea_v1_n10x_n1_span_surface_span_level_utility_validation_report.json`
