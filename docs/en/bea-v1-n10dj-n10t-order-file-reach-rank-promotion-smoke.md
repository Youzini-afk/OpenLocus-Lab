# BEA-v1-N10DJ N10T-Order File-Reach Rank-Promotion Smoke

Date: 2026-06-30

BEA-v1-N10DJ is a direct empirical same-source rank/file-reach smoke over the same scoped N1 span rows. It starts every variant from the N10T-best-order candidate list, changes only ordering within the existing pool, and evaluates both file reach and the fixed current-best span projection (`short75_225` plus top2 pm1000). It does not run retrieval/rerun/OpenLocus, generate/materialize/add/remove candidates, use selector/reranker logic, change runtime/default behavior, or make heldout/generalization, method-winner, or downstream-value claims.

## Result

```text
status: n10t_order_file_reach_rank_promotion_smoke_complete_n10dk_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
variant count: 8
anchor file top10/top20: 34 / 44
anchor projected span top10/top20: 30 / 36
N10DK authorized: true
```

## Metrics by variant

| Variant | file top10/top20 | projected span top10/top20 | Δ file top10 | Δ span top10 | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| anchor_n10t_order | 34 / 44 | 30 / 36 | 0 | 0 | no_rank_promotion_improvement |
| anchor_n10t_order_top2_pm1000_span_projection | 34 / 44 | 30 / 36 | 0 | 0 | no_rank_promotion_improvement |
| promote_rank11_20_before_rank6_10 | packaged aggregate | packaged aggregate | packaged | packaged | packaged |
| interleave_top10_with_rank11_20_1to1_after_top5 | packaged aggregate | packaged aggregate | packaged | packaged | packaged |
| promote_rank21_50_after_top5_before_rank6_10 | packaged aggregate | packaged aggregate | packaged | packaged | packaged |
| fill_top10_with_distinct_files_from_rank11_50 | packaged aggregate | packaged aggregate | packaged | packaged | packaged |
| fill_top10_with_distinct_files_from_rank11_100 | packaged aggregate | packaged aggregate | packaged | packaged | packaged |
| max_per_file_2_top10_on_n10t_order | packaged aggregate | packaged aggregate | packaged | packaged | packaged |

See the JSON artifact for exact aggregate counts for all eight variants. Public output is aggregate-only and contains no private paths, filenames, spans, lines, snippets, gold labels, candidate lists, or exact ranks.

## Boundary

Gold is used only after the fixed ordering/projection policies are applied. Candidate pool is preserved; candidate generation, addition, removal, and materialization are zero. N10DJ authorizes only `BEA-v1-N10DK Rank/File-Reach Rank-Promotion Public Package`.

## Artifact

- Script: `eval/bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke.py`
- Report: `artifacts/bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke/bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke_report.json`
