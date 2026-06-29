# BEA-v1-N10BQ Plateau Cost-Minimization Sweep

日期：2026-06-29

BEA-v1-N10BQ 是在 same scoped N1 span rows 上进行的 direct empirical cost-minimization sweep。它只使用 stable plateau ratio family（`20/80`、`25/75`、`30/70`、`35/65`、`40/60`）和 4 个预声明 total costs（`60`、`80`、`100`、`120`），共 20 个 fixed variants。它不添加 ranking/order arms，不进行 adaptive tuning，不运行 retrieval/reruns/OpenLocus，不生成 candidates，也不作 runtime/default、heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: plateau_cost_minimization_sweep_complete_n10br_authorized
self-test: 17 / 17
forbidden scan: pass
private span rows read: 213
variant count: 20
minimum cost preserving plateau: 80
chosen research operating point: cost80_before25_after75
N10BR authorized: true
```

## Cost summary

Plateau-preserved 表示 top10 >= 20、top20 >= 24，且 lost plateau-core top10 hits = 0。

| Total cost | Best top10/top20 | Preserved variants | Plateau preserved |
| ---: | ---: | ---: | --- |
| 60 | 19 / 23 | 0 | false |
| 80 | 20 / 24 | 1 | true |
| 100 | 20 / 24 | 5 | true |
| 120 | 20 / 24 | 5 | true |

在 cost 80，只有 `before25_after75` 保留 plateau。在 cost 60，没有 ratio 保留 plateau。在 cost 100 和 120，全部 5 个 stable-plateau ratios 均保留 plateau。

## Boundary

这是 research sweep，不是 runtime/default recommendation。它使用 fixed global windows，无 per-row adaptive choice，无 gold-based window choice，无 plateau family 之外的新 ratio，也无 4 个预声明 costs 之外的新 cost。

## Handoff

N10BQ 只授权 `BEA-v1-N10BR Plateau Cost-Minimization Package`，即该 cost-minimization result 的 public package。

## Artifact

- Script: `eval/bea_v1_n10bq_plateau_cost_minimization_sweep.py`
- Report: `artifacts/bea_v1_n10bq_plateau_cost_minimization_sweep/bea_v1_n10bq_plateau_cost_minimization_sweep_report.json`
