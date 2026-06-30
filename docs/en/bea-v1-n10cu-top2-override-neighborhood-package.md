# BEA-v1-N10CU Top2 Override Neighborhood Public Package

Date: 2026-06-30

BEA-v1-N10CU is a public-only package of the N10CT top2 override window neighborhood sweep. It reads public artifacts only and performs no private reads, no recompute, and no new variants.

## Result

```text
status: top2_override_neighborhood_package_complete_n10cv_authorized
self-test: 11 / 11
forbidden scan: pass
private reads in N10CU: 0
recomputes in N10CU: 0
N10CV authorized: true
```

## Packaged facts

- N10CT completed with 9 fixed variants: pm200, pm225, pm250, pm275, pm300, pm325, pm350, pm375, and pm400.
- pm200: top10/top20 `25 / 31`, cost10/cost20 `3200 / 6200`.
- pm275: top10/top20 `26 / 32`, cost10/cost20 `3500 / 6500`; first/minimal tested pm preserving `26 / 32`, lost pm300 top10 hits `0`, and lower cost than pm300.
- pm300: top10/top20 `26 / 32`, cost10/cost20 `3600 / 6600`.
- pm325, pm350, and pm375: each `26 / 32`.
- pm400: top10/top20 `27 / 33`, cost10/cost20 `4000 / 7000`, improving pm300 by `+1 / +1`.
- Candidate pool/order unchanged; no top3 override and no medium/long extra gates.

## Boundary

N10CU is same-source N1 proxy packaging only. It does not authorize private reads, recompute, new variants, runtime/default enablement, existing evaluator hooks, heldout/generalization, retrieval/rerun, candidate generation/add/remove/reorder, top3 override, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Handoff

N10CU authorizes only `BEA-v1-N10CV Follow-up Around pm400 Gain`, to be scoped by the next oracle contract as pm400 gain mechanism analysis or pm400-neighborhood exploration.

## Artifact

- Script: `eval/bea_v1_n10cu_top2_override_neighborhood_package.py`
- Report: `artifacts/bea_v1_n10cu_top2_override_neighborhood_package/bea_v1_n10cu_top2_override_neighborhood_package_report.json`
