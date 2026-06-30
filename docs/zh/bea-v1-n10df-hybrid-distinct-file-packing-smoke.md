# BEA-v1-N10DF Hybrid Distinct-File Packing Smoke

日期：2026-06-30

BEA-v1-N10DF 是在 scoped N1 span rows 上进行的 direct empirical same-source smoke。它测试 fixed、deterministic hybrid packing variants，用来保留 prefix evidence，同时增加 distinct-file coverage。Gold 仅用于事后 evaluation。

## 结果

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

`prefix7_then_distinct_fill_top10` hybrid 达到 aggressive 的 top10 span count 16，同时避免了那 1 个 baseline top10 span regression。

## Boundary

该 smoke 只使用 existing candidate order 与 private file identity。它不把 gold、outcomes、miss direction、snippets、content 或 raw paths 用作 policy input。Candidate pool 保持不变；没有 retrieval/rerun、candidate generation、candidate add/remove、selector/reranker execution、P5、BEA-v1-A、runtime/default promotion、method-winner claim、downstream-value claim 或 broad private read。

## Artifact

- Script: `eval/bea_v1_n10df_hybrid_distinct_file_packing_smoke.py`
- Report: `artifacts/bea_v1_n10df_hybrid_distinct_file_packing_smoke/bea_v1_n10df_hybrid_distinct_file_packing_smoke_report.json`
