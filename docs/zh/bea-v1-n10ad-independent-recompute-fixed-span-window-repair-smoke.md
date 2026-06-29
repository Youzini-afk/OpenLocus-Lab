# BEA-v1-N10AD Independent Recompute Fixed Span-Window Repair Smoke

日期：2026-06-29

BEA-v1-N10AD 在 same scoped recovered N1 span rows 上独立 recompute N10AB fixed span-window repair smoke。它独立实现 row parsing、best-arm ordering 与 fixed-window overlap evaluation，并且仅使用 N10AB/N10AC public artifacts 做 aggregate comparison。

## 结果

```text
status: independent_recompute_fixed_span_window_repair_smoke_pass_n10ae_authorized
self-test: 17 / 17
forbidden scan: pass
private span rows read: 213
baseline unexpanded top10/top20 span overlap: 9 / 10
pm20 top10/top20 expanded span overlap: 15 / 19
pm50 top10/top20 expanded span overlap: 19 / 23
pm100 top10/top20 expanded span overlap: 21 / 25
pm50 delta top10 vs unexpanded: 10
original span hit lost count: 0
aggregate comparison to N10AB: match
N10AB code call count: 0
```

## Boundary

N10AD 只读取 scoped private N1 span-row input，不读取其他 private files。它不 import 或 call N10AB evaluator 或其 transform functions。不运行 retrieval/reruns、OpenLocus execution、candidate generation/materialization、candidate add/remove、new arms、selector/reranker、P5、BEA-v1-A、runtime/default promotion、method-winner claims 或 downstream-value claims。

## 决策

Independent recompute 在 baseline、pm20、pm50 与 pm100 aggregate metrics 上与 N10AB 完全匹配。N10AD 只授权 `BEA-v1-N10AE Fixed Span-Window Repair Replication Package`，该阶段为 public package，不授权 private-read 或 execution。

## Artifact

- Script: `eval/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke.py`
- Report: `artifacts/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke_report.json`
