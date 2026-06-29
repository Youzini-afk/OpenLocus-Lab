# BEA-v1-N10W N1 Span-Surface Proxy Replication Package

Date: 2026-06-29

BEA-v1-N10W is a public replication/package phase for the N10T/N10U/N10V N1 span-surface proxy result. It performs no new experiment: it reads public artifacts only and packages the validated aggregate proxy result and claim boundary.

## Result

```text
status: n1_span_surface_proxy_replication_package_complete
self-test: 15 / 15
forbidden scan: pass
chain: N10T pass -> N10U audit pass -> N10V recompute pass
surface: n1_span_p4_evidence_order_proxy
N2-equivalent validation: false
eligible denominator: 213
reachable in pool: 52
baseline top10/top20: 0 / 0
best arm: span_extra_depth_promote_before_primary_prefix_4
best top10/top20: 34 / 44
best delta top10 vs baseline: 34
regressions: 0
thresholds: 11 / 3
threshold passed: true
```

## Package boundary

N10W contains only public aggregate pointers and sanitized summary records. It does not read private data, recompute outcomes, run retrieval, rerun P4L/N1/N2/N3, execute OpenLocus, generate or materialize candidates, search new arms, run selector/reranker logic, enter P5/BEA-v1-A, run counterfactuals, promote runtime/default behavior, or make method-winner/downstream-value claims.

## Claim boundary

The packaged result is a proxy/span-surface finding only. It is not N2-equivalent validation, not a runtime/policy/default result, not a method winner, and not downstream-value evidence.

## Decision

N10W authorizes only `BEA-v1-N10X N1 Span-Surface Stronger Validation Preflight` with scope `preflight_only_no_execution`. Execution, private reads, recompute, runtime/default promotion, P5, BEA-v1-A, selector/reranker execution, retrieval/reruns, new-arm search, method-winner claims, and downstream-value claims remain unauthorized.

## Artifact

- Script: `eval/bea_v1_n10w_n1_span_surface_proxy_replication_package.py`
- Report: `artifacts/bea_v1_n10w_n1_span_surface_proxy_replication_package/bea_v1_n10w_n1_span_surface_proxy_replication_package_report.json`
