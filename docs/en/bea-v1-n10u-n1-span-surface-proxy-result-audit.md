# BEA-v1-N10U N1 Span-Surface Proxy Result Audit

Date: 2026-06-29

BEA-v1-N10U is a public-artifact-only audit of the N10T N1 span-surface proxy validation. It reads public N10T/N10R/N9 artifacts only. It does not read private rows, scan private storage, recompute the proxy result, call N10T code, run retrieval, rerun P4L/N1/N2/N3, generate candidates, run selector/reranker logic, enter P5/BEA-v1-A, or promote runtime/default behavior.

## Result

```text
status: n1_span_surface_proxy_result_audit_pass_n10v_authorized
self-test: 15 / 15
forbidden scan: pass
surface: n1_span_p4_evidence_order_proxy
proxy surface: true
N2-equivalent validation: false
eligible denominator: 213
reachable in pool: 52
baseline top10/top20: 0 / 0
best arm: span_extra_depth_promote_before_primary_prefix_4
best top10/top20: 34 / 44
best delta top10 vs baseline: 34
regressions: 0
threshold: delta >= 11 and regressions <= 3
threshold passed: true
```

## Audit findings

- N10T status is `n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized` and its forbidden scan passes.
- The audited surface is explicitly `n1_span_p4_evidence_order_proxy`, with `proxy_surface_bool=true` and `n2_equivalent_validation_bool=false`.
- Result consistency matches N10T exactly: eligible denominator 213, reachable-in-pool 52, baseline top10/top20 0/0, best arm `span_extra_depth_promote_before_primary_prefix_4`, best top10/top20 34/44, delta 34, regressions 0.
- The threshold audit passes: observed delta 34 is above threshold 11, and observed regressions 0 are below threshold 3.
- Privacy and claim boundaries pass: no private paths, file names, candidate lists, gold paths, spans, snippets, hashes, provider payloads, runtime/default claims, method-winner claims, downstream-value claims, P5, or BEA-v1-A.

## Decision

N10U authorizes only `BEA-v1-N10V Independent Recompute N1 Span-Surface Proxy`, using the same private span rows. Broad private reads remain unauthorized. N10U does not authorize runtime/default promotion, method-winner claims, downstream-value claims, P5, BEA-v1-A, selector/reranker execution, retrieval, reruns, new-arm search, counterfactuals, or policy changes.

## Artifact

- Script: `eval/bea_v1_n10u_n1_span_surface_proxy_result_audit.py`
- Report: `artifacts/bea_v1_n10u_n1_span_surface_proxy_result_audit/bea_v1_n10u_n1_span_surface_proxy_result_audit_report.json`
