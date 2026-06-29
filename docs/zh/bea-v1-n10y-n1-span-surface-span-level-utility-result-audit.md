# BEA-v1-N10Y N1 Span-Surface Span-Level Utility Result Audit

日期：2026-06-29

BEA-v1-N10Y 是对 N10X span-level utility validation 的 public-only audit。它不读取 private rows，不 recompute，也不执行新实验。

## 结果

```text
status: n1_span_surface_span_level_utility_result_audit_complete
self-test: 13 / 13
forbidden scan: pass
N10X status: n1_span_surface_span_level_utility_validation_complete_below_threshold
span-evaluable denominator: 213
reachable file count: 52
span-reachable count: 12
best arm: span_extra_depth_promote_before_primary_prefix_4
best span-overlap top10/top20: 9 / 10
best file top10/top20: 34 / 44
delta span-overlap top10: 9
regressions: 0
threshold: 11 / 3
threshold passed: false
fallback to file-level: false
```

## 解释

N10Y 确认 N10X 是 complete below-threshold empirical result，而不是 infrastructure failure。File-level proxy improvement 未通过更严格的 span-level utility gate：best span-overlap top-10 gain 为 9，低于 threshold 11。

## Boundary

N10Y 只读取 public artifacts。它不读取 private rows，不 recompute outcomes，不运行 retrieval，不 rerun P4L/N1/N2/N3，不执行 OpenLocus，不 generate/materialize candidates，不 search new arms，不运行 selector/reranker logic，不进入 P5/BEA-v1-A，不运行 counterfactuals，不推广 runtime/default behavior，也不提出 method-winner/downstream-value 声明。

## 决策

由于 span-level result 低于 threshold，N10Y 只授权 `BEA-v1-N10Z Span-Level Failure Decomposition Preflight`，且无 execution。Private reads、recompute、execution、runtime/default promotion、P5、BEA-v1-A、selector/reranker execution、retrieval/reruns、new-arm search、method-winner claims 与 downstream-value claims 均仍未授权。

## Artifact

- Script: `eval/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit.py`
- Report: `artifacts/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit_report.json`
