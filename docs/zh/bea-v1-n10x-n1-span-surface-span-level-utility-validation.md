# BEA-v1-N10X N1 Span-Surface Span-Level Utility Validation

日期：2026-06-29

BEA-v1-N10X 是对 N1 span-surface proxy 的 span-level direct empirical validation。它使用 same four N10T/N10V proxy arms 与 same recovered N1 span rows，但 primary metric 是与 private gold line ranges 的 overlap，而不是 file-level reach。

## 结果

```text
status: n1_span_surface_span_level_utility_validation_complete_below_threshold
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
span-evaluable denominator: 213
reachable file count: 52
span-reachable count: 12
best arm: span_extra_depth_promote_before_primary_prefix_4
best span-overlap top10: 9
best span-overlap top20: 10
best file top10/top20: 34 / 44
best delta span-overlap top10 vs baseline: 9
regressions: 0
threshold: delta >= 11 and regressions <= 3
threshold passed: false
```

## 解释

N10T 的 file-level proxy gain 是真实的 file-reach signal，但更严格的 span-level utility gate 未通过：best arm 的 span-overlap top-10 提升为 9 cases，低于 threshold 11。这不是 method-winner 或 runtime/default result。

## Boundary

N10X 只读取 scoped recovered N1 span rows，不读取其他 private files。它不公开 private paths、file names、contents、gold line ranges、spans、snippets、candidate lists、exact ranks、source hashes、provider payloads 或 raw rows。它不运行 retrieval，不 rerun P4L/N1/N2/N3，不执行 OpenLocus，不 generate/materialize candidates，不 add/remove candidates，不 search new arms，不运行 selector/reranker logic，不运行 support labeling，不进入 P5/BEA-v1-A，不运行 counterfactuals，也不推广 policy/runtime/default behavior。

## 决策

由于 validation completed below threshold，N10X 只授权 `BEA-v1-N10Y N1 Span-Surface Span-Level Utility Result Audit`。它不授权 runtime/default promotion、P5、BEA-v1-A、selector/reranker execution、retrieval/reruns、new arms、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10x_n1_span_surface_span_level_utility_validation.py`
- Report: `artifacts/bea_v1_n10x_n1_span_surface_span_level_utility_validation/bea_v1_n10x_n1_span_surface_span_level_utility_validation_report.json`
