# BEA-v1-N10CD Observable Span-Shape Gated Expansion Audit Package

日期：2026-06-29

BEA-v1-N10CD 是 N10CC observable span-shape gated expansion smoke 的 public-only audit/package。它只读取 public artifacts。不进行 private reads、不 recompute、不添加 new variants、不 adaptive tuning、不运行 retrieval/rerun/OpenLocus、不生成/添加/删除/重排 candidates、不执行 cluster/bridge，也不进行 runtime/default promotion。

## 结果

```text
status: observable_span_shape_package_complete_n10ce_authorized
self-test: 15 / 15
forbidden scan: pass
private reads in N10CD: 0
recomputes in N10CD: 0
N10CE authorized: true
```

## Packaged N10CC facts

- N10CC 已完成，包含 12 个预声明 variants。
- Policy inputs 仅为 observable original evidence span-length bucket 与 candidate position bucket。
- Gold/outcome、file identity、content/snippets 与 before/after direction 均未用作 policy inputs。
- Anchor `anchor_cost80_all_spans_before20_after60`：top10/top20 `20 / 24`，cost10 `800`，cost20 `1600`。
- Anchor `anchor_pm200_all_spans_before200_after200`：top10/top20 `25 / 30`，cost10 `4000`，cost20 `8000`。

Positive same-source variants：

| Variant | top10/top20 | cost10/cost20 | lost anchor | Decision |
| --- | ---: | ---: | ---: | --- |
| short_only_before50_after150 | 22 / 27 | 2000 / 4000 | 0 | recall_improves_anchor |
| short_medium_before50_after150 | 22 / 27 | 2000 / 4000 | 0 | recall_improves_anchor |
| top10_short_only_before50_after150 | 22 / 23 | 2000 / 2000 | 0 | recall_improves_anchor |
| anchor_pm200_all_spans_before200_after200 | 25 / 30 | 4000 / 8000 | 0 | recall_improves_anchor |

Summary：`cost_efficient_preserve_anchor_count=0`；`recall_improves_anchor_count=4`。这是新的 same-source exploratory positive signal：由 observable short span shape 门控的大窗口扩展，以低于 pm200 all-spans 的成本优于 cost80；但它不是 heldout/generalization evidence，不是 runtime/default behavior，也不是 method-winner claim。

## Handoff

N10CD 只授权 `BEA-v1-N10CE Span-Shape Refinement Sweep`：在 same scoped N1 rows 上继续用固定/预声明 variants 细化 short-span gated large-expansion cost/benefit boundary。它不授权 runtime/default promotion、heldout/generalization claims、retrieval/rerun、candidate generation/add/remove/reorder、cluster/bridge execution、adaptive tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10cd_observable_span_shape_audit_package.py`
- Report: `artifacts/bea_v1_n10cd_observable_span_shape_audit_package/bea_v1_n10cd_observable_span_shape_audit_package_report.json`
