# BEA-v1-N10AW Cost-Sensitive Span-Window Frontier Mechanism Decomposition

日期：2026-06-29

BEA-v1-N10AW 按 marginal cost tier 分解 N10AV/N10AS/N10AU 锁定的 span-window frontier。它只读取 scoped private N1 span rows 以及 public N10AV/N10AU/N10AS/N10Z artifacts。它不增加 variants，不进行 adaptive tuning，不 rerun retrieval，不执行 OpenLocus，不生成或 materialize candidates，不改变 candidate pools，不 sweep rank/order arms，也不作 heldout、runtime/default、method-winner 或 downstream-value claims。

## 结果

```text
status: cost_sensitive_span_window_frontier_mechanism_decomposition_complete_n10ax_authorized
self-test: 14 / 14
forbidden scan: pass
private span rows read: 213
frontier chain consistent: true
result accounting valid: true
```

## Frontier tier accounting

| Tier | Cumulative top10 span hits | Cumulative top20 span hits | New top10 hits vs previous | Lost previous hits | Marginal cost | Marginal cost / new hit bucket |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| baseline | 9 | 10 | 9 | 0 | 0 | baseline |
| pm30 | 18 | 22 | 9 | 0 | 600 | low |
| before25_after75 | 20 | 24 | 2 | 0 | 400 | medium |
| pm75 | 21 | 25 | 1 | 0 | 500 | high |
| pm200 | 25 | 30 | 4 | 0 | 2500 | very_high |

## 新增 top10 span hits 的 mechanism buckets

| Transition | before_gold_gap | after_gold_gap | already_reachable_late_rank | other_bucketed |
| --- | ---: | ---: | ---: | ---: |
| baseline -> pm30 | 8 | 1 | 0 | 0 |
| pm30 -> before25_after75 | 2 | 0 | 0 | 0 |
| before25_after75 -> pm75 | 0 | 1 | 0 | 0 |
| pm75 -> pm200 | 3 | 1 | 0 | 0 |

因此，max-recall gains 仍被 bucket 为 same-file before/after gold-window misses 的更宽窗口恢复，而不是这个 scoped same-source proxy 中的质变 late-rank mechanism。

## Handoff

N10AW 只授权 `BEA-v1-N10AX Cost-Sensitive Frontier Claim Package`，且仅为 public package。它不授权 private reads、recompute、new variants、adaptive tuning、heldout/generalization claims、runtime/default changes、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition.py`
- Report: `artifacts/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition_report.json`
