# BEA-v1-N10AE Fixed Span-Window Repair Replication Package

日期：2026-06-29

BEA-v1-N10AE 是 N10AB/N10AC/N10AD fixed span-window repair chain 的 public-only replication package。它只读取 public artifacts。不进行 private reads、recompute、retrieval/rerun、OpenLocus execution、candidate generation/materialization、new-arm search、selector/reranker execution、P5/BEA-v1-A、runtime/default promotion、method-winner claim 或 downstream-value claim。

## 结果

```text
status: fixed_span_window_repair_replication_package_complete_n10af_authorized
self-test: 15 / 15
forbidden scan: pass
N10AB: pass
N10AC: audit complete
N10AD: independent recompute pass
aggregate comparison: match
N10AB code call count in N10AD: 0
baseline unexpanded top10/top20 span overlap: 9 / 10
pm20 top10/top20 expanded span overlap: 15 / 19
pm50 top10/top20 expanded span overlap: 19 / 23
pm50 delta top10 vs unexpanded: 10
pm50 threshold: 11
pm100 top10/top20 expanded span overlap: 21 / 25
original span hit lost count: 0
candidate pool changed: false
```

## Replication chain

- N10AB 执行 fixed-window repair smoke 并通过。
- N10AC 审计 N10AB public result 并确认有效。
- N10AD 在 same scoped private span rows 上独立 recompute same fixed-window smoke，在不 import/call N10AB code 的情况下匹配 N10AB aggregate metrics。

## Claim boundary

本 package 只支持 N1 span-surface proxy 上的 fixed local span-window expansion 结果。它不是 retrieval，不是 selector/reranker execution，不是 N2-equivalent validation，不是 runtime/default policy，不是 method-winner claim，也不是 downstream-value evidence。

## 决策

N10AE 只授权 `BEA-v1-N10AF Next-Step Selection Stronger Validation Preflight`。它不授权 private reads、runtime/default promotion、retrieval/reruns、candidate generation/materialization、new-arm search、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10ae_fixed_span_window_repair_replication_package.py`
- Report: `artifacts/bea_v1_n10ae_fixed_span_window_repair_replication_package/bea_v1_n10ae_fixed_span_window_repair_replication_package_report.json`
