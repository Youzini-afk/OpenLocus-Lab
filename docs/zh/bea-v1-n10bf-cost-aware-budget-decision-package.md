# BEA-v1-N10BF Cost-Aware Operating-Point Decision Smoke Audit Package

日期：2026-06-29

BEA-v1-N10BF 是 N10BE budget-conditioned operating-point decision smoke 的 public-only audit/package。它只读取 public artifacts。它不读取 private rows，不 recompute metrics，不添加 variants，不进行 adaptive tuning，不运行 retrieval/reruns/OpenLocus，不生成或 materialize candidates，也不作 runtime/default recommendations。

## 结果

```text
status: cost_aware_budget_decision_package_complete_n10bg_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10BF: 0
recomputes in N10BF: 0
N10BG authorized: true
```

## Packaged budget decisions

| Budget bucket | Rule | Selected point | Variant | top10/top20 | Delta vs baseline | Cost proxy | Cost bucket |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| strict_budget | max cost <= 600 | low_cost | pm30 | 18 / 22 | +9 / +12 | 600 | low |
| moderate_budget | max cost <= 1000 | balanced | before25_after75 | 20 / 24 | +11 / +14 | 1000 | medium |
| recall_budget | max cost <= 4000 | max_recall | pm200 | 25 / 30 | +16 / +20 | 4000 | very_high |

该 package 确认这仍是 research decision only：没有 runtime/default recommendation，没有 new variants，没有 adaptive per-case selection，没有 heldout/generalization，没有 method-winner，也没有 downstream-value claim。

## Handoff

N10BF 只授权 `BEA-v1-N10BG Cost-Aware Decisions vs Fixed-pm50 Comparator`：same scoped N1 rows，无 new variants，将 strict/moderate/recall decisions 与 original fixed pm50 comparator 进行 aggregate metrics 与 bucketed dominance outcomes 对比。N10BF 本身是 public-only。

## Artifact

- Script: `eval/bea_v1_n10bf_cost_aware_budget_decision_package.py`
- Report: `artifacts/bea_v1_n10bf_cost_aware_budget_decision_package/bea_v1_n10bf_cost_aware_budget_decision_package_report.json`
