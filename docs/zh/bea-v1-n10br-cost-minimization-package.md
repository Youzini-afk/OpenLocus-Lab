# BEA-v1-N10BR Plateau Cost-Minimization Package

日期：2026-06-29

BEA-v1-N10BR 是 N10BQ plateau cost-minimization sweep 的 public-only package。它只读取 public artifacts，不读取 private rows，不 recompute metrics，不添加 variants，不进行 adaptive tuning，不运行 retrieval/reruns/OpenLocus，不生成或 materialize candidates，也不作 runtime/default、heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: cost_minimization_package_complete_n10bs_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BR: 0
recomputes in N10BR: 0
N10BS authorized: true
```

## Packaged cost-minimization facts

N10BQ 评估了 20 个预声明 variants：5 个 stable-plateau ratios（`20/80` 到 `40/60`）乘以 4 个 total costs（`60`、`80`、`100`、`120`）。

| Cost | Best top10/top20 | Preserved variants | Package fact |
| ---: | ---: | ---: | --- |
| 60 | 19 / 23 | 0 | lost plateau core = 1 |
| 80 | 20 / 24 | 1 | `cost80_before25_after75`, lost_core=0, lost_pm50=0 |
| 100 | 20 / 24 | 5 | all five plateau ratios preserve |
| 120 | 20 / 24 | 5 | all five plateau ratios preserve |

保留 plateau 的 minimum cost 是 `80`。Chosen research operating point 是 `cost80_before25_after75`。这明确不是 runtime/default recommendation，也不是 method-winner claim。

## Handoff

N10BR 只授权 `BEA-v1-N10BS Boundary-Cost Refinement Sweep`：same scoped N1 span rows，仅 fixed ratio `25/75`，total costs `65`、`70`、`75`、`80`、`85`、`90`、`95`，无 new ratios，无 adaptive tuning，无 ranking/order changes，且仅 public aggregate output。

## Artifact

- Script: `eval/bea_v1_n10br_cost_minimization_package.py`
- Report: `artifacts/bea_v1_n10br_cost_minimization_package/bea_v1_n10br_cost_minimization_package_report.json`
