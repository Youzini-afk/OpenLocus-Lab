# BEA-v1-N10ED Novel-First Depth-to-Head Mechanism Analysis

日期：2026-06-30

BEA-v1-N10ED 解释 N10EB 的 novel-first repacking 为什么有效。它只读取 N10EC/N10EB public artifacts，以及 scoped N10DZ top100 private rows 和 N1 private rows。不运行 retrieval、OpenLocus、network、clone、provider calls、selector/reranker execution、candidate generation 或 runtime/default changes。

## 结果

```text
status: normalized_bm25_depth_to_head_mechanism_analysis_complete_n10ee_authorized
self-test: 13 / 13
forbidden scan: pass
case count: 60
baseline BM25 top10/top20/top50/top100: 5 / 11 / 17 / 26
novel-first top10/top20/top50/top100: 11 / 16 / 20 / 26
new top10 recovered vs baseline: 6
lost baseline top10: 0
remaining top10 miss: 49
recommended next phase: BEA-v1-N10EE Normalized-BM25 Novel-Guard Fixed Repacking Experiment
```

## 为什么 novel-first 有效

6 个新增 top10 cases 全部是相对旧 N1 pool 新颖的 matched targets。

它们在 baseline 里的来源深度是：

```text
11-20: 1
21-50: 2
51-100: 3
```

经过 novel-first repacking 后，3 个进入 positions 1-5，3 个进入 positions 6-10。Distinct-file controls 只恢复了 6 个中的 1 个，所以主要机制不是泛化的文件多样性，而是旧池 novelty。

## 为什么还有 49 个没进 top10

Novel-first 后剩余 top10 misses 分成：

```text
target in 11-20: 5
target in 21-50: 4
target in 51-100: 6
target absent from top100: 34
```

15 个 present-but-not-top10 misses 的 target 全部也相对旧 N1 pool 新颖。问题是它前面还有很多其它 novel files：其中 13 个有超过 10 个 novel items ahead，2 个有 6-10 个 novel items ahead。这支持下一步做 guarded novel-first，而不是盲目把所有 novel files 都放最前。

## Handoff

N10ED 只授权 N10EE：在已有 N10DZ top100 rows 上做固定、gold-free 的 novel-guard repacking experiment。它不授权 new retrieval、scaled retrieval、runtime/default changes、selector/reranker execution、method-winner claims、downstream claims 或 heldout/generalization claims。

## Artifact

- Script: `eval/bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis.py`
- Report: `artifacts/bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis/bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis_report.json`
