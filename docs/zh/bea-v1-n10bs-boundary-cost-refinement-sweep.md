# BEA-v1-N10BS Boundary-Cost Refinement Sweep

日期：2026-06-29

BEA-v1-N10BS 是在 same scoped N1 span rows 上进行的 direct empirical boundary-cost refinement sweep。它将 ratio 固定为 `25/75`，并且只评估 7 个预声明 total costs：`65`、`70`、`75`、`80`、`85`、`90`、`95`。它不引入 new ratios、adaptive tuning、ranking/order changes、retrieval/reruns/OpenLocus execution、candidate generation、selector/reranker execution、runtime/default behavior 或 heldout/generalization/method/downstream claims。

## 结果

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

Plateau preservation 要求 top10=20、top20=24，且 lost plateau-core top10 hits=0。

| Total cost | Window before/after | top10/top20 | Lost plateau core | Lost pm50 | Preserved |
| ---: | ---: | ---: | ---: | ---: | --- |
| 65 | 16 / 49 | 19 / 22 | 1 | 0 | false |
| 70 | 17 / 53 | 19 / 22 | 1 | 0 | false |
| 75 | 18 / 57 | 19 / 23 | 1 | 0 | false |
| 80 | 20 / 60 | 20 / 24 | 0 | 0 | true |
| 85 | 21 / 64 | 20 / 24 | 0 | 0 | true |
| 90 | 22 / 68 | 20 / 24 | 0 | 0 | true |
| 95 | 23 / 72 | 20 / 24 | 0 | 0 | true |

该 boundary 很窄：cost 75 是 boundary 以下第一个失败值，cost 80 是 minimum preserving cost。Chosen research operating point 仍为 `cost80_before25_after75`；这不是 runtime/default recommendation。

## Handoff

N10BS 只授权 `BEA-v1-N10BT Boundary-Cost Package`，即该 boundary-cost result 的 public package。

## Artifact

- Script: `eval/bea_v1_n10bs_boundary_cost_refinement_sweep.py`
- Report: `artifacts/bea_v1_n10bs_boundary_cost_refinement_sweep/bea_v1_n10bs_boundary_cost_refinement_sweep_report.json`
