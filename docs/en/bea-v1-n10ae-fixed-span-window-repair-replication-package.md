# BEA-v1-N10AE Fixed Span-Window Repair Replication Package

Date: 2026-06-29

BEA-v1-N10AE is a public-only replication package for the N10AB/N10AC/N10AD fixed span-window repair chain. It reads public artifacts only. It performs no private reads, recompute, retrieval/rerun, OpenLocus execution, candidate generation/materialization, new-arm search, selector/reranker execution, P5/BEA-v1-A, runtime/default promotion, method-winner claim, or downstream-value claim.

## Result

```text
status: fixed_span_window_repair_replication_package_complete_n10af_authorized
self-test: 15 / 15
forbidden scan: pass
N10AB: pass
N10AC: audit complete
N10AD: independent recompute pass
aggregate comparison: match
N10AB code call count in N10AD: 0
baseline unexpanded top10/top20 span overlap: 9 / 10
pm20 top10/top20 expanded span overlap: 15 / 19
pm50 top10/top20 expanded span overlap: 19 / 23
pm50 delta top10 vs unexpanded: 10
pm50 threshold: 11
pm100 top10/top20 expanded span overlap: 21 / 25
original span hit lost count: 0
candidate pool changed: false
```

## Replication chain

- N10AB executed the fixed-window repair smoke and passed.
- N10AC audited the N10AB public result and found it valid.
- N10AD independently recomputed the same fixed-window smoke over the same scoped private span rows and matched N10AB aggregate metrics without importing/calling N10AB code.

## Claim boundary

This package supports only a fixed local span-window expansion result on the N1 span-surface proxy. It is not retrieval, not selector/reranker execution, not N2-equivalent validation, not runtime/default policy, not a method-winner claim, and not downstream-value evidence.

## Decision

N10AE authorizes only `BEA-v1-N10AF Next-Step Selection Stronger Validation Preflight`. It does not authorize private reads, runtime/default promotion, retrieval/reruns, candidate generation/materialization, new-arm search, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10ae_fixed_span_window_repair_replication_package.py`
- Report: `artifacts/bea_v1_n10ae_fixed_span_window_repair_replication_package/bea_v1_n10ae_fixed_span_window_repair_replication_package_report.json`
