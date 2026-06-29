# BEA-v1-N10CA Same-File Span Cluster Bridge Smoke

日期：2026-06-29

BEA-v1-N10CA 是 fixed-window family 之外的 direct empirical same-source smoke。它只读取同一个 scoped N1 span rows，并在 N10T best-order evidence surface 上测试 same-file span clustering/bridging。它不 reorder、add 或 remove candidates；gold 只用于 evaluation。

## 结果

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

9 个预声明 variants 全部完成，且只输出 public aggregate：

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

Decision result：所有 variants 均为 `cluster_bridge_no_improvement`。在该 same-source smoke 中，same-file cluster bridge mechanism 没有优于 cost80 anchor 或 pm200 anchor。

## Boundary

N10CA 仅为 exploratory same-source N1 proxy research。它不是 heldout validation，不是 runtime/default behavior，不是 method winner，也不是 downstream-value evidence。

## Handoff

N10CA 只授权 `BEA-v1-N10CB Same-File Span Cluster Bridge Audit Package`，即 public audit/package。它不授权 private reads、new variants、adaptive tuning、runtime/default promotion、heldout/generalization claims、method/downstream claims、retrieval/rerun、candidate generation/add/remove/reorder、selector/reranker execution、P5 或 BEA-v1-A。

## Artifact

- Script: `eval/bea_v1_n10ca_same_file_span_cluster_bridge_smoke.py`
- Report: `artifacts/bea_v1_n10ca_same_file_span_cluster_bridge_smoke/bea_v1_n10ca_same_file_span_cluster_bridge_smoke_report.json`
