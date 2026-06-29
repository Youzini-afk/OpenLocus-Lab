# BEA-v1-N10Z N1 Span-Surface Span-Level Failure Decomposition

Date: 2026-06-29

BEA-v1-N10Z is a direct empirical decomposition of the N10X below-threshold span-level result. It reads exactly the scoped recovered N1 span rows and uses only the N10X best arm, `span_extra_depth_promote_before_primary_prefix_4`, with the same N10T fixed-pool ordering semantics.

## Result

```text
status: n1_span_surface_span_level_failure_decomposition_complete_n10aa_authorized
self-test: 14 / 14
forbidden scan: pass
private span rows read: 213
best arm scope: span_extra_depth_promote_before_primary_prefix_4
top10 file-hit count: 34
top10 span-overlap count: 9
file-hit but no top10 span-overlap count: 25
span-reachable total: 12
```

## Decomposition

For the 25 top-10 same-file hits that do not also overlap the private gold span in top 10:

- `same_file_before_gold`: 17
- `same_file_after_gold`: 8
- `same_file_disjoint_unknown_order`: 0
- `same_file_malformed_or_missing_span`: 0
- `gold_line_schema_malformed`: 0
- `no_same_file_top10_despite_file_hit_in_record_bug`: 0

For the 12 rows with any span overlap in the fixed pool:

- `span_overlap_rank_1_10`: 9
- `span_overlap_rank_11_20`: 1
- `span_overlap_rank_21_50`: 2
- `span_overlap_rank_gt_50`: 0
- `span_overlap_not_ranked_or_missing`: 0

## Repair signal

The same-file/no-overlap buckets dominate the top-10 gap: 25/25 misses are same-file spans that land before or after the gold span window. This supports a span-window repair preflight, not immediate repair execution.

## Boundary

N10Z publishes bucket counts only. It does not publish private paths, file names, contents, gold lines, spans, snippets, candidate lists, exact ranks, source hashes, provider payloads, or raw rows. It does not run retrieval, rerun P4L/N1/N2/N3, execute OpenLocus, generate/materialize candidates, add/remove candidates, search new arms, run selector/reranker logic, perform support labeling, enter P5/BEA-v1-A, run counterfactuals, promote runtime/default behavior, or make method-winner/downstream-value claims.

## Decision

N10Z authorizes only `BEA-v1-N10AA Span-Window Repair Preflight` as design/preflight only. Repair execution, retrieval/reruns, runtime/default promotion, P5, BEA-v1-A, selector/reranker execution, method-winner claims, and downstream-value claims remain unauthorized.

## Artifact

- Script: `eval/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition.py`
- Report: `artifacts/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition_report.json`
