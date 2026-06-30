# BEA-v1-N10DT Real Candidate-Source Canary Failure Mechanism Analysis

Date: 2026-06-30

BEA-v1-N10DT is an analysis-only follow-up to the N10DR bounded local candidate-source canary. It reads existing private canary rows/log buckets and the same scoped N1 span rows. It does not run new retrieval, OpenLocus, network, clone, provider, candidate generation, selector/reranker, or runtime/default changes.

## Result

```text
status: real_candidate_source_failure_analysis_complete_n10du_authorized
self-test: 12 / 12
forbidden scan: pass
private canary rows read: 30
same scoped N1 rows read: 213
zero candidate cases: 8
command failed cases: 2
nonzero no-gold cases: 20
gold top50: 0
N10DU authorized: targeted small canary only
```

## Findings

- Candidate overlap with the original N1 pool is bucketed; public output contains no candidate lists or filenames.
- Nonzero-result cases largely repeat/overlap the existing pool; returned channel metadata is bm25-only, and zero-candidate/failed cases create a reliability tail. The dominant interpretation is `source_repeats_existing_pool_with_channel_skew_and_query_mismatch`.
- Query shape and channel metadata are available only as buckets; raw queries are not public.
- A targeted channel/query-shape small canary is warranted, but scaled retrieval is not.

## Boundary

N10DT is analysis-only. It does not authorize scaled retrieval, network access, git clone, provider calls, candidate generation/materialization, selector/reranker execution, runtime/default changes, P5, BEA-v1-A, method-winner claims, downstream-value claims, heldout/generalization claims, or broad private reads.

## Handoff

N10DT authorizes only `BEA-v1-N10DU Targeted Candidate-Source Variant Canary` under scoped constraints.

## Artifact

- Script: `eval/bea_v1_n10dt_real_candidate_source_failure_analysis.py`
- Report: `artifacts/bea_v1_n10dt_real_candidate_source_failure_analysis/bea_v1_n10dt_real_candidate_source_failure_analysis_report.json`
