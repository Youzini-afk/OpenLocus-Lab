# BEA-v1-N10AL Scoped Eval-Only Adapter Integration Smoke

Date: 2026-06-29

BEA-v1-N10AL is an empirical eval-only integration smoke for the default-off span projection adapter. It uses the same scoped N1 span rows and the N10AJ adapter to reproduce the N10AB pm50 result. It is not runtime integration and does not hook existing evaluators.

## Result

```text
status: scoped_eval_only_adapter_integration_smoke_pass_n10am_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
baseline top10/top20 span overlap: 9 / 10
pm50 top10/top20 span overlap: 19 / 23
delta top10 vs baseline: 10
original span-hit lost: 0
candidate pool changed: false
order changed: false
matches N10AB/N10AD: true
```

## Boundary

N10AL imports only the eval-only projection adapter for span projection. It does not import or call N10AB, N10AD, N10T, N10X, N1, N2, N3, P4L, runtime, retrieval, selector, or reranker modules. It performs one scoped private read of the recovered N1 span rows, computes only aggregate counts, and publishes no paths, spans, snippets, content, gold lines, candidate lists, or exact ranks.

## Decision

N10AL authorizes only `BEA-v1-N10AM Eval-Only Adapter Integration Result Audit Package`. It does not authorize existing evaluator hook-in, runtime/default enablement, private reads in the next phase, retrieval/rerun, candidate generation/materialization, new arms/window tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke.py`
- Report: `artifacts/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke_report.json`
