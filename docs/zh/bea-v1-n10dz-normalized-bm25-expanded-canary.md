# BEA-v1-N10DZ Normalized-BM25 Expanded Canary

日期：2026-06-30

BEA-v1-N10DZ 是 normalized BM25 的 bounded same-source expanded canary。它排除原始 30 个 diagnostic cases，从 corrected suffix-safe absent-pool cases 中采样最多 60 个，并且只在 existing local clones 上运行 cap12 的 normalized BM25 top50 与 top100。

## 结果

```text
status: normalized_bm25_expanded_canary_low_recovery_n10ea_authorized
self-test: 12 / 12
forbidden scan: pass
sampled cases: 60
max commands: 120
settings: normalized_bm25_top50_cap12; normalized_bm25_top100_cap12
top50/cap12 top10/top20/top50/top100: 5 / 11 / 17 / 17
top100/cap12 top10/top20/top50/top100: 5 / 11 / 17 / 26
```

## Interpretation

N10DZ 仍是 expanded canary，不是 statistical generalization claim。它测试 N10DU/N10DX normalized-BM25 signal 是否在原始 30-case diagnostic sample 之外仍然存在。按 top10 gate 看结果是 low-recovery：top50/cap12 在 top10 只恢复 `5/60`，低于 10 的 pass threshold。但它仍显示 candidate-source depth signal：top50 恢复 `17/60`，top100/cap12 达到 `26/60`，且同样没有改善 top10。Artifact 中 pool-richness recovered counts 都限定在各自 `(setting, topK)` record 范围内（`recovered_case_count_scope_bucket=setting_and_topk`）。Public outputs 仅为 aggregate/bucket，不包含 raw queries、paths、filenames、candidate lists、exact ranks、snippets、spans 或 gold labels。

## Boundary

不授权 network、git clone、provider、selector/reranker、P5、BEA-v1-A、runtime/default change、method/downstream claim、heldout/generalization claim、scaled full-denominator retrieval 或 candidate generation/materialization。

## Artifact

- Script: `eval/bea_v1_n10dz_normalized_bm25_expanded_canary.py`
- Report: `artifacts/bea_v1_n10dz_normalized_bm25_expanded_canary/bea_v1_n10dz_normalized_bm25_expanded_canary_report.json`
