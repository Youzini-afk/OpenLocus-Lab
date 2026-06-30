# BEA-v1-N10EA Normalized-BM25 Expanded Canary Public Package

日期：2026-06-30

BEA-v1-N10EA 是 N10DZ 的 public-only package。它只读取 N10DZ public artifact，不进行 private reads、retrieval、OpenLocus execution 或 recompute。

## 结果

```text
status: normalized_bm25_expanded_canary_public_package_complete_n10eb_authorized
self-test: 8 / 8
forbidden scan: pass
private reads: 0
retrieval executions: 0
recomputes: 0
primary top50/cap12 top10/top20/top50/top100: 5 / 11 / 17 / 17
depth top100/cap12 top10/top20/top50/top100: 5 / 11 / 17 / 26
```

## Interpretation

按 head gate 看，N10DZ 是 low-recovery：primary top50/cap12 在 top10 只恢复 `5/60`，低于 10 的 pass threshold。但它仍然显示 depth 上的 source signal：top50 恢复 `17/60`，top100 恢复 `26/60`。top100 增益只发生在深层位置，不改善 top10。

N10EA 不宣称 statistical generalization、runtime/default readiness、method winner status 或 downstream value。

## Handoff

N10EA 只授权 `BEA-v1-N10EB Normalized-BM25 Depth-to-Head Integration Experiment`。

## Artifact

- Script: `eval/bea_v1_n10ea_normalized_bm25_expanded_canary_public_package.py`
- Report: `artifacts/bea_v1_n10ea_normalized_bm25_expanded_canary_public_package/bea_v1_n10ea_normalized_bm25_expanded_canary_public_package_report.json`
