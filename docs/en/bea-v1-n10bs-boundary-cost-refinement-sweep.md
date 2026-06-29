# BEA-v1-N10BS Boundary-Cost Refinement Sweep

Date: 2026-06-29

BEA-v1-N10BS is a direct empirical boundary-cost refinement sweep over the same scoped N1 span rows. It fixes the ratio at `25/75` and evaluates only the seven predeclared total costs `65`, `70`, `75`, `80`, `85`, `90`, and `95`. It does not introduce new ratios, adaptive tuning, ranking/order changes, retrieval/reruns/OpenLocus execution, candidate generation, selector/reranker execution, runtime/default behavior, or heldout/generalization/method/downstream claims.

## Result

```text
status: boundary_cost_refinement_sweep_complete_n10bt_authorized
self-test: 17 / 17
forbidden scan: pass
private span rows read: 213
variant count: 7
minimum preserving cost: 80
first failing below boundary: 75
boundary margin: 5
N10BT authorized: true
```

## Boundary-cost metrics

Plateau preservation requires top10=20, top20=24, and lost plateau-core top10 hits=0.

| Total cost | Window before/after | top10/top20 | Lost plateau core | Lost pm50 | Preserved |
| ---: | ---: | ---: | ---: | ---: | --- |
| 65 | 16 / 49 | 19 / 22 | 1 | 0 | false |
| 70 | 17 / 53 | 19 / 22 | 1 | 0 | false |
| 75 | 18 / 57 | 19 / 23 | 1 | 0 | false |
| 80 | 20 / 60 | 20 / 24 | 0 | 0 | true |
| 85 | 21 / 64 | 20 / 24 | 0 | 0 | true |
| 90 | 22 / 68 | 20 / 24 | 0 | 0 | true |
| 95 | 23 / 72 | 20 / 24 | 0 | 0 | true |

The boundary is narrow: cost 75 is the first failing value below the boundary, and cost 80 is the minimum preserving cost. The chosen research operating point remains `cost80_before25_after75`; this is not a runtime/default recommendation.

## Handoff

N10BS authorizes only `BEA-v1-N10BT Boundary-Cost Package`, a public package of this boundary-cost result.

## Artifact

- Script: `eval/bea_v1_n10bs_boundary_cost_refinement_sweep.py`
- Report: `artifacts/bea_v1_n10bs_boundary_cost_refinement_sweep/bea_v1_n10bs_boundary_cost_refinement_sweep_report.json`
