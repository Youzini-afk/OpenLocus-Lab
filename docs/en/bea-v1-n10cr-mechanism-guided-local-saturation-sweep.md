# BEA-v1-N10CR Mechanism-Guided Local Saturation Sweep

Date: 2026-06-29

BEA-v1-N10CR is a direct empirical same-source sweep over the scoped N1 span rows. It tests whether the refined hybrid local-window family is saturated before pivoting toward rank/file-reach mechanisms. It keeps candidate order fixed and does not add or remove candidates.

## Result

```text
status: mechanism_guided_local_saturation_sweep_complete_n10cs_authorized
self-test: 14 / 14
forbidden scan: pass
private span rows read: 213
variants evaluated: 8
refined anchor: 25 / 31 at 3200 / 6200
pm200 all-spans: 25 / 30 at 4000 / 8000
best variant: top2_pm300_short75_225
best result: 26 / 32 at 3600 / 6600
overall local saturation: false
N10CS authorized: true
```

## Key finding

The local span-window family is **not** saturated yet. The mechanism-guided variant `top2_pm300_short75_225` improves the refined anchor from `25 / 31` to `26 / 32` without changing candidate order or adding candidates.

## Variant results

- `anchor_refined_top2_pm200_short75_225`: `25 / 31`, cost10/cost20 `3200 / 6200`.
- `anchor_pm200_all_spans`: `25 / 30`, cost10/cost20 `4000 / 8000`.
- `top2_pm200_short90_270`: `25 / 31`, cost10/cost20 `3680 / 7280`.
- `top2_pm200_short100_300`: `25 / 31`, cost10/cost20 `4000 / 8000`.
- `top2_pm200_short75_225_medium40_120`: `25 / 31`, cost10/cost20 `3200 / 6200`.
- `top2_pm200_short75_225_medium75_225`: `25 / 31`, cost10/cost20 `3200 / 6200`.
- `top2_pm200_short75_225_medium75_225_long75_225`: `25 / 31`, cost10/cost20 `3200 / 6200`.
- `top2_pm300_short75_225`: `26 / 32`, cost10/cost20 `3600 / 6600`.

The winning local variant reduces same-file/no-span-overlap remaining cases from 9 to 8 while preserving the fixed order. The largest remaining blocker is still file reach/rank: `file_not_in_top10` remains 167 under the best variant.

## Boundary

N10CR does not change candidate order, add or remove candidates, run retrieval/rerun/OpenLocus, generate candidates, execute selector/reranker logic, enter P5/BEA-v1-A, enable runtime/default behavior, or make heldout/generalization, method-winner, or downstream-value claims. Gold/outcome information is used only for aggregate evaluation, not policy.

## Handoff

N10CR authorizes only `BEA-v1-N10CS Local Saturation Sweep Public Package`. It does not authorize runtime/default promotion, existing evaluator hook-in, retrieval/rerun, candidate generation, rank/file promotion, or broad claims.

## Artifact

- Script: `eval/bea_v1_n10cr_mechanism_guided_local_saturation_sweep.py`
- Report: `artifacts/bea_v1_n10cr_mechanism_guided_local_saturation_sweep/bea_v1_n10cr_mechanism_guided_local_saturation_sweep_report.json`
