# BEA-v1-N10EJ Full-Only vs Guard-Only Difference Analysis

Date: 2026-06-30

BEA-v1-N10EJ analyzes the N10EG/N10EI full-only and guard-only difference using only the same scoped N10DZ top100 private rows and N1 rows. It recomputes membership for aggregate analysis only; it does not run retrieval, OpenLocus binary execution, candidate generation, network, runtime/default changes, or selector/reranker logic.

## Result

```text
status: full_guard_difference_analysis_complete_n10ek_authorized
self-test: 8 / 8
forbidden scan: pass
baseline top10: 5
full novel-first top10: 11
guarded top5 novel-distinct top10: 10
full/guard union top10: 13
full/guard intersection top10: 8
full-only: 3
guard-only: 2
```

## Difference buckets

The public artifact exposes only aggregate buckets. It does not publish paths, filenames, queries, candidates, gold labels, spans, or exact ranks.

- All full-only cases are in the `novel_count_gt_10` bucket.
- All guard-only cases are also in the `novel_count_gt_10` bucket.
- Full-only cases show a deep-displacement signal: `full_only_deep_displacement_hit = 3` and `full_only_not_deep_displacement_hit = 0`.
- Guard-only cases do not depend on preserving BM25 top5 hits in this sample: `guard_only_preserves_bm25_top5_hit = 0` and `guard_only_not_bm25_top5_preservation = 2`.
- Top5 duplicate pressure is mixed for both difference sets: full-only has 2 none / 1 one-duplicate; guard-only has 1 none / 1 one-duplicate.

## Meaning

The useful next rule should be difference-aware rather than a naive full/guard splice. Full-only gains are consistent with aggressive novel-first displacement from deeper BM25 buckets. Guard-only gains are not explained by preserving BM25 top5 hits here; they likely need a fixed rule that accounts for crowding/ordering pressure while retaining the guard's conservative diversity behavior.

## Handoff

N10EJ authorizes only N10EK fixed difference-aware combination experiment over the same rows. It does not authorize new/scaled retrieval, OpenLocus binary execution, candidate generation, network, runtime/default changes, selector/reranker execution, method-winner claims, downstream claims, or heldout/generalization claims.

## Artifact

- Script: `eval/bea_v1_n10ej_full_guard_difference_analysis.py`
- Report: `artifacts/bea_v1_n10ej_full_guard_difference_analysis/bea_v1_n10ej_full_guard_difference_analysis_report.json`
