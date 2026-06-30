# BEA-v1-N10DC Distinct-File Packing Rank/File-Reach Smoke

Date: 2026-06-30

BEA-v1-N10DC is a direct empirical same-source rank/file-reach smoke over the scoped N1 span rows. It uses private candidate file identifiers as a gold-free observable policy feature, keeps the original candidate pool intact, and only repacks/reorders views within that pool. It does not generate, add, remove, or materialize candidates.

## Result

```text
status: distinct_file_packing_rank_file_reach_smoke_complete_n10dd_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
candidate generation/add/remove: 0 / 0 / 0
N10DD authorized: true
```

## Variant results

| Variant | Top10 file | Top20 file | Top10 span | Top20 span | Duplicate pressure reduced rows | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `baseline_existing_order` | 14 | 19 | 13 | 17 | 0 | baseline_existing_order |
| `distinct_file_top10_greedy` | 19 | 20 | 16 | 18 | 152 | span_regression_or_no_file_gain |
| `distinct_file_top20_greedy_then_top10` | 19 | 47 | 16 | 24 | 152 | span_regression_or_no_file_gain |
| `max_per_file_1_top10` | 19 | 20 | 16 | 18 | 152 | span_regression_or_no_file_gain |
| `max_per_file_2_top10` | 16 | 19 | 15 | 17 | 93 | improves_file_reach_without_span_regression |

Distinct-file packing improves top10 file reach from baseline `14` to `19` and top10 span from `13` to `16`, but the one-file-per-file variants lose 1 baseline top10 span hit. The top10-only variant reaches file/span top20 `20/18`; the top20-then-top10 variant exposes more top20 reach at `47/24`. The safer `max_per_file_2_top10` variant gives smaller but zero-loss gains: file `16/19` and span `15/17`. This is still a same-source N1 proxy result and not a runtime/default recommendation.

## Boundary

N10DC uses the existing `p4_evidence` pool only. Candidate pool is preserved; candidate generation, materialization, addition, and removal are all zero. Gold is used only for evaluation, not for packing. Public artifacts contain aggregate counts/buckets only and no private paths, filenames, spans, lines, snippets, gold rows, candidate lists, or exact ranks.

## Handoff

N10DC authorizes only `BEA-v1-N10DD Distinct-File Packing Rank/File-Reach Public Package`. It does not authorize runtime/default changes, heldout/generalization claims, retrieval/rerun, candidate generation/materialization/add/remove, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke.py`
- Report: `artifacts/bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke/bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke_report.json`
