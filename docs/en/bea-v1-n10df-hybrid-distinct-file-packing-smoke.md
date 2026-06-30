# BEA-v1-N10DF Hybrid Distinct-File Packing Smoke

Date: 2026-06-30

BEA-v1-N10DF is a direct empirical same-source smoke over the scoped N1 span rows. It tests fixed, deterministic hybrid packing variants that preserve prefix evidence while adding distinct-file coverage. Gold is used only for after-the-fact evaluation.

## Result

```text
status: hybrid_distinct_file_packing_smoke_pass_n10dg_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
variant count: 5
zero-loss aggressive-equivalent hybrid: prefix7_then_distinct_fill_top10
N10DG authorized: true
```

## Variant metrics

| Variant | Role | file top10/top20 | span top10/top20 | Lost baseline span top10 |
| --- | --- | ---: | ---: | ---: |
| `baseline_existing_order` | reference | 14 / 19 | 13 / 17 | 0 |
| `aggressive_distinct_file_top20_greedy_then_top10` | reference | 19 / 47 | 16 / 24 | 1 |
| `max_per_file_2_top10` | reference | 16 / 19 | 15 / 17 | 0 |
| `prefix5_then_distinct_fill_top10` | hybrid | 19 / 20 | 16 / 18 | 1 |
| `prefix7_then_distinct_fill_top10` | hybrid | 17 / 19 | 16 / 17 | 0 |

The `prefix7_then_distinct_fill_top10` hybrid matches the aggressive top10 span count of 16 while avoiding the one baseline top10 span regression.

## Boundary

The smoke uses only existing candidate order and private file identity. It does not use gold, outcomes, miss direction, snippets, content, or raw paths as policy input. Candidate pool is preserved; there is no retrieval/rerun, candidate generation, candidate add/remove, selector/reranker execution, P5, BEA-v1-A, runtime/default promotion, method-winner claim, downstream-value claim, or broad private read.

## Artifact

- Script: `eval/bea_v1_n10df_hybrid_distinct_file_packing_smoke.py`
- Report: `artifacts/bea_v1_n10df_hybrid_distinct_file_packing_smoke/bea_v1_n10df_hybrid_distinct_file_packing_smoke_report.json`
