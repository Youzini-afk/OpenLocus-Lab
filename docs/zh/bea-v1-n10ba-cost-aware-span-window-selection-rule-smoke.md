# BEA-v1-N10BA Cost-Aware Span-Window Selection Rule Smoke

日期：2026-06-29

BEA-v1-N10BA 是在 same scoped N1 span rows 上使用 predeclared cost-aware operating points 的 direct empirical smoke。它只评估 named operating points，不是 runtime defaults。它不使用 new window sizes，不进行 adaptive per-case selection，不运行 retrieval/rerun/OpenLocus，不生成或 materialize candidates，不运行 selector/reranker，也不进入 P5/BEA-v1-A。

## 结果

```text
status: cost_aware_span_window_selection_rule_smoke_complete_n10bb_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
operating points: 3
new window sizes: 0
adaptive per-case selection: 0
N10BB authorized: true
```

## Operating point results

| Operating point | Variant | top10/top20 span overlap | Delta top10/top20 vs baseline | Cost proxy | Lost previous hits |
| --- | --- | ---: | ---: | ---: | ---: |
| low_cost | pm30 | 18 / 22 | +9 / +12 | 600 (`low`) | 0 |
| balanced | before25_after75 | 20 / 24 | +11 / +14 | 1000 (`medium`) | 0 |
| max_recall | pm200 | 25 / 30 | +16 / +20 | 4000 (`very_high`) | 0 |

所有 operating points 的 candidate pool 与 candidate order 都保持不变。

## Boundary

N10BA 是 same-source N1 span-surface proxy smoke。三个 operating points 只是 evaluation 的 named choices，不是 default/runtime behavior。N10BA 不作 heldout/generalization、method-winner、downstream-value、selector/reranker、P5/BEA-v1-A、retrieval/rerun 或 runtime/default claim。

## Handoff

N10BA 只授权 `BEA-v1-N10BB Cost-Aware Span-Window Selection Rule Smoke Audit Package`，该阶段为 public-only audit/package。它不授权 same scoped rows 之外的 private reads、runtime/default promotion、new variants、adaptive selection、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、heldout/generalization claims、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke.py`
- Report: `artifacts/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke_report.json`
