# BEA-v1-N10DW Normalized-BM25 Recovery Mechanism Analysis

日期：2026-06-30

BEA-v1-N10DW 是 analysis-only phase，读取既有 N10DU private candidate rows 与 same scoped N1 span rows。它不执行新的 retrieval、OpenLocus execution、network、clone、provider call、candidate generation、selector/reranker execution 或 runtime/default change。

## 结果

```text
status: normalized_bm25_recovery_mechanism_analysis_complete_n10dx_authorized
self-test: 12 / 12
forbidden scan: pass
private variant rows read: 30
same scoped N1 rows read: 213
identifier_normalized_bm25 top10/top20/top50: 8 / 9 / 10
N10DX authorized: true
```

## Key mechanism findings

- `identifier_normalized_bm25_only` 的 recovery rank buckets 合计为 30，并复现 N10DU：top10 `8`，top20 `9`，top50 `10`。
- Normalization 为一部分 cases 解锁 BM25：original BM25 recovered zero，而 normalized BM25 by top50 recovered 10 cases。
- 剩余失败主要是 nonzero candidate sets with no gold file，因此 topK/token-cap variants 是 bounded next diagnostic，而不是 scaled retrieval。
- N10DW 只发布 buckets 与 aggregates：不发布 raw queries、paths、filenames、candidate lists、snippets、spans、gold labels 或 exact ranks。

## Handoff

N10DW 只授权 `BEA-v1-N10DX Normalized-BM25 TopK/Token-Cap Variant Canary`，范围是 same 30 cases 和固定 variants：top50/top100 与 token cap 12/24。它不授权 scaling、network、clone、provider calls、candidate generation/materialization、selector/reranker execution、runtime/default changes、P5、BEA-v1-A、method/downstream claims 或 heldout/generalization claims。

## Artifact

- Script: `eval/bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis.py`
- Report: `artifacts/bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis/bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis_report.json`
