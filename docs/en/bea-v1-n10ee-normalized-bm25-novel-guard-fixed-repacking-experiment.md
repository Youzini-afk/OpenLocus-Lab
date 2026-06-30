# BEA-v1-N10EE Normalized-BM25 Novel-Guard Fixed Repacking Experiment

Date: 2026-06-30

BEA-v1-N10EE tests fixed guarded variants of the N10EB novel-first rule. It uses only the existing N10DZ top100 rows and scoped N1 old-pool membership. It does not run new retrieval, OpenLocus, network, clone, provider calls, selector/reranker execution, candidate generation, or runtime/default changes.

## Result

```text
status: normalized_bm25_novel_guard_fixed_repacking_experiment_complete_n10ef_authorized
self-test: 9 / 9
forbidden scan: pass
case count: 60
variant count: 8
baseline BM25 top10/top20/top50/top100: 5 / 11 / 17 / 26
full novel-first top10/top20/top50/top100: 11 / 16 / 20 / 26
best guarded variant: top5_bm25_then_novel_distinct_fill_top10
best guarded top10/top20/top50/top100: 10 / 13 / 18 / 26
lost baseline top10: 0 for all variants
```

## Interpretation

Full novel-first remains the strongest same-source head rule. Guarding the first five BM25 positions and then filling with novel+distinct files is safer/conservative but gives up one recovered top10 case and several top20 cases.

So N10EE does **not** replace full novel-first. It shows a trade-off:

- full novel-first: strongest recovery (`11/60` top10), still zero-loss on this sample;
- guarded top5 novel-distinct: slightly weaker (`10/60` top10), also zero-loss, potentially safer for future stress tests.

## Variant outcomes

```text
baseline_bm25_order: 5 / 11 / 17 / 26
novel_file_first_top10: 11 / 16 / 20 / 26
top5_bm25_then_novel_distinct_fill_top10: 10 / 13 / 18 / 26
top3_bm25_then_novel_fill_top10: 9 / 14 / 18 / 26
top5_bm25_then_novel_fill_top10: 8 / 13 / 18 / 26
top7_bm25_then_novel_fill_top10: 7 / 12 / 17 / 26
top5_bm25_then_score_band_novel_fill_top10: 9 / 12 / 17 / 26
top5_bm25_then_old_pool_cap_novel_fill_top10: 9 / 14 / 18 / 26
```

## Handoff

N10EE authorizes only `BEA-v1-N10EF Normalized-BM25 Novel-Guard Experiment Package`. It does not authorize runtime/default changes, scaled retrieval, heldout/generalization claims, method-winner claims, or downstream claims.

## Artifact

- Script: `eval/bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment.py`
- Report: `artifacts/bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment/bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment_report.json`
