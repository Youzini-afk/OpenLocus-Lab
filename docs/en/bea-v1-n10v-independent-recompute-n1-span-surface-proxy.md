# BEA-v1-N10V Independent Recompute N1 Span-Surface Proxy

Date: 2026-06-29

BEA-v1-N10V independently recomputes the N10T N1 span-surface proxy result over the same scoped private span rows and the same four proxy arms. It implements the transform logic directly and does not import or call the N10T evaluator. Public output contains only aggregate counts, buckets, booleans, and claim-boundary records.

## Result

```text
status: independent_recompute_n1_span_surface_proxy_pass_n10w_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
other private files read: 0
eligible denominator: 213
reachable in pool: 52
baseline top10/top20: 0 / 0
best arm: span_extra_depth_promote_before_primary_prefix_4
best top10/top20: 34 / 44
best delta top10 vs baseline: 34
regressions: 0
threshold passed: true
comparison to N10T: match
```

## Independent recompute boundary

- Reads exactly the same scoped private N1 span rows authorized by N10U.
- Does not read other private files or broad private storage.
- Does not import or call N10T code or transform functions.
- Uses file-level matching only after ordering; no gold signal is used for ordering.
- Preserves the fixed candidate pool: no candidate addition, removal, generation, or materialization.
- Does not run retrieval, rerun P4L/N1/N2/N3, execute OpenLocus, search new arms, run selector/reranker logic, perform support labeling, enter P5/BEA-v1-A, run counterfactuals, or change runtime/default policy.

## Decision

N10V validates the N10T aggregate proxy result exactly and authorizes only `BEA-v1-N10W N1 Span-Surface Proxy Replication Package`. It does not authorize broad private reads, runtime/default promotion, method-winner claims, downstream-value claims, P5, BEA-v1-A, selector/reranker execution, retrieval, reruns, new-arm search, counterfactuals, or policy changes.

## Artifact

- Script: `eval/bea_v1_n10v_independent_recompute_n1_span_surface_proxy.py`
- Report: `artifacts/bea_v1_n10v_independent_recompute_n1_span_surface_proxy/bea_v1_n10v_independent_recompute_n1_span_surface_proxy_report.json`
