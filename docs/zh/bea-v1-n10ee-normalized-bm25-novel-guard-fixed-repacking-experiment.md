# BEA-v1-N10EE Normalized-BM25 Novel-Guard Fixed Repacking Experiment

日期：2026-06-30

BEA-v1-N10EE 测试 N10EB novel-first 规则的固定 guarded variants。它只使用已有 N10DZ top100 rows 和 scoped N1 old-pool membership。不运行 new retrieval、OpenLocus、network、clone、provider calls、selector/reranker execution、candidate generation 或 runtime/default changes。

## 结果

```text
status: normalized_bm25_novel_guard_fixed_repacking_experiment_complete_n10ef_authorized
self-test: 9 / 9
forbidden scan: pass
case count: 60
variant count: 8
baseline BM25 top10/top20/top50/top100: 5 / 11 / 17 / 26
full novel-first top10/top20/top50/top100: 11 / 16 / 20 / 26
best guarded variant: top5_bm25_then_novel_distinct_fill_top10
best guarded top10/top20/top50/top100: 10 / 13 / 18 / 26
lost baseline top10: 0 for all variants
```

## Interpretation

Full novel-first 仍然是最强 same-source head rule。保留前 5 个 BM25 位置、再用 novel+distinct 文件补位的 guard 更保守，但会少恢复 1 个 top10 case，并损失几个 top20 case。

所以 N10EE **没有**替换 full novel-first。它说明的是一个 trade-off：

- full novel-first：恢复最强（top10 `11/60`），本样本仍然 zero-loss；
- guarded top5 novel-distinct：稍弱（top10 `10/60`），同样 zero-loss，可能适合后续 stress test。

## Variant outcomes

```text
baseline_bm25_order: 5 / 11 / 17 / 26
novel_file_first_top10: 11 / 16 / 20 / 26
top5_bm25_then_novel_distinct_fill_top10: 10 / 13 / 18 / 26
top3_bm25_then_novel_fill_top10: 9 / 14 / 18 / 26
top5_bm25_then_novel_fill_top10: 8 / 13 / 18 / 26
top7_bm25_then_novel_fill_top10: 7 / 12 / 17 / 26
top5_bm25_then_score_band_novel_fill_top10: 9 / 12 / 17 / 26
top5_bm25_then_old_pool_cap_novel_fill_top10: 9 / 14 / 18 / 26
```

## Handoff

N10EE 只授权 `BEA-v1-N10EF Normalized-BM25 Novel-Guard Experiment Package`。它不授权 runtime/default changes、scaled retrieval、heldout/generalization claims、method-winner claims 或 downstream claims。

## Artifact

- Script: `eval/bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment.py`
- Report: `artifacts/bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment/bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment_report.json`
