# BEA-v1-N10AM Eval-Only Adapter Integration Result Audit Package

Date: 2026-06-29

BEA-v1-N10AM is a public-only audit package for the N10AL eval-only adapter integration smoke. It reads public N10AL/N10AK/N10AJ/N10AB/N10AD artifacts only. It does not read private rows, recompute metrics, hook existing evaluators, or modify runtime/default behavior.

## Result

```text
status: eval_only_adapter_integration_result_audit_package_complete_n10an_authorized
self-test: 12 / 12
forbidden scan: pass
eligible denominator: 213
baseline top10/top20 span overlap: 9 / 10
pm50 top10/top20 span overlap: 19 / 23
delta top10 vs baseline: 10
original span-hit lost: 0
candidate pool changed: false
order changed: false
private reads: 0
empirical recomputes: 0
```

## Audit findings

- N10AL status and forbidden scan pass.
- N10AL aggregate result matches N10AB and N10AD: 213 rows, baseline 9/10, pm50 19/23, delta +10, and 0 original span-hit losses.
- Candidate pool and order remain unchanged.
- N10AK and N10AJ public statuses pass.
- N10AM performs no private read and no empirical recompute.

## Claim boundary

Allowed claim: the eval-only adapter reproduces the scoped N1 pm50 aggregate. Forbidden claims remain runtime/default promotion, existing evaluator hook-in, retrieval/rerun, candidate generation, selector/reranker, P5/BEA-v1-A, method-winner, and downstream-value claims.

## Decision

N10AM authorizes only `BEA-v1-N10AN Default-Off Existing-Evaluator Hook Feasibility Preflight`, a public/static preflight. N10AM itself does not authorize existing evaluator hook-in, runtime/default enablement, private reads, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10am_eval_only_adapter_integration_result_audit_package.py`
- Report: `artifacts/bea_v1_n10am_eval_only_adapter_integration_result_audit_package/bea_v1_n10am_eval_only_adapter_integration_result_audit_package_report.json`
