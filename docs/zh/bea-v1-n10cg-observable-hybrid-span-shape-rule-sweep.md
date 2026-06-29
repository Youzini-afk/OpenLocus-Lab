# BEA-v1-N10CG Observable Hybrid Span-Shape Rule Sweep

日期：2026-06-29

BEA-v1-N10CG 是 direct empirical same-source sweep，用于测试 fixed observable hybrid span-shape rules 是否能缩小 `short75/225` 与 pm200 all-spans 之间的 gap。它只读取 same scoped N1 span rows，并且只使用 original span-length bucket 与 candidate-position bucket 作为 policy inputs。

## 结果

```text
status: observable_hybrid_span_shape_rule_sweep_complete_n10ch_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
variant count: 12
recovers pm200 at lower cost: 2
improves short frontier below pm200: 0
N10CH authorized: true
```

## Key findings

Anchors：

- `anchor_short75_225`：`24 / 30`，cost10/cost20 `3000 / 6000`。
- `anchor_pm200_all_spans`：`25 / 30`，cost10/cost20 `4000 / 8000`。

两个 fixed observable hybrid variants 以更低成本恢复或超过 pm200 aggregate：

- `short75_225_top3_all_pm200`：`25 / 31`，cost10/cost20 `3300 / 6300`，相对 pm200 节省 `700 / 1700`。
- `short75_225_top5_all_pm200`：`25 / 31`，cost10/cost20 `3500 / 6500`，相对 pm200 节省 `500 / 1500`。

其他 medium/long hybrid variants 以 cost10/cost20 `3000 / 6000` 保持 `24 / 30` short75/225 anchor。`short75_225_top10_all_pm200` 达到 `25 / 31`，但 top10 cost 没有低于 pm200，因此不计入 lower-cost recovery。

## Boundary

Policy inputs 限制为 original span-length buckets（`short`、`medium`、`long`）与 candidate-position buckets（`top3`、`top5`、`top10` 或 all positions）。N10CG 没有使用 gold/outcome/miss direction/file identity/content 作为 policy inputs；没有 reorder/add/remove candidates；没有运行 retrieval/rerun/OpenLocus；没有运行 cluster/bridge logic；也没有 adaptive tuning。这只是 same-source exploratory evidence，不是 heldout/generalization evidence，不是 runtime/default behavior，也不是 method/downstream claim。

## Handoff

N10CG 只授权 `BEA-v1-N10CH Observable Hybrid Span-Shape Rule Sweep Audit Package`，即 public audit/package。它不授权 private reads、new variants、runtime/default promotion、heldout/generalization claims、retrieval/rerun、candidate generation/add/remove/reorder、cluster/bridge execution、adaptive tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep.py`
- Report: `artifacts/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep_report.json`
