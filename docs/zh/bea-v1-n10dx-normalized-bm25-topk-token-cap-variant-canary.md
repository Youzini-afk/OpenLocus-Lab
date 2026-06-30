# BEA-v1-N10DX Normalized-BM25 TopK/Token-Cap Variant Canary

日期：2026-06-30

BEA-v1-N10DX 是 same 30 N10DR/N10DU cases 上的 bounded local canary。它只运行 BM25-only retrieval 与 normalized queries，测试四个固定 topK/token-cap variants。它仅使用 existing local clones 与 local OpenLocus CLI。

## 结果

```text
status: normalized_bm25_topk_token_cap_variant_canary_pass_n10dy_authorized
self-test: 12 / 12
forbidden scan: pass
sampled cases: 30
variant count: 4
command count: 120
best variant: normalized_bm25_top100_cap12
baseline top50/cap12 top10/top20/top50/top100: 8 / 9 / 10 / 10
best top100/cap12 top10/top20/top50/top100: 8 / 9 / 10 / 15
```

这个增益只发生在更深位置：`top100/cap12` 额外找回的 5 个 case 位于
ranks 51-100，top10/top20/top50 仍然是 `8/9/10`。把 token cap 提到 24
没有改善前排结果；本 canary 中 top10/top20 反而降到 `6/8`。因此最佳前排
点仍是 `top50/cap12`，而 `top100/cap12` 是后续分析的 deeper-reach signal。

## Boundary

N10DX 不执行 network access、git clone、provider calls、selector/reranker execution、runtime/default changes、P5、BEA-v1-A、candidate generation/materialization、scaling、heldout/generalization、method-winner claims 或 downstream-value claims。Public outputs 仅为 aggregate/bucket，不包含 raw queries、paths、file names、candidate lists、exact ranks、spans、snippets 或 gold labels。

## Handoff

N10DX 只授权 `BEA-v1-N10DY Normalized-BM25 TopK/Token-Cap Canary Public Package`。

## Artifact

- Script: `eval/bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary.py`
- Report: `artifacts/bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary/bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary_report.json`
