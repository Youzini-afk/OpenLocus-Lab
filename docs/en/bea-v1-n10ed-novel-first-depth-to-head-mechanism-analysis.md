# BEA-v1-N10ED Novel-First Depth-to-Head Mechanism Analysis

Date: 2026-06-30

BEA-v1-N10ED explains why N10EB's novel-first repacking worked. It reads only N10EC/N10EB public artifacts plus the scoped N10DZ top100 private rows and N1 private rows. It does not run retrieval, OpenLocus, network, clone, provider calls, selector/reranker execution, candidate generation, or runtime/default changes.

## Result

```text
status: normalized_bm25_depth_to_head_mechanism_analysis_complete_n10ee_authorized
self-test: 13 / 13
forbidden scan: pass
case count: 60
baseline BM25 top10/top20/top50/top100: 5 / 11 / 17 / 26
novel-first top10/top20/top50/top100: 11 / 16 / 20 / 26
new top10 recovered vs baseline: 6
lost baseline top10: 0
remaining top10 miss: 49
recommended next phase: BEA-v1-N10EE Normalized-BM25 Novel-Guard Fixed Repacking Experiment
```

## Why novel-first worked

The 6 newly recovered top10 cases are all matched targets that are novel relative to the old N1 pool.

Their baseline source depths were:

```text
11-20: 1
21-50: 2
51-100: 3
```

After novel-first repacking, 3 moved into positions 1-5 and 3 moved into positions 6-10. Distinct-file controls recovered only 1 of the 6, so the main mechanism is not just generic file diversity; it is specifically old-pool novelty.

## Why 49 still miss

After novel-first, the remaining top10 misses split into:

```text
target in 11-20: 5
target in 21-50: 4
target in 51-100: 6
target absent from top100: 34
```

For all 15 present-but-not-top10 misses, the target is also novel relative to the old N1 pool. The problem is that many other novel files are ahead of it: 13 of these have more than 10 novel items ahead, and 2 have 6-10 novel items ahead. This supports a guarded novel-first follow-up rather than blindly putting all novel files first.

## Handoff

N10ED authorizes only N10EE: a fixed, gold-free novel-guard repacking experiment over the existing N10DZ top100 rows. It does not authorize new retrieval, scaled retrieval, runtime/default changes, selector/reranker execution, method-winner claims, downstream claims, or heldout/generalization claims.

## Artifact

- Script: `eval/bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis.py`
- Report: `artifacts/bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis/bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis_report.json`
