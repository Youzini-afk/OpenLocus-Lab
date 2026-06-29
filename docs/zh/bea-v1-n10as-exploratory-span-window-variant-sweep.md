# BEA-v1-N10AS Exploratory Span-Window Variant Sweep

日期：2026-06-29

BEA-v1-N10AS 是 existing N1 span-surface proxy 上的 same-source exploratory optimization。它只读取 scoped private N1 span rows，并使用已知最佳 N10T order（`span_extra_depth_promote_before_primary_prefix_4`）。它不 sweep rank/order arms。它不执行 retrieval、reruns、OpenLocus execution、candidate generation/materialization、selector/reranker logic、P5/BEA-v1-A、runtime/default promotion 或 downstream/method claims。

## 结果

```text
status: exploratory_span_window_variant_sweep_complete_n10at_authorized
self-test: 13 / 13
forbidden scan: pass
private span rows read: 213
variant count: 15
baseline unexpanded top10/top20: 9 / 10
max-recall frontier point: pm200
recommended top10/top20 span overlap: 25 / 30
recommended delta top10 vs unexpanded: 16
recommended cost proxy bucket: very_high
N10AT authorized: true
```

## Sweep design

Sweep 是固定且预声明的：symmetric `pm0`、`pm10`、`pm20`、`pm30`、`pm50`、`pm75`、`pm100`、`pm150`、`pm200`，以及 asymmetric `before75_after25`、`before100_after50`、`before150_after50`、`before25_after75`、`before50_after100`、`before50_after150`。

Frontier 是 trade-off curve，不是 default-policy recommendation：`pm30` 是 low-cost point（top10/top20 `18/22`），`before25_after75` 和 `pm75` 是 balanced points（`20/24` 和 `21/25`），`pm200` 是 max-recall point（`25/30`）且 cost proxy 为 very-high。单一 recommendation 字段只遵循预声明 exploratory rule：在 Pareto-frontier variants 中选择最高 top-10 count，并以较低 cost、再以 symmetric window 打破平局。没有 per-record adaptive window、gold-directed tuning、candidate addition/removal，也没有超过 N10T best order 的 candidate reorder。

## Claim boundary

N10AS 仅为 same-source、仅限 N1 span-surface proxy、不是 heldout、不是 N2-equivalent、不是 runtime/default、不是 method winner、也不是 downstream-value evidence。它只授权 `BEA-v1-N10AT Exploratory Span-Window Variant Sweep Audit Package`，即 public audit/package。它不授权 private reads、extra sweeps、heldout validation claims、runtime/default changes、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、adaptive tuning、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10as_exploratory_span_window_variant_sweep.py`
- Report: `artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json`
