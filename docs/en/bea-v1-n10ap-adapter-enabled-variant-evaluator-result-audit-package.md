# BEA-v1-N10AP Adapter-Enabled Variant Evaluator Result Audit Package

Date: 2026-06-29

BEA-v1-N10AP is a public-only audit package for the N10AO adapter-enabled variant evaluator. It reads public N10AO/N10AN/N10AM/N10AL/N10AJ artifacts only. It does not read private rows, recompute metrics, modify code, hook existing evaluators, or change runtime/default behavior.

## Result

```text
status: adapter_enabled_variant_evaluator_result_audit_package_complete_n10aq_authorized
self-test: 14 / 14
forbidden scan: pass
explicit enablement used in N10AO: true
default enabled: false
private read by default: false
private reads in N10AP: 0
empirical recomputes in N10AP: 0
private span rows audited from N10AO: 213
baseline top10/top20 span overlap: 9 / 10
pm50 top10/top20 span overlap: 19 / 23
delta top10 vs baseline: 10
original span-hit lost: 0
candidate pool changed: false
order changed: false
```

## Audit findings

- N10AO status and forbidden scan pass.
- N10AO used explicit scoped enablement while keeping default mode disabled and private-read-by-default false.
- N10AO aggregate result matches the N10AL/N10AB/N10AD chain: 213 rows, baseline 9/10, pm50 19/23, delta +10, and 0 original span-hit losses.
- Candidate pool and order remain unchanged.
- N10AN strategy is `new_adapter_enabled_variant_evaluator` and does not modify existing validated evaluators.
- N10AM/N10AL/N10AJ public statuses pass.
- N10AP performs no private read and no empirical recompute.

## Claim boundary

Allowed claim: a new eval-only variant evaluator reproduces the scoped N1 pm50 aggregate under explicit enablement. Forbidden claims remain runtime/default promotion, existing evaluator hook-in, modification of existing validators, retrieval/rerun, candidate generation, new window tuning, selector/reranker, P5/BEA-v1-A, method-winner, and downstream-value claims.

## Decision

N10AP authorizes only `BEA-v1-N10AQ Heldout External Validation Source-Discovery Preflight`, a public/source-discovery preflight for heldout or external validation. It does not authorize direct experiment execution, private reads, runtime/default enablement, retrieval/rerun, candidate generation, new arms/window tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package.py`
- Report: `artifacts/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package_report.json`
