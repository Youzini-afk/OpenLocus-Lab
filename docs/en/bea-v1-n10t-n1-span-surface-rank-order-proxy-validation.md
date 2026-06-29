# BEA-v1-N10T N1 Span-Surface Fixed-Pool Rank-Order Proxy Validation

Date: 2026-06-29

BEA-v1-N10T is a proxy/span-surface experiment, not an N2-equivalent validation. It reads exactly one scoped private N1 span-surface row file, evaluates fixed-pool order transforms over the existing `p4_evidence` list order, and publishes only scanner-safe aggregate buckets and counts.

## Result

```text
status: n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized
self-test: 15 / 15
forbidden scan: pass
eligible denominator: 213
reachable in pool: 52
baseline top10 file reach: 0
best arm: span_extra_depth_promote_before_primary_prefix_4
best top10 file reach: 34
best top20 file reach: 44
best delta top10 vs baseline: 34
best regressions vs baseline: 0
threshold: delta >= 11 and regressions <= 3
```

## Boundary

N10T uses file-level gold matching only after ordering. It does not publish private paths, file names, content, spans, snippets, candidate lists, gold paths, exact ranks, source hashes, provider payloads, or raw rows. It does not read other private files, run retrieval, rerun P4L/N1/N2/N3, execute OpenLocus, generate or materialize candidates, add/remove candidates, search new arms, run selector/reranker logic, run support labeling, enter P5/BEA-v1-A, change runtime/default policy, or make method-winner/downstream-value claims.

## Proxy arm results

- `baseline_n1_span_order`: top10 file reach 0, top20 file reach 0.
- `span_extra_depth_promote_before_primary_prefix_4`: top10 file reach 34, top20 file reach 44, delta +34, regressions 0.
- `span_bounded_interleave_primary2_extra1`: top10 file reach 17, top20 file reach 22, delta +17, regressions 0.
- `span_late_extra_depth_demote_after_primary_prefix_8`: top10 file reach 0, top20 file reach 0, delta 0, regressions 0.

## Decision

N10T authorizes only `BEA-v1-N10U N1 Span-Surface Proxy Result Audit`. It does not authorize runtime/default promotion, P5, BEA-v1-A, selector/reranker execution, retrieval/reruns, candidate generation/materialization, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation.py`
- Report: `artifacts/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation_report.json`
