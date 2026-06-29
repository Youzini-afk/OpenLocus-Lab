# BEA-v1-N10BG Cost-Aware Decisions vs Fixed-pm50 Comparator

Date: 2026-06-29

BEA-v1-N10BG 在同一批 scoped N1 span rows 上，把三个 budget-conditioned span-window decisions 与最初的固定 `pm50` 点对比。这只是 research comparator smoke：不是 runtime/default recommendation，不是 heldout validation，也不是 method-winner 或 downstream-value claim。

## Result

```text
status: cost_aware_decisions_vs_fixed_pm50_comparator_complete_n10bh_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
fixed pm50 comparator: 19 / 23, cost 1000
N10BH authorized: true
```

## Comparator findings

| Budget bucket | Decision | Variant | top10/top20 | Delta vs pm50 | Cost delta vs pm50 | Dominance bucket |
| --- | --- | --- | ---: | ---: | ---: | --- |
| strict_budget | low_cost | pm30 | 18 / 22 | -1 / -1 | -400 | cost_saving_tradeoff_vs_pm50 |
| moderate_budget | balanced | before25_after75 | 20 / 24 | +1 / +1 | 0 | dominates_pm50 |
| recall_budget | max_recall | pm200 | 25 / 30 | +6 / +7 | +3000 | higher_recall_higher_cost_vs_pm50 |

新的有用信号是：`before25_after75` 在同样 cost proxy 下超过了原来的对称 `pm50`。`pm30` 是便宜但小幅损失的选项，`pm200` 则用更高成本换更高召回。

## Boundary

N10BG 不新增 variants，不做 per-case tuning，不改变 candidate pool/order，不跑 retrieval/rerun，也不推荐 runtime/default behavior。它只授权 N10BH public comparator package；下一个研究问题是解释为什么不对称的 `before25_after75` 能赢对称 `pm50`。

## Artifact

- Script: `eval/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator.py`
- Report: `artifacts/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator_report.json`
