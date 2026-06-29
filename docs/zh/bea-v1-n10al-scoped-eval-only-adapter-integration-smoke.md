# BEA-v1-N10AL Scoped Eval-Only Adapter Integration Smoke

日期：2026-06-29

BEA-v1-N10AL 是 default-off span projection adapter 的 empirical eval-only integration smoke。它使用 same scoped N1 span rows 与 N10AJ adapter 来复现 N10AB pm50 result。它不是 runtime integration，也不 hook existing evaluators。

## 结果

```text
status: scoped_eval_only_adapter_integration_smoke_pass_n10am_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
baseline top10/top20 span overlap: 9 / 10
pm50 top10/top20 span overlap: 19 / 23
delta top10 vs baseline: 10
original span-hit lost: 0
candidate pool changed: false
order changed: false
matches N10AB/N10AD: true
```

## Boundary

N10AL 只导入 eval-only projection adapter 进行 span projection。它不 import 或 call N10AB、N10AD、N10T、N10X、N1、N2、N3、P4L、runtime、retrieval、selector 或 reranker modules。它只对 recovered N1 span rows 执行一次 scoped private read，只计算 aggregate counts，并且不公开 paths、spans、snippets、content、gold lines、candidate lists 或 exact ranks。

## 决策

N10AL 只授权 `BEA-v1-N10AM Eval-Only Adapter Integration Result Audit Package`。它不授权 existing evaluator hook-in、runtime/default enablement、下一阶段 private reads、retrieval/rerun、candidate generation/materialization、new arms/window tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke.py`
- Report: `artifacts/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke_report.json`
