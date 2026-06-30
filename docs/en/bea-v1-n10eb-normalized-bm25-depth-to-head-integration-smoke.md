# BEA-v1-N10EB Normalized-BM25 Depth-to-Head Integration Smoke

Date: 2026-06-30

BEA-v1-N10EB tests whether the normalized-BM25 candidates that were only reachable deep in N10DZ can be moved into the first ten positions by fixed, gold-free repacking rules. It uses only the already retrieved N10DZ top100 private rows and the scoped N1 span rows for novelty comparison/scoring. It does not run new retrieval, OpenLocus, network, clone, provider, selector, reranker, or candidate generation.

## Result

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

The simple fixed rule "put files not already present in the old N1 pool first" turns the depth-only source signal into a head-ranking gain. Top10 recovery increases from `5/60` to `11/60`, meeting the N10EB threshold, and no baseline top10 hits are lost.

This is still a same-source smoke. It is not runtime/default readiness, not a scaled retrieval result, not a method-winner claim, and not downstream value.

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

N10EB authorizes only `BEA-v1-N10EC Normalized-BM25 Depth-to-Head Integration Audit Package`.

## Artifact

- Script: `eval/bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke.py`
- Report: `artifacts/bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke/bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke_report.json`
