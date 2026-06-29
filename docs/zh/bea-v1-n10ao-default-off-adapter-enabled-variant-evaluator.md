# BEA-v1-N10AO Default-Off Adapter-Enabled Variant Evaluator Patch

日期：2026-06-29

BEA-v1-N10AO 新增一个 eval-only variant evaluator。它导入 N10AJ span projection adapter，保持 default-off，并且只在 explicit enablement 时读取 scoped N1 span rows。它不修改 existing N10T/N10X/N10AB/N1/N2/N3/P4L evaluators、runtime、retrieval、selector/reranker 或 configuration code。

本阶段 public artifact 使用 explicit scoped enablement 生成。Default mode 仍保持 disabled：默认不读取 private rows、不 recompute metrics，也不启用 adapter projection。

## 结果

```text
status: default_off_adapter_enabled_variant_evaluator_pass_n10ap_authorized
self-test: 16 / 16
forbidden scan: pass
explicit enablement used: true
default enabled: false
private read by default: false
private span rows read: 213
baseline top10/top20 span overlap: 9 / 10
pm50 top10/top20 span overlap: 19 / 23
delta top10 vs baseline: 10
original span-hit lost: 0
candidate pool changed: false
order changed: false
```

## Boundary

- 仅新增 eval-only variant evaluator。
- 导入 adapter，而不导入 N10AB/N10AD/N10T/N10X/N1/N2/N3/P4L evaluators。
- 需要 explicit scoped enablement 才读取 private rows 并运行 adapter projection。
- 使用固定 pm50 projection；没有 new arms、window tuning、retrieval、rerun、selector/reranker、runtime/default change、P5 或 BEA-v1-A。
- Public output 仅包含 aggregate counts；不公开 private paths、filenames、spans、line values、candidate lists、gold paths、snippets、hashes 或 raw rows。

## 决策

N10AO 只授权 `BEA-v1-N10AP Adapter-Enabled Variant Evaluator Result Audit Package`，即 public audit/package。N10AO 不授权 additional private reads、existing evaluator hook-in、modifying existing validated evaluators、runtime/default enablement、retrieval/rerun、candidate generation、new arms/window tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator.py`
- Report: `artifacts/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator_report.json`
