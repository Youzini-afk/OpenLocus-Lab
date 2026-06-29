# BEA-v1-N10AF Fixed Span-Window Repair Robustness/Subgroup Validation

日期：2026-06-29

BEA-v1-N10AF 是 fixed span-window repair smoke 的 direct empirical subgroup validation。它只读取 scoped recovered N1 span rows 以及 public N10AE/N10AD/N10AB/N10Z artifacts。它仅评估 predeclared target arm `span_extra_depth_promote_before_primary_prefix_4` 与 fixed primary repair variant `fixed_symmetric_span_expansion_pm50_lines`。

## 结果

```text
status: fixed_span_window_repair_robustness_validation_pass_n10ag_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
baseline top10 span overlap: 9
pm50 top10 span overlap: 19
delta top10 span overlap: 10
pm50 lost original span hits: 0
pm50 file top10 count: 34
positive-delta predeclared subgroups: 5
baseline-span-hit negative-delta subgroups: 0
```

## Subgroup signal

Global N10AE result 被精确复现。多个 predeclared subgroup families 出现 positive delta，包括：

- `baseline_file_hit_no_span_top10`：+10。
- `pm50_file_hit_top10`：+10。
- `not_span_reachable`：在 original unexpanded span-reach bucket 下 +10，反映 same-file non-overlap cases 的 window repair。
- `before_gold`：+9，`after_gold`：+1。
- Evidence-count buckets `21_50`：+8，`gt50`：+2。

`baseline_span_hit_top10` subgroup 的 delta 为 0，且没有 lost original span hits。

## Boundary

N10AF 不进行 adaptive window tuning，不 search new arms，不 add/remove candidates，不运行 retrieval/reruns，不执行 OpenLocus，不 generate/materialize candidates，不运行 selector/reranker logic，不进入 P5/BEA-v1-A，不运行 counterfactuals，不推广 runtime/default behavior，也不提出 method-winner/downstream-value claims。Public output 只包含 aggregate 与 subgroup counts/buckets。

## 决策

Robustness gate 通过：global metrics 匹配 N10AE，lost hits 为零，至少两个 predeclared subgroups 有 positive delta，且 baseline-span-hit subgroup 没有 negative delta。N10AF 只授权 `BEA-v1-N10AG Fixed Span-Window Repair Claim-Boundary Audit Package`，且仅为 public package/audit scope。

## Artifact

- Script: `eval/bea_v1_n10af_fixed_span_window_repair_robustness_validation.py`
- Report: `artifacts/bea_v1_n10af_fixed_span_window_repair_robustness_validation/bea_v1_n10af_fixed_span_window_repair_robustness_validation_report.json`
