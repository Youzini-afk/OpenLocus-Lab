# BEA-v1-N10DZ Normalized-BM25 Expanded Canary

Date: 2026-06-30

BEA-v1-N10DZ is a bounded same-source expanded canary for normalized BM25. It excludes the original 30 diagnostic cases, samples up to 60 corrected suffix-safe absent-pool cases, and runs only normalized BM25 with cap12 at top50 and top100 over existing local clones.

## Result

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

N10DZ remains an expanded canary, not a statistical generalization claim. It tests whether the N10DU/N10DX normalized-BM25 signal persists beyond the original 30-case diagnostic sample. The result is low-recovery by the top10 gate: top50/cap12 recovers only `5/60` at top10, below the pass threshold of 10. It still shows a candidate-source signal at depth: top50 recovers `17/60`, and top100/cap12 reaches `26/60`, again without improving top10. Pool-richness recovered counts in the artifact are scoped to each `(setting, topK)` record (`recovered_case_count_scope_bucket=setting_and_topk`). Public outputs are aggregate/bucket-only and contain no raw queries, paths, filenames, candidate lists, exact ranks, snippets, spans, or gold labels.

## Boundary

No network, git clone, provider, selector/reranker, P5, BEA-v1-A, runtime/default change, method/downstream claim, heldout/generalization claim, scaled full-denominator retrieval, or candidate generation/materialization is authorized.

## Artifact

- Script: `eval/bea_v1_n10dz_normalized_bm25_expanded_canary.py`
- Report: `artifacts/bea_v1_n10dz_normalized_bm25_expanded_canary/bea_v1_n10dz_normalized_bm25_expanded_canary_report.json`
