# BEA-v1-N10DW Normalized-BM25 Recovery Mechanism Analysis

Date: 2026-06-30

BEA-v1-N10DW is an analysis-only phase over existing N10DU private candidate rows and the same scoped N1 span rows. It performs no new retrieval, OpenLocus execution, network, clone, provider call, candidate generation, selector/reranker execution, or runtime/default change.

## Result

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

- Recovery rank buckets for `identifier_normalized_bm25_only` sum to 30 and reproduce N10DU: top10 `8`, top20 `9`, top50 `10`.
- Normalization unlocks BM25 for a subset: original BM25 recovered zero, while normalized BM25 recovered 10 cases by top50.
- Remaining failures are mostly nonzero candidate sets with no gold file, so topK/token-cap variants are a bounded next diagnostic rather than scaled retrieval.
- N10DW publishes only buckets and aggregates: no raw queries, paths, filenames, candidate lists, snippets, spans, gold labels, or exact ranks.

## Handoff

N10DW authorizes only `BEA-v1-N10DX Normalized-BM25 TopK/Token-Cap Variant Canary` over the same 30 cases with fixed variants: top50/top100 and token cap 12/24. It does not authorize scaling, network, clone, provider calls, candidate generation/materialization, selector/reranker execution, runtime/default changes, P5, BEA-v1-A, method/downstream claims, or heldout/generalization claims.

## Artifact

- Script: `eval/bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis.py`
- Report: `artifacts/bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis/bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis_report.json`
