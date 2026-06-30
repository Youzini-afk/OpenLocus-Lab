# BEA-v1-N10EJ Full-Only vs Guard-Only Difference Analysis

日期：2026-06-30

BEA-v1-N10EJ 只使用同一批 scoped N10DZ top100 private rows 和 N1 rows，分析 N10EG/N10EI 中 full-only 与 guard-only 的差异。它只为聚合分析重算 membership；不运行 retrieval、OpenLocus binary、candidate generation、network、runtime/default changes 或 selector/reranker logic。

## 结果

```text
status: full_guard_difference_analysis_complete_n10ek_authorized
self-test: 8 / 8
forbidden scan: pass
baseline top10: 5
full novel-first top10: 11
guarded top5 novel-distinct top10: 10
full/guard union top10: 13
full/guard intersection top10: 8
full-only: 3
guard-only: 2
```

## 差异 buckets

公开 artifact 只暴露聚合 bucket。不公开 paths、filenames、queries、candidates、gold labels、spans 或 exact ranks。

- 所有 full-only cases 都在 `novel_count_gt_10` bucket。
- 所有 guard-only cases 也在 `novel_count_gt_10` bucket。
- Full-only cases 显示 deep-displacement signal：`full_only_deep_displacement_hit = 3`，`full_only_not_deep_displacement_hit = 0`。
- 在该样本中，guard-only cases 不依赖 preserving BM25 top5 hits：`guard_only_preserves_bm25_top5_hit = 0`，`guard_only_not_bm25_top5_preservation = 2`。
- Top5 duplicate pressure 在两个差异集合中都是混合的：full-only 为 2 none / 1 one-duplicate；guard-only 为 1 none / 1 one-duplicate。

## 含义

下一条有用规则应是 difference-aware，而不是朴素 full/guard 拼接。Full-only 收益符合 aggressive novel-first displacement from deeper BM25 buckets。Guard-only 收益在这里不能用 preserving BM25 top5 hits 解释；它可能需要一个固定规则，在考虑 crowding/ordering pressure 的同时保留 guard 的保守 diversity 行为。

## Handoff

N10EJ 只授权 N10EK fixed difference-aware combination experiment over the same rows。它不授权 new/scaled retrieval、OpenLocus binary execution、candidate generation、network、runtime/default changes、selector/reranker execution、method-winner claims、downstream claims 或 heldout/generalization claims。

## Artifact

- Script: `eval/bea_v1_n10ej_full_guard_difference_analysis.py`
- Report: `artifacts/bea_v1_n10ej_full_guard_difference_analysis/bea_v1_n10ej_full_guard_difference_analysis_report.json`
