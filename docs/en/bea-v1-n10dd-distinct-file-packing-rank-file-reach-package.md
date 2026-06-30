# BEA-v1-N10DD Distinct-File Packing Rank/File-Reach Public Package

Date: 2026-06-30

BEA-v1-N10DD is a public-only package of the corrected N10DC distinct-file packing smoke. It reads public artifacts only, performs no private reads, and does not recompute policy outcomes.

## Result

```text
status: distinct_file_packing_rank_file_reach_package_complete_n10de_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10DD: 0
recomputes in N10DD: 0
N10DE authorized: true
```

## Packaged N10DC facts

N10DC used corrected safe same/suffix private reference matching for evaluation and topK-only packing semantics over the existing candidate pool.

| Variant | File top10/top20 | Span top10/top20 | Delta top10 file/span | Lost baseline top10 span |
| --- | ---: | ---: | ---: | ---: |
| `baseline_existing_order` | 14 / 19 | 13 / 17 | 0 / 0 | 0 |
| `distinct_file_top10_greedy` | 19 / 20 | 16 / 18 | +5 / +3 | 1 |
| `distinct_file_top20_greedy_then_top10` | 19 / 47 | 16 / 24 | +5 / +3 | 1 |
| `max_per_file_1_top10` | 19 / 20 | 16 / 18 | +5 / +3 | 1 |
| `max_per_file_2_top10` | 16 / 19 | 15 / 17 | +2 / +2 | 0 |

Candidate generation, materialization, addition, and removal are all zero; the candidate pool is preserved.

## Tradeoff summary

- Aggressive one-file-per-file packing improves top10 file reach by +5 and gives the strongest top20 file reach, but incurs 1 baseline top10 span regression.
- Conservative `max_per_file_2_top10` provides smaller top10 file/span gains (+2/+2) but has zero baseline top10 span regression.

## Handoff

N10DD authorizes only `BEA-v1-N10DE Regression-vs-Zero-Loss Mechanism Decomposition`. N10DE may read the same scoped N1 rows only to decompose this tradeoff. N10DD itself performs no private read or recompute and does not authorize runtime/default changes, heldout/generalization, retrieval/rerun, candidate generation/materialization/add/remove, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10dd_distinct_file_packing_rank_file_reach_package.py`
- Report: `artifacts/bea_v1_n10dd_distinct_file_packing_rank_file_reach_package/bea_v1_n10dd_distinct_file_packing_rank_file_reach_package_report.json`
