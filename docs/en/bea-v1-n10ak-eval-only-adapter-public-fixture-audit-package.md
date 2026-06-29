# BEA-v1-N10AK Eval-Only Adapter Public Fixture Integration Audit Package

Date: 2026-06-29

BEA-v1-N10AK is a public/synthetic-only audit package for the N10AJ default-off eval-only adapter patch. It reads public N10AJ/N10AI/N10AH artifacts and performs static adapter/helper source checks only. It does not read private rows and does not recompute empirical N10AB/N10AF metrics.

## Result

```text
status: eval_only_adapter_public_fixture_audit_package_complete_n10al_authorized
self-test: 13 / 13
forbidden scan: pass
N10AJ adapter status: pass
N10AI target: future_eval_only_span_projection_adapter
N10AH helper status: pass
synthetic projection checks: 8 / 8
private reads: 0
empirical recomputes: 0
```

## Audit findings

- N10AJ status and forbidden scan pass.
- N10AI selected the future eval-only span projection adapter target.
- N10AH helper artifact is valid and the helper source exists.
- The adapter source exists, imports the helper, and contains no forbidden IO imports/calls.
- N10AJ synthetic projections passed, count/order preservation passed, no-IO/private boundary passed, no existing evaluator hook-in occurred, and runtime/default configuration remained unchanged.

## Claim boundary

Allowed claim: a default-off eval-only adapter exists and is synthetically validated. Forbidden claims remain runtime/default promotion, existing evaluator hook-in, private read by default, retrieval/rerun, candidate generation, selector/reranker, P5/BEA-v1-A, method-winner, and downstream-value claims.

## Decision

N10AK authorizes only `BEA-v1-N10AL Scoped Eval-Only Adapter Integration Smoke`. N10AK itself does not authorize existing evaluator hook-in, runtime/default enablement, private reads by default, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package.py`
- Report: `artifacts/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package_report.json`
