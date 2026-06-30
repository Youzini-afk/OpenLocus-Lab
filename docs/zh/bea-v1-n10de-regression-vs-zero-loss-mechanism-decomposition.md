# BEA-v1-N10DE Regression-vs-Zero-Loss Mechanism Decomposition

日期：2026-06-30

BEA-v1-N10DE 是对 baseline existing order、aggressive `distinct_file_top20_greedy_then_top10` 和 conservative `max_per_file_2_top10` 之间 tradeoff 的 direct empirical decomposition。它读取 same scoped N1 span rows，并且只发布 aggregate/bucket outputs。

## 结果

```text
status: regression_vs_zero_loss_mechanism_decomposition_complete_n10df_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
baseline span top10: 13
aggressive span top10: 16
max_per_file_2 span top10: 15
aggressive lost baseline top10 span hits: 1
max_per_file_2 lost baseline top10 span hits: 0
N10DF authorized: true
```

## Outcome groups

- `gained_by_aggressive_only`: 2
- `gained_by_max2_only`: 0
- `gained_by_both`: 2
- `lost_by_aggressive`: 1
- `preserved_by_max2`: 0
- `unchanged_hit`: 12
- `unchanged_miss`: 196

## Regression mechanism

唯一的 aggressive regression 是：strict file uniqueness 移除了一个 early duplicate-file candidate，使 baseline rank-1-10 span hit 被 rank-11-20 replacement 替代。`max_per_file_2_top10` 通过允许同一文件的第二个 candidate，在降低 duplicate pressure 的同时保留了该 regression case。

## Hybrid-rule signal

N10DE 识别了 gold-free hybrid family：`prefix_preserving_distinct_file_fill`。授权给 N10DF 的 preview variants 是：

1. `preserve_top3_then_distinct_file_fill_top10`
2. `preserve_top5_then_distinct_file_fill_top10`
3. `max_per_file_2_then_distinct_file_fill_top10`
4. `max_per_file_2_then_distinct_file_fill_top20_then_top10`
5. `preserve_top3_max_per_file_2_then_distinct_file_fill_top10`

## Boundary

Gold/outcome/miss-direction 不作为 policy input；gold 仅用于 post-hoc bucketed evaluation。N10DE 不运行 retrieval/rerun/OpenLocus、candidate generation/materialization、candidate add/remove、selector/reranker execution、P5、BEA-v1-A、runtime/default changes，也不作 heldout/generalization、method-winner 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition.py`
- Report: `artifacts/bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition/bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition_report.json`
