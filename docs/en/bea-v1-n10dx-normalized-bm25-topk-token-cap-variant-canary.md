# BEA-v1-N10DX Normalized-BM25 TopK/Token-Cap Variant Canary

Date: 2026-06-30

BEA-v1-N10DX is a bounded local canary over the same 30 N10DR/N10DU cases. It runs BM25-only retrieval with normalized queries only, testing four fixed topK/token-cap variants. It uses existing local clones and the local OpenLocus CLI only.

## Result

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

The gain is depth-only: `top100/cap12` adds five recoveries in ranks 51-100,
while top10/top20/top50 stay at `8/9/10`. Increasing the token cap to 24 does
not help the head result; it lowers top10/top20 to `6/8` in this canary. Thus
the best head-ranking point remains `top50/cap12`, while `top100/cap12` is a
deeper-reach signal for follow-up analysis.

## Boundary

N10DX does not perform network access, git clone, provider calls, selector/reranker execution, runtime/default changes, P5, BEA-v1-A, candidate generation/materialization, scaling, heldout/generalization, method-winner claims, or downstream-value claims. Public outputs are aggregate/bucket-only and contain no raw queries, paths, file names, candidate lists, exact ranks, spans, snippets, or gold labels.

## Handoff

N10DX authorizes only `BEA-v1-N10DY Normalized-BM25 TopK/Token-Cap Canary Public Package`.

## Artifact

- Script: `eval/bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary.py`
- Report: `artifacts/bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary/bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary_report.json`
