# BEA-v1-N10AN Default-Off Existing-Evaluator Hook Feasibility Preflight

日期：2026-06-29

BEA-v1-N10AN 是 public/static preflight。它判断下一步代码是否应将 eval-only adapter hook 到 existing validated evaluators。它读取 public N10AM/N10AL/N10AJ artifacts，并静态检查 adapter/helper 与 N10AB/N10X/N10T evaluator text。它不 import 或 execute candidate evaluators，不读取 private rows，不 patch hooks，也不改变 runtime/default behavior。

## 结果

```text
status: default_off_existing_evaluator_hook_feasibility_preflight_pass_n10ao_authorized
self-test: 14 / 14
forbidden scan: pass
selected strategy: new_adapter_enabled_variant_evaluator
direct existing-evaluator hook recommended: false
modify existing validated evaluator: false
runtime path hook: false
eval-only: true
default-off required: true
private reads: 0
candidate evaluator imports: 0
candidate evaluator executions: 0
hook patches: 0
```

## Static finding

候选 surface `n10ab_fixed_span_window_repair_smoke`、`n10x_span_level_utility_validation` 与 `n10t_span_surface_proxy_validation` 仅被静态检查。如果直接 patch，每个都有 medium mutation risk。因此本 preflight 拒绝 direct hook-in，并为 N10AO 选择 new adapter-enabled variant evaluator。

## 决策

N10AN 只授权 `BEA-v1-N10AO Default-Off Adapter-Enabled Variant Evaluator Patch`：新增一个导入 adapter 的 eval-only variant evaluator，要求 explicit default-off flag，仅在 explicit enablement 时允许 same scoped N1 span rows，并且不修改 existing N10T/N10X/N10AB evaluators。N10AN 不授权 existing evaluator hook-in、runtime/default enablement、retrieval/rerun、candidate generation、new arms/window tuning、selector/reranker、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight.py`
- Report: `artifacts/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight_report.json`
