# BEA-v1-N10AC Fixed Span-Window Repair Smoke Result Audit

日期：2026-06-29

BEA-v1-N10AC 是对 N10AB fixed span-window repair smoke 的 public-only audit。它只读取 committed public artifacts。不读取 private rows，不 recompute outcomes，不运行 retrieval 或 OpenLocus，不生成 candidates，不 search new arms，不运行 selector/reranker logic，不进入 P5/BEA-v1-A，也不推广 runtime/default behavior。

## 结果

```text
status: fixed_span_window_repair_smoke_result_audit_complete_n10ad_authorized
self-test: 14 / 14
forbidden scan: pass
baseline unexpanded top10/top20 span overlap: 9 / 10
pm20 top10/top20 expanded span overlap: 15 / 19
pm50 top10/top20 expanded span overlap: 19 / 23
pm100 top10/top20 expanded span overlap: 21 / 25
pm50 delta top10 vs unexpanded: 10
pm50 threshold: 11
original span hit lost count: 0
```

## Audit findings

- N10AB status 为 `fixed_span_window_repair_smoke_pass_n10ac_authorized`，且 forbidden scan 通过。
- Primary pm50 variant 通过：top-10 expanded span overlap 为 19，top-20 为 23，baseline top-10/top-20 为 9/10，delta 为 +10，threshold 为 11，original span-hit loss 为 0。
- Sensitivity variants 稳定：pm20 达到 15/19，pm100 达到 21/25。
- Candidate pool unchanged，candidate additions/removals 为 0，gold 仅用于 evaluation，且 gold 与 miss direction 都不用于 window choice。

## Interpretation

Fixed local span-window expansion 可以在 N1 span-surface proxy 上恢复足够的 span overlap，并通过本 smoke。这不是 retrieval，不是 selector/reranker execution，不是 runtime/default policy，不是 downstream-value evidence，也不是 method-winner claim。

## 决策

N10AC 只授权 `BEA-v1-N10AD Independent Recompute Fixed Span-Window Repair Smoke`，使用 same private span rows 且仅限 scoped same-private-read permission。Broad private reads、runtime/default promotion、retrieval/reruns、candidate generation/materialization、new-arm search、selector/reranker execution、P5、BEA-v1-A、method-winner claims 与 downstream-value claims 均仍未授权。

## Artifact

- Script: `eval/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit.py`
- Report: `artifacts/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit_report.json`
