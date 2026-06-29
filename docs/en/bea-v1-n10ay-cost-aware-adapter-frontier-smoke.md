# BEA-v1-N10AY Cost-Aware Adapter Frontier Smoke

Date: 2026-06-29

BEA-v1-N10AY is a direct empirical smoke over the locked cost-sensitive frontier tiers using the default-off eval-only adapter path. It reads the same scoped N1 span rows and public N10AX/N10AW/N10AV/N10AU/N10AS artifacts. It imports the adapter/helper path only, does not import or call existing validated evaluators, and does not hook runtime/default behavior.

## Result

```text
status: cost_aware_adapter_frontier_smoke_pass_n10az_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
adapter imported: true
existing evaluator imported/called: false
runtime/default hook: false
```

## Adapter frontier results

| Variant | top10/top20 span overlap | Cost proxy | Match locked aggregate | Lost original hits |
| --- | ---: | ---: | --- | ---: |
| pm30 | 18 / 22 | 600 (`low`) | true | 0 |
| before25_after75 | 20 / 24 | 1000 (`medium`) | true | 0 |
| pm75 | 21 / 25 | 1500 (`medium`) | true | 0 |
| pm200 | 25 / 30 | 4000 (`very_high`) | true | 0 |

The smoke confirms that the eval-only adapter path reproduces the locked N10AW/N10AV frontier aggregates for the four predeclared frontier variants. Candidate pool and order remain unchanged.

## Boundaries

N10AY is same-source N1 span-surface proxy evidence only. It is not heldout validation, not N2-equivalent validation, not a runtime/default change, not a selector/reranker result, not a method-winner claim, and not downstream-value evidence.

## Handoff

N10AY authorizes only `BEA-v1-N10AZ Cost-Aware Adapter Frontier Smoke Result Audit Package`, which is public-only. It does not authorize additional private reads, existing evaluator hook-in, runtime/default promotion, new variants, adaptive tuning, retrieval/rerun, candidate generation/materialization, selector/reranker execution, P5, BEA-v1-A, method-winner claims, downstream-value claims, or heldout/generalization claims.

## Artifact

- Script: `eval/bea_v1_n10ay_cost_aware_adapter_frontier_smoke.py`
- Report: `artifacts/bea_v1_n10ay_cost_aware_adapter_frontier_smoke/bea_v1_n10ay_cost_aware_adapter_frontier_smoke_report.json`
