# BEA-v1-N10EF Normalized-BM25 Novel-Guard Experiment Package

Date: 2026-06-30

BEA-v1-N10EF packages N10EE without private reads or recompute. It locks the result boundary before the next experiment.

## Result

```text
status: normalized_bm25_novel_guard_experiment_package_complete_n10eg_authorized
self-test: 6 / 6
forbidden scan: pass
private reads: 0
recomputes: 0
baseline BM25 top10/top20/top50/top100: 5 / 11 / 17 / 26
full novel-first top10/top20/top50/top100: 11 / 16 / 20 / 26
guarded top5 novel-distinct top10/top20/top50/top100: 10 / 13 / 18 / 26
all tracked variants lost baseline top10: 0
```

## Meaning

Full novel-first is still the strongest observed same-source rule on this sample. The guarded top5 novel-distinct rule is more conservative but one top10 case weaker. This is a useful trade-off, not a default policy decision.

## Handoff

N10EF authorizes only N10EG: a bounded follow-up experiment over the same scoped N10DZ top100 rows and N1 rows. It does not authorize new retrieval, scaled retrieval, runtime/default changes, selector/reranker execution, method-winner claims, downstream claims, or heldout/generalization claims.

## Artifact

- Script: `eval/bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package.py`
- Report: `artifacts/bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package/bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package_report.json`
