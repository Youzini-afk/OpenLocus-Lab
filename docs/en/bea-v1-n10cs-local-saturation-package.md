# BEA-v1-N10CS Local Saturation Sweep Public Package

Date: 2026-06-30

BEA-v1-N10CS is a public-only package of the N10CR mechanism-guided local saturation sweep. It reads public artifacts only and performs no private reads, no recompute, and no new variants.

## Result

```text
status: local_saturation_package_complete_n10ct_authorized
self-test: 12 / 12
forbidden scan: pass
private reads in N10CS: 0
recomputes in N10CS: 0
N10CT authorized: true
```

## Packaged facts

- N10CR completed with 8 fixed variants.
- Refined anchor `anchor_refined_top2_pm200_short75_225`: top10/top20 `25 / 31`, cost10/cost20 `3200 / 6200`.
- `pm200_all_spans`: top10/top20 `25 / 30`, cost10/cost20 `4000 / 8000`.
- Positive local result: `top2_pm300_short75_225` reaches top10/top20 `26 / 32`, cost10/cost20 `3600 / 6600`, with lost refined top10 hits `0` and unchanged candidate pool/order.
- Saturation decision: `local_window_not_saturated`; `overall_saturation=false`; rank/file-reach pivot allowed next from N10CR is `false`.
- Residual under `top2_pm300_short75_225`: file-not-in-top10 remains `167`, same-file/no-span-overlap reduces from `9` to `8`, and span-overlap-beyond-top10 remains `12`.

## Boundary

N10CS packages the same-source N1 proxy result only. It does not authorize runtime/default enablement, existing evaluator hooks, heldout/generalization, retrieval/rerun, candidate generation/add/remove/reorder, rank/file promotion, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Handoff

N10CS authorizes only `BEA-v1-N10CT Exploration Around top2_pm300_short75_225`, to be scoped by the next oracle contract as an adapter smoke or bounded pm300-neighborhood follow-up.

## Artifact

- Script: `eval/bea_v1_n10cs_local_saturation_package.py`
- Report: `artifacts/bea_v1_n10cs_local_saturation_package/bea_v1_n10cs_local_saturation_package_report.json`
