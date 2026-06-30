# BEA-v1-N10DY Normalized-BM25 TopK/Token-Cap Canary Public Package

Date: 2026-06-30

BEA-v1-N10DY is a public-only package of N10DX. It reads only the N10DX public artifact and performs no private reads, retrieval, recompute, or OpenLocus execution.

## Result

```text
status: normalized_bm25_topk_token_cap_canary_public_package_complete_n10dz_authorized
self-test: 8 / 8
forbidden scan: pass
private reads: 0
retrieval executions: 0
recomputes: 0
```

## Packaged interpretation

- Baseline `normalized_bm25_top50_cap12`: top10/top20/top50/top100 `8 / 9 / 10 / 10`.
- `normalized_bm25_top100_cap12`: `8 / 9 / 10 / 15`; this is a depth-only improvement of `+5` at ranks 51-100, not a top10/top20/top50 improvement.
- Cap24 worsens head ranking: top50/cap24 is `6 / 8 / 10 / 10`, and top100/cap24 is `6 / 8 / 10 / 13`.
- Top50/cap12 remains the best head-ranking point.

## Handoff

N10DY authorizes only `BEA-v1-N10DZ` focused follow-up to test whether top100 depth evidence can be promoted safely or whether normalized-BM25 should be expanded on another small sample. It does not authorize runtime/default changes, scaled retrieval, method/downstream claims, heldout/generalization claims, candidate generation, selector/reranker execution, P5, or BEA-v1-A.

## Artifact

- Script: `eval/bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package.py`
- Report: `artifacts/bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package/bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package_report.json`
