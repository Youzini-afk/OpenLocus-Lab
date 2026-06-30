# BEA-v1-N10DY Normalized-BM25 TopK/Token-Cap Canary Public Package

日期：2026-06-30

BEA-v1-N10DY 是 N10DX 的 public-only package。它只读取 N10DX public artifact，不进行 private reads、retrieval、recompute 或 OpenLocus execution。

## 结果

```text
status: normalized_bm25_topk_token_cap_canary_public_package_complete_n10dz_authorized
self-test: 8 / 8
forbidden scan: pass
private reads: 0
retrieval executions: 0
recomputes: 0
```

## Packaged interpretation

- Baseline `normalized_bm25_top50_cap12`：top10/top20/top50/top100 `8 / 9 / 10 / 10`。
- `normalized_bm25_top100_cap12`：`8 / 9 / 10 / 15`；这是 ranks 51-100 的 depth-only improvement `+5`，不是 top10/top20/top50 improvement。
- Cap24 使 head ranking 变差：top50/cap24 为 `6 / 8 / 10 / 10`，top100/cap24 为 `6 / 8 / 10 / 13`。
- Top50/cap12 仍是 best head-ranking point。

## Handoff

N10DY 只授权 `BEA-v1-N10DZ` focused follow-up，用于测试 top100 depth evidence 是否能安全 promotion，或 normalized-BM25 是否应在另一个 small sample 上扩展。它不授权 runtime/default changes、scaled retrieval、method/downstream claims、heldout/generalization claims、candidate generation、selector/reranker execution、P5 或 BEA-v1-A。

## Artifact

- Script: `eval/bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package.py`
- Report: `artifacts/bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package/bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package_report.json`
