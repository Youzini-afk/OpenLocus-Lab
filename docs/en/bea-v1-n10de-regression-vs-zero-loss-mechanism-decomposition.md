# BEA-v1-N10DE Regression-vs-Zero-Loss Mechanism Decomposition

Date: 2026-06-30

BEA-v1-N10DE is a direct empirical decomposition of the tradeoff among baseline existing order, aggressive `distinct_file_top20_greedy_then_top10`, and conservative `max_per_file_2_top10`. It reads the same scoped N1 span rows and publishes only aggregate/bucket outputs.

## Result

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

The single aggressive regression displaces a baseline rank-1-10 span hit with a rank-11-20 replacement because strict file uniqueness removes an early duplicate-file candidate. `max_per_file_2_top10` preserves that regression case by allowing a second candidate from the same file while still reducing duplicate pressure.

## Hybrid-rule signal

N10DE identifies a gold-free hybrid family: `prefix_preserving_distinct_file_fill`. The authorized N10DF preview variants are:

1. `preserve_top3_then_distinct_file_fill_top10`
2. `preserve_top5_then_distinct_file_fill_top10`
3. `max_per_file_2_then_distinct_file_fill_top10`
4. `max_per_file_2_then_distinct_file_fill_top20_then_top10`
5. `preserve_top3_max_per_file_2_then_distinct_file_fill_top10`

## Boundary

No gold/outcome/miss-direction is used as a policy input; gold is used only for post-hoc bucketed evaluation. N10DE does not run retrieval/rerun/OpenLocus, candidate generation/materialization, candidate add/remove, selector/reranker execution, P5, BEA-v1-A, runtime/default changes, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition.py`
- Report: `artifacts/bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition/bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition_report.json`
