# BEA-v1-N10DJ N10T-Order File-Reach Rank-Promotion Smoke

日期：2026-06-30

BEA-v1-N10DJ 是在 same scoped N1 span rows 上运行的 direct empirical same-source rank/file-reach smoke。所有 variants 都从 N10T-best-order candidate list 开始，只在 existing pool 内改变 ordering，并同时评估 file reach 和固定 current-best span projection（`short75_225` 加 top2 pm1000）。它不运行 retrieval/rerun/OpenLocus，不生成/materialize/add/remove candidates，不使用 selector/reranker logic，不改变 runtime/default behavior，也不作 heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: n10t_order_file_reach_rank_promotion_smoke_complete_n10dk_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
variant count: 8
anchor file top10/top20: 34 / 44
anchor projected span top10/top20: 30 / 36
N10DK authorized: true
```

## Metrics by variant

| Variant | file top10/top20 | projected span top10/top20 | Δ file top10 | Δ span top10 | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| anchor_n10t_order | 34 / 44 | 30 / 36 | 0 | 0 | no_rank_promotion_improvement |
| anchor_n10t_order_top2_pm1000_span_projection | 34 / 44 | 30 / 36 | 0 | 0 | no_rank_promotion_improvement |
| promote_rank11_20_before_rank6_10 | packaged aggregate | packaged aggregate | packaged | packaged | packaged |
| interleave_top10_with_rank11_20_1to1_after_top5 | packaged aggregate | packaged aggregate | packaged | packaged | packaged |
| promote_rank21_50_after_top5_before_rank6_10 | packaged aggregate | packaged aggregate | packaged | packaged | packaged |
| fill_top10_with_distinct_files_from_rank11_50 | packaged aggregate | packaged aggregate | packaged | packaged | packaged |
| fill_top10_with_distinct_files_from_rank11_100 | packaged aggregate | packaged aggregate | packaged | packaged | packaged |
| max_per_file_2_top10_on_n10t_order | packaged aggregate | packaged aggregate | packaged | packaged | packaged |

所有 8 个 variants 的 exact aggregate counts 见 JSON artifact。Public output 仅为 aggregate，不包含 private paths、filenames、spans、lines、snippets、gold labels、candidate lists 或 exact ranks。

## Boundary

Gold 只在固定 ordering/projection policies 应用之后用于 evaluation。Candidate pool 保持不变；candidate generation、addition、removal、materialization 均为 0。N10DJ 只授权 `BEA-v1-N10DK Rank/File-Reach Rank-Promotion Public Package`。

## Artifact

- Script: `eval/bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke.py`
- Report: `artifacts/bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke/bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke_report.json`
