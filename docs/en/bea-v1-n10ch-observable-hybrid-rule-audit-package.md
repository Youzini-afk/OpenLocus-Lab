# BEA-v1-N10CH Observable Hybrid Span-Shape Rule Sweep Audit Package

Date: 2026-06-29

BEA-v1-N10CH is a public-only audit/package for the N10CG positive observable hybrid span-shape rule sweep. It reads public artifacts only and performs no private reads, no recompute, and no new variants.

## Result

```text
status: observable_hybrid_rule_package_complete_n10ci_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10CH: 0
recomputes in N10CH: 0
N10CI authorized: true
```

## Packaged facts

- N10CG completed with 12 predeclared variants.
- `anchor_short75_225`: `24 / 30`, cost10/cost20 `3000 / 6000`.
- `anchor_pm200_all_spans`: `25 / 30`, cost10/cost20 `4000 / 8000`.
- `short75_225_top3_all_pm200`: `25 / 31`, cost10/cost20 `3300 / 6300`, savings vs pm200 `700 / 1700`, lost short75 hits `0`, decision `recovers_pm200_at_lower_cost`.
- `short75_225_top5_all_pm200`: `25 / 31`, cost10/cost20 `3500 / 6500`, savings vs pm200 `500 / 1500`, lost short75 hits `0`, decision `recovers_pm200_at_lower_cost`.
- `short75_225_top10_all_pm200` also reached `25 / 31`, but it did not save top10 cost and is correctly not counted as a success.
- Medium/long targeted expansions retained `24 / 30` but did not improve.

## Boundary

Policy inputs were only observable span-length bucket and candidate-position bucket. Gold, outcome, miss direction, file identity, and content were not used. Candidate pool/order remained unchanged. This is same-source exploratory evidence only: not heldout/generalization, not runtime/default, not retrieval/rerun, not candidate generation, not cluster/bridge, not adaptive tuning, and not a method/downstream claim.

## Handoff

N10CH authorizes only N10CI independent recompute or adapter smoke of the new candidate strategy `short75_225_top3_all_pm200`. It does not authorize runtime/default promotion, heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/reorder, cluster/bridge execution, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10ch_observable_hybrid_rule_audit_package.py`
- Report: `artifacts/bea_v1_n10ch_observable_hybrid_rule_audit_package/bea_v1_n10ch_observable_hybrid_rule_audit_package_report.json`
