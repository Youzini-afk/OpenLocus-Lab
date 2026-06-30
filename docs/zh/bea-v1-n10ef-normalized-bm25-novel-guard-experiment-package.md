# BEA-v1-N10EF Normalized-BM25 Novel-Guard Experiment Package

日期：2026-06-30

BEA-v1-N10EF 打包 N10EE，不读取私有数据、不重算。它在下一步实验前锁住结果边界。

## 结果

```text
status: normalized_bm25_novel_guard_experiment_package_complete_n10eg_authorized
self-test: 6 / 6
forbidden scan: pass
private reads: 0
recomputes: 0
baseline BM25 top10/top20/top50/top100: 5 / 11 / 17 / 26
full novel-first top10/top20/top50/top100: 11 / 16 / 20 / 26
guarded top5 novel-distinct top10/top20/top50/top100: 10 / 13 / 18 / 26
all tracked variants lost baseline top10: 0
```

## 含义

Full novel-first 仍是这个样本上观察到的最强 same-source rule。Guarded top5 novel-distinct 更保守，但 top10 少 1 个 case。这是有用的 trade-off，不是默认策略决策。

## Handoff

N10EF 只授权 N10EG：在同一 scoped N10DZ top100 rows 和 N1 rows 上做 bounded follow-up experiment。它不授权 new retrieval、scaled retrieval、runtime/default changes、selector/reranker execution、method-winner claims、downstream claims 或 heldout/generalization claims。

## Artifact

- Script: `eval/bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package.py`
- Report: `artifacts/bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package/bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package_report.json`
