# BEA-v1-N10BB Cost-Aware Span-Window Selection Rule Smoke Audit Package

日期：2026-06-29

BEA-v1-N10BB 是 N10BA cost-aware span-window selection rule smoke 的 public-only audit/package。它只读取 public artifacts。它不读取 private rows，不 recompute metrics，不添加 variants，不进行 adaptive tuning，不运行 retrieval/reruns/OpenLocus，不生成或 materialize candidates，不 hook existing evaluators，也不改变 runtime/default behavior。

## 结果

```text
status: cost_aware_selection_rule_smoke_audit_package_complete_n10bc_authorized
self-test: 16 / 16
forbidden scan: pass
private reads in N10BB: 0
recomputes in N10BB: 0
N10BC authorized: true
```

## Packaged operating points

| Operating point | Variant | top10/top20 span overlap | Delta top10/top20 vs baseline | Cost proxy | Lost previous hits |
| --- | --- | ---: | ---: | ---: | ---: |
| low_cost | pm30 | 18 / 22 | +9 / +12 | 600 (`low`) | 0 |
| balanced | before25_after75 | 20 / 24 | +11 / +14 | 1000 (`medium`) | 0 |
| max_recall | pm200 | 25 / 30 | +16 / +20 | 4000 (`very_high`) | 0 |

所有 packaged operating points 都保持 candidate pool 与 order 不变。Rule boundary 仍是 named operating points only，不是 defaults；没有 adaptive per-case selection，也没有 new variant。

## Adapter and claim boundary

N10BB 确认 N10BA adapter/helper-only path：没有 existing evaluator import/call/hook-in，也没有 runtime/default hook。该 package 只是 same-source N1 span-surface proxy evidence。它不作 heldout/generalization、N2-equivalent、runtime/default、method-winner、downstream-value、selector/reranker、P5/BEA-v1-A、retrieval/rerun、candidate-generation、new-variant 或 adaptive-selection claim。

## Handoff

N10BB 只授权 `BEA-v1-N10BC Operating-Point Tradeoff Decomposition`：same scoped N1 span rows，无 new variants，并且只对 low_cost、balanced 与 max_recall operating points 输出 public bucket/count。N10BB 本身是 public-only，不进行 private read 或 recompute。

## Artifact

- Script: `eval/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package.py`
- Report: `artifacts/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package_report.json`
