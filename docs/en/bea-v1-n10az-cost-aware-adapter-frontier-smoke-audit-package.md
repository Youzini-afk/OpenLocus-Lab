# BEA-v1-N10AZ Cost-Aware Adapter Frontier Smoke Result Audit Package

Date: 2026-06-29

BEA-v1-N10AZ is a public-only audit/package for the N10AY cost-aware adapter frontier smoke. It reads public N10AY/N10AX/N10AW/N10AV artifacts only. It does not read private rows, recompute metrics, add variants, tune adaptively, run retrieval/reruns/OpenLocus, generate/materialize candidates, hook existing evaluators, or change runtime/default behavior.

## Result

```text
status: cost_aware_adapter_frontier_smoke_audit_package_complete_n10ba_authorized
self-test: 15 / 15
forbidden scan: pass
private reads in N10AZ: 0
recomputes in N10AZ: 0
N10BA authorized: true
```

## Audited adapter boundary

- N10AY status is pass.
- Adapter/helper import is true.
- Existing evaluator imported, called, or hook-in is false.
- Runtime/default hook is false.
- N10AY used the same scoped input row count: 213.

## Audited frontier metrics

| Operating point | Variant | top10/top20 span overlap | Cost proxy | Candidate pool/order changed | Lost original hits |
| --- | --- | ---: | ---: | --- | ---: |
| low cost | pm30 | 18 / 22 | 600 (`low`) | false | 0 |
| balanced | before25_after75 | 20 / 24 | 1000 (`medium`) | false | 0 |
| balanced reference | pm75 | 21 / 25 | 1500 (`medium`) | false | 0 |
| max recall | pm200 | 25 / 30 | 4000 (`very_high`) | false | 0 |

## Claim boundary

Allowed claim: default-off eval-only adapter/helper path reproduces the locked same-source N1 proxy frontier aggregates. Forbidden claims remain false: runtime/default promotion, heldout/generalization, N2-equivalent validation, method-winner/downstream value, selector/reranker, P5/BEA-v1-A, retrieval/rerun, candidate generation, new variants, and adaptive tuning.

## Handoff

N10AZ authorizes only `BEA-v1-N10BA Cost-Aware Span-Window Selection Rule Smoke`: same scoped rows, no new window sizes, predeclared operating points only (`pm30` low-cost, `before25_after75` balanced, `pm200` max-recall), and no adaptive per-case selection. N10AZ does not authorize runtime/default behavior or broader claims.

## Artifact

- Script: `eval/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package.py`
- Report: `artifacts/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package_report.json`
