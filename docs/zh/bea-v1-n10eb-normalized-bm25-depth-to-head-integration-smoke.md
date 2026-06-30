# BEA-v1-N10EB Normalized-BM25 Depth-to-Head Integration Smoke

日期：2026-06-30

BEA-v1-N10EB 测试：N10DZ 中只能在深层找到的 normalized-BM25 candidates，能不能通过固定、gold-free 的重排规则推到前 10。它只使用 N10DZ 已经取回的 top100 私有行，以及 scoped N1 span rows 做 novelty comparison/scoring。不运行新的 retrieval、OpenLocus、network、clone、provider、selector、reranker 或 candidate generation。

## 结果

```text
status: normalized_bm25_depth_to_head_integration_smoke_complete_n10ec_authorized
self-test: 13 / 13
forbidden scan: pass
case count: 60
variant count: 8
baseline normalized-BM25 top10/top20/top50/top100: 5 / 11 / 17 / 26
best top10 variant: novel_file_first_top10
best top10/top20/top50/top100: 11 / 16 / 20 / 26
best top20 variant: novel_file_first_top20_then_top10
best top20/top10: 18 / 11
depth-to-head success variants: 3
new retrieval executions: 0
candidate added/removed: 0
```

## Interpretation

一个简单固定规则“优先放旧 N1 池里没有出现过的文件”，把 depth-only source signal 转成了 head-ranking gain。Top10 recovery 从 `5/60` 提到 `11/60`，达到 N10EB threshold，并且没有丢失 baseline top10 hits。

这仍然只是 same-source smoke。它不是 runtime/default readiness，不是 scaled retrieval result，不是 method-winner claim，也不是 downstream value。

## Variant outcomes

```text
baseline_bm25_order: 5 / 11 / 17 / 26
distinct_file_top10: 8 / 11 / 17 / 26
distinct_file_top20_then_top10: 8 / 14 / 17 / 26
novel_file_first_top10: 11 / 16 / 20 / 26
novel_file_first_top20_then_top10: 11 / 18 / 20 / 26
top5_bm25_then_novel_fill_top10: 8 / 13 / 18 / 26
top5_bm25_then_distinct_file_fill_top10: 8 / 11 / 17 / 26
top5_bm25_then_novel_distinct_fill_top10: 10 / 13 / 18 / 26
```

## Handoff

N10EB 只授权 `BEA-v1-N10EC Normalized-BM25 Depth-to-Head Integration Audit Package`。

## Artifact

- Script: `eval/bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke.py`
- Report: `artifacts/bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke/bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke_report.json`
