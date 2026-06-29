# BEA-v1-N10AB Fixed Span-Window Repair Smoke

日期：2026-06-29

BEA-v1-N10AB 是 N10AA 授权的 direct empirical fixed span-window repair smoke。它只读取 scoped recovered N1 span rows，并在 N10T/N10X best arm order 上评估 fixed symmetric span expansion variants。

## 结果

```text
status: fixed_span_window_repair_smoke_pass_n10ac_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
baseline unexpanded top10 span overlap: 9
baseline unexpanded top20 span overlap: 10
top10 file-hit reference: 34
primary pm50 top10 expanded span overlap: 19
primary pm50 top20 expanded span overlap: 23
primary pm50 delta top10 vs unexpanded: 10
primary threshold: pm50 top10 expanded span overlap >= 11
original span hit lost count: 0
```

## Variant results

- `fixed_symmetric_span_expansion_pm20_lines`：top10 expanded span overlap 15，top20 19，delta +6，lost original hits 0。
- `fixed_symmetric_span_expansion_pm50_lines`：top10 expanded span overlap 19，top20 23，delta +10，lost original hits 0。
- `fixed_symmetric_span_expansion_pm100_lines`：top10 expanded span overlap 21，top20 25，delta +12，lost original hits 0。

## Boundary

N10AB 只使用 fixed symmetric windows。Gold 仅用于 evaluation，不用于选择 window size、移动 windows、content-aware adjustment、path changes、candidate addition/removal 或 arm selection。它不运行 retrieval，不 rerun P4L/N1/N2/N3，不执行 OpenLocus，不 generate/materialize candidates，不 add/remove candidates，不 search new arms，不运行 selector/reranker logic，不进入 P5/BEA-v1-A，不运行 counterfactuals，不推广 runtime/default behavior，也不提出 method-winner/downstream-value 声明。

## 决策

Primary pm50 variant 通过 N10AA threshold：19 >= 11。N10AB 只授权 `BEA-v1-N10AC Fixed Span-Window Repair Smoke Result Audit`，且仅为 public audit scope。不授权 runtime/default promotion 或 method/downstream claim。

## Artifact

- Script: `eval/bea_v1_n10ab_fixed_span_window_repair_smoke.py`
- Report: `artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json`
