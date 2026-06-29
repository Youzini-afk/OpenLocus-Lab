# BEA-v1-N10AC Fixed Span-Window Repair Smoke Result Audit

Date: 2026-06-29

BEA-v1-N10AC is a public-only audit of the N10AB fixed span-window repair smoke. It reads committed public artifacts only. It does not read private rows, recompute outcomes, run retrieval or OpenLocus, generate candidates, search new arms, run selector/reranker logic, enter P5/BEA-v1-A, or promote runtime/default behavior.

## Result

```text
status: fixed_span_window_repair_smoke_result_audit_complete_n10ad_authorized
self-test: 14 / 14
forbidden scan: pass
baseline unexpanded top10/top20 span overlap: 9 / 10
pm20 top10/top20 expanded span overlap: 15 / 19
pm50 top10/top20 expanded span overlap: 19 / 23
pm100 top10/top20 expanded span overlap: 21 / 25
pm50 delta top10 vs unexpanded: 10
pm50 threshold: 11
original span hit lost count: 0
```

## Audit findings

- N10AB status is `fixed_span_window_repair_smoke_pass_n10ac_authorized` and its forbidden scan passes.
- The primary pm50 variant passes: top-10 expanded span overlap is 19, top-20 is 23, baseline top-10/top-20 is 9/10, delta is +10, threshold is 11, and original span-hit loss is 0.
- Sensitivity variants are stable: pm20 reaches 15/19 and pm100 reaches 21/25.
- Candidate pool is unchanged, candidate additions/removals are 0, gold is used only for evaluation, and neither gold nor miss direction is used for window choice.

## Interpretation

Fixed local span-window expansion can recover enough span overlap on the N1 span-surface proxy to pass this smoke. This is not retrieval, not selector/reranker execution, not runtime/default policy, not downstream-value evidence, and not a method-winner claim.

## Decision

N10AC authorizes only `BEA-v1-N10AD Independent Recompute Fixed Span-Window Repair Smoke` over the same private span rows with scoped same-private-read permission. Broad private reads, runtime/default promotion, retrieval/reruns, candidate generation/materialization, new-arm search, selector/reranker execution, P5, BEA-v1-A, method-winner claims, and downstream-value claims remain unauthorized.

## Artifact

- Script: `eval/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit.py`
- Report: `artifacts/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit_report.json`
