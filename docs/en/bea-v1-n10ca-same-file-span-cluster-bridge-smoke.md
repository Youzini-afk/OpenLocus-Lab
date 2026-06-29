# BEA-v1-N10CA Same-File Span Cluster Bridge Smoke

Date: 2026-06-29

BEA-v1-N10CA is a direct empirical same-source smoke outside the fixed-window family. It reads only the same scoped N1 span rows and tests same-file span clustering/bridging over the N10T best-order evidence surface. It does not reorder, add, or remove candidates; gold is used only for evaluation.

## Result

```text
status: same_file_span_cluster_bridge_smoke_complete_n10cb_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
variant count: 9
best top10/top20: 15 / 19
cluster-bridge improvement variants: 0
N10CB authorized: true
```

## Variant findings

All nine predeclared variants completed with public aggregate output only:

| Variant | top10/top20 | delta vs cost80 | delta top10 vs pm200 | lost cost80 hits | cost bucket |
| --- | ---: | ---: | ---: | ---: | --- |
| top10_bridge20_pad20 | 15 / 16 | -5 / -8 | -10 | 5 | below_cost80 |
| top10_bridge50_pad20 | 15 / 16 | -5 / -8 | -10 | 5 | below_cost80 |
| top10_bridge100_pad20 | 15 / 16 | -5 / -8 | -10 | 5 | below_cost80 |
| top10_bridge200_pad20 | 15 / 16 | -5 / -8 | -10 | 5 | below_cost80 |
| top20_bridge20_pad20 | 15 / 19 | -5 / -5 | -10 | 5 | below_cost80 |
| top20_bridge50_pad20 | 15 / 19 | -5 / -5 | -10 | 5 | below_cost80 |
| top20_bridge100_pad20 | 15 / 19 | -5 / -5 | -10 | 5 | up_to_pm200 |
| top20_bridge200_pad20 | 15 / 19 | -5 / -5 | -10 | 5 | up_to_pm200 |
| top10_no_bridge_pad20 | 15 / 16 | -5 / -8 | -10 | 5 | below_cost80 |

Decision result: all variants are `cluster_bridge_no_improvement`. The same-file cluster bridge mechanism does not improve on the cost80 anchor or pm200 anchor in this same-source smoke.

## Boundary

N10CA is exploratory same-source N1 proxy research only. It is not heldout validation, not runtime/default behavior, not a method winner, and not downstream-value evidence.

## Handoff

N10CA authorizes only `BEA-v1-N10CB Same-File Span Cluster Bridge Audit Package`, a public audit/package. It does not authorize private reads, new variants, adaptive tuning, runtime/default promotion, heldout/generalization claims, method/downstream claims, retrieval/rerun, candidate generation/add/remove/reorder, selector/reranker execution, P5, or BEA-v1-A.

## Artifact

- Script: `eval/bea_v1_n10ca_same_file_span_cluster_bridge_smoke.py`
- Report: `artifacts/bea_v1_n10ca_same_file_span_cluster_bridge_smoke/bea_v1_n10ca_same_file_span_cluster_bridge_smoke_report.json`
