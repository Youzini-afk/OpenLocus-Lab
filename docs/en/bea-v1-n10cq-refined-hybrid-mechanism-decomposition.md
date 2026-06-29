# BEA-v1-N10CQ Refined Hybrid Mechanism Decomposition

Date: 2026-06-29

BEA-v1-N10CQ is a direct empirical same-source mechanism decomposition of the refined hybrid `short75_225_top2_all_pm200`. It is not a new variant sweep. It reads only the same scoped N1 span rows and compares exactly five fixed reference policies.

## Result

```text
status: refined_hybrid_mechanism_decomposition_complete_n10cr_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
policies evaluated: 5
refined hybrid: 25 / 31
top1 result: 24 / 30
top3 result: 25 / 31
pm200 all-spans result: 25 / 30
N10CR authorized: true
```

## Mechanism facts

- `short75_225`: `24 / 30`, cost10/cost20 `3000 / 6000`.
- `short75_225_top1_all_pm200`: `24 / 30`, cost10/cost20 `3100 / 6100`.
- `short75_225_top2_all_pm200`: `25 / 31`, cost10/cost20 `3200 / 6200`.
- `short75_225_top3_all_pm200`: `25 / 31`, cost10/cost20 `3300 / 6300`.
- `pm200_all_spans`: `25 / 30`, cost10/cost20 `4000 / 8000`.

Top2 vs top1 recovers exactly one top10 case: rank2 override recovers the case, rank1 is insufficient, and the case is non-short-span. Top3 vs top2 adds zero top10 recoveries. Remaining top10 misses under the refined hybrid sum to 188: file not in top10 `167`, same-file no span overlap `9`, span overlap beyond top10 `12`, not span reachable `0`.

## Boundary

Gold/outcome/miss-direction is used only for post-hoc bucketed evaluation, not policy. N10CQ does not add/remove/reorder candidates, run retrieval/rerun/OpenLocus, generate candidates, tune adaptively, execute selector/reranker logic, enter P5/BEA-v1-A, enable runtime/default behavior, or make heldout/generalization, method-winner, or downstream-value claims.

## Handoff

N10CQ authorizes only `BEA-v1-N10CR Mechanism-Guided Refined Hybrid Sweep`: same scoped rows, fixed variants derived from N10CQ, and no runtime/default or broad claims.

## Artifact

- Script: `eval/bea_v1_n10cq_refined_hybrid_mechanism_decomposition.py`
- Report: `artifacts/bea_v1_n10cq_refined_hybrid_mechanism_decomposition/bea_v1_n10cq_refined_hybrid_mechanism_decomposition_report.json`
