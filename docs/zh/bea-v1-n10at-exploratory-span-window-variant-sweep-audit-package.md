# BEA-v1-N10AT Exploratory Span-Window Variant Sweep Audit Package

日期：2026-06-29

BEA-v1-N10AT 是 N10AS exploratory span-window variant sweep 的 public-only audit/package。它只读取 public N10AS artifact。它不读取 private rows，不 recompute variants，不进行 extra sweeps，不运行 retrieval/reruns/OpenLocus，不生成 candidates，不进行 adaptive window tuning，也不作 runtime/default、heldout、method-winner 或 downstream-value claims。

## 结果

```text
status: exploratory_span_window_variant_sweep_audit_package_complete_n10au_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10AT: 0
variant recomputes in N10AT: 0
N10AU authorized: true
```

## Audited frontier tiers

N10AT 确认 public N10AS frontier tiers：

| Tier | Variant | top10/top20 | Cost proxy |
| --- | --- | --- | --- |
| low-cost frontier | `pm30` | 18 / 22 | 600 (`low`) |
| balanced frontier | `before25_after75` | 20 / 24 | 1000 (`medium`) |
| balanced frontier | `pm75` | 21 / 25 | 1500 (`medium`) |
| max-recall frontier | `pm200` | 25 / 30 | 4000 (`very_high`) |

该 package 保持 N10AS interpretation：仅 same-source N1 span-surface proxy，不是 heldout，不是 N2-equivalent，不是 runtime/default，不是 method winner，也不是 downstream-value evidence。

## Handoff

N10AT 只授权 `BEA-v1-N10AU Independent Recompute Exploratory Span-Window Variant Sweep`，范围是 same scoped private rows 与完整固定 15-variant grid。它不授权 extra sweeps、new variants、heldout validation claims、runtime/default changes、retrieval/rerun、candidate generation、adaptive tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package.py`
- Report: `artifacts/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package_report.json`
