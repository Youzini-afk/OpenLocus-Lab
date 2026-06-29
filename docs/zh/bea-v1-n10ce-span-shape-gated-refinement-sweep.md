# BEA-v1-N10CE Span-Shape Gated Refinement Sweep

日期：2026-06-29

BEA-v1-N10CE 是对 N10CC short-span gated expansion signal 的 direct empirical same-source refinement。它读取同一个 scoped N1 span rows，并且只使用 observable original span-length 与 candidate-position buckets 作为 policy inputs。Gold 只用于 evaluation。

## 结果

```text
status: span_shape_gated_refinement_sweep_complete_n10cf_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
variant count: 12
cheaper-preserves-short-anchor variants: 0
recall-improves-short-anchor variants: 2
N10CF authorized: true
```

## Key findings

Anchors：

- `anchor_cost80_all_spans_before20_after60`：`20 / 24`，cost10/cost20 `800 / 1600`。
- `anchor_short_only_before50_after150`：`22 / 27`，cost10/cost20 `2000 / 4000`。
- `anchor_pm200_all_spans_before200_after200`：`25 / 30`，cost10/cost20 `4000 / 8000`。

Refinement results 显示平滑的 short-span cost/recall ladder：

- `short_only_before30_after90`：`20 / 24`，cost10 `1200`。
- `short_only_before40_after120`：`21 / 25`，cost10 `1600`。
- `short_only_before45_after135`：`21 / 26`，cost10 `1800`。
- `short_only_before50_after150`：`22 / 27`，cost10 `2000`。
- `short_only_before60_after180`：`23 / 27`，cost10 `2400`，decision `recall_improves_short_anchor`。
- `short_only_before75_after225`：`24 / 30`，cost10 `3000`，decision `recall_improves_short_anchor`。
- `short_medium_before40_after120`：`21 / 25`，cost10 `1600`。

没有 variant 以更低成本保持 short50/150 anchor。两个 variants 在低于 pm200 成本时改善 short anchor：`short_only_before60_after180` 与 `short_only_before75_after225`。

## Boundary

N10CE 没有使用 gold/outcome/miss direction/file identity/content 作为 policy inputs。它没有 reorder、add 或 remove candidates；没有运行 retrieval/rerun/OpenLocus；没有执行 cluster/bridge logic；也没有 adaptive tuning。这只是 same-source exploratory research，不是 heldout evidence，不是 runtime/default behavior，也不是 method/downstream claim。

## Handoff

N10CE 只授权 `BEA-v1-N10CF Span-Shape Gated Refinement Audit Package`，即 public audit/package。它不授权 private reads、new variants、runtime/default promotion、heldout/generalization claims、retrieval/rerun、candidate generation/add/remove/reorder、cluster/bridge execution、adaptive tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10ce_span_shape_gated_refinement_sweep.py`
- Report: `artifacts/bea_v1_n10ce_span_shape_gated_refinement_sweep/bea_v1_n10ce_span_shape_gated_refinement_sweep_report.json`
