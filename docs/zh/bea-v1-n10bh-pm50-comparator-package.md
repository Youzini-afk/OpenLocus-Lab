# BEA-v1-N10BH Cost-Aware Decisions vs Fixed-pm50 Comparator Audit Package

日期：2026-06-29

BEA-v1-N10BH 是 N10BG fixed-pm50 comparator 的 public-only audit/package。它只读取 public artifacts，不读取 private rows，不 recompute metrics，不添加 variants，不进行 adaptive tuning，不运行 retrieval/reruns/OpenLocus，不生成或 materialize candidates，也不作 runtime/default recommendations。

## 结果

```text
status: pm50_comparator_package_complete_n10bi_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10BH: 0
recomputes in N10BH: 0
N10BI authorized: true
```

## Packaged pm50 comparison

Fixed pm50 comparator：top10/top20 `19 / 23`，cost proxy `1000`。

| Budget decision | Variant | top10/top20 | Delta vs pm50 | Cost delta vs pm50 | Lost original span hits | Dominance bucket |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| strict_budget / low_cost | pm30 | 18 / 22 | -1 / -1 | -400 | 1 | cost_saving_tradeoff_vs_pm50 |
| moderate_budget / balanced | before25_after75 | 20 / 24 | +1 / +1 | 0 | 0 | dominates_pm50 |
| recall_budget / max_recall | pm200 | 25 / 30 | +6 / +7 | +3000 | 0 | higher_recall_higher_cost_vs_pm50 |

该 package 确认 candidate pool/order 保持不变，且所有输出都是 public aggregate/bucket counts。

## Handoff

N10BH 只授权 `BEA-v1-N10BI Asymmetric Window Direction Mechanism Decomposition`：same scoped rows，比较 pm50 与 `before25_after75`，使用 before/after direction 分析 gained/lost buckets，并验证没有使用 gold/miss direction 来选择 per-record windows。它不授权 new variants、adaptive/default behavior、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、heldout/generalization claims、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10bh_pm50_comparator_package.py`
- Report: `artifacts/bea_v1_n10bh_pm50_comparator_package/bea_v1_n10bh_pm50_comparator_package_report.json`
