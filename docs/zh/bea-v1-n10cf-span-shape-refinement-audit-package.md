# BEA-v1-N10CF Span-Shape Gated Refinement Audit Package

日期：2026-06-29

BEA-v1-N10CF 是 N10CE span-shape gated refinement sweep 的 public-only audit/package。它只读取 public artifacts，不进行 private reads、不 recompute，也不添加 new variants。

## 结果

```text
status: span_shape_refinement_package_complete_n10cg_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10CF: 0
recomputes in N10CF: 0
N10CG authorized: true
```

## Packaged refinement facts

- N10CE 已完成，包含 12 个 predeclared variants。
- Policy inputs 仅为 observable original span-length bucket 与 candidate-position bucket。
- Gold/outcome/miss direction/file identity/content 均未用作 policy inputs。
- Cost80 all-spans anchor：`20 / 24`，cost10/cost20 `800 / 1600`。
- Short50/150 anchor：`22 / 27`，cost10/cost20 `2000 / 4000`。
- pm200 all-spans global best：`25 / 30`，cost10/cost20 `4000 / 8000`。

Short-only ladder：

| Variant | top10/top20 | cost10/cost20 | Decision |
| --- | ---: | ---: | --- |
| short_only_before30_after90 | 20 / 24 | 1200 / 2400 | anchor_retained_no_improvement |
| short_only_before40_after120 | 21 / 25 | 1600 / 3200 | anchor_retained_no_improvement |
| short_only_before45_after135 | 21 / 26 | 1800 / 3600 | anchor_retained_no_improvement |
| short_only_before50_after150 | 22 / 27 | 2000 / 4000 | anchor_retained_no_improvement |
| short_only_before60_after180 | 23 / 27 | 2400 / 4800 | recall_improves_short_anchor |
| short_only_before75_after225 | 24 / 30 | 3000 / 6000 | recall_improves_short_anchor |

`short_only_before75_after225` 是 best short-span-gated frontier point，但不是 global best；pm200 仍是 global same-source top10/top20 maximum。没有更低成本的 variant 保持 short50/150 anchor。`recall_improves_short_anchor_count=2`，对应 60/180 与 75/225。

## Boundary

该 package 仅为 same-source N1 proxy evidence。它不是 heldout/generalization evidence，不是 runtime/default behavior，不是 retrieval/rerun，不是 candidate generation，不是 cluster/bridge，不是 adaptive tuning，不是 selector/reranker result，不是 P5/BEA-v1-A，也不是 method/downstream claim。

## Handoff

N10CF 只授权 `BEA-v1-N10CG Span-Shape Mechanism Follow-up`：在 same scoped rows 上使用 fixed/predeclared observable rules，调查 short75/225 (`24 / 30`) 与 pm200 (`25 / 30`) 之间的 gap，或寻找更便宜地保持 `24 / 30` 的机会。

## Artifact

- Script: `eval/bea_v1_n10cf_span_shape_refinement_audit_package.py`
- Report: `artifacts/bea_v1_n10cf_span_shape_refinement_audit_package/bea_v1_n10cf_span_shape_refinement_audit_package_report.json`
