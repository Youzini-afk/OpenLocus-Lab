# BEA-v1-N10BW Adapter Operating-Point Smoke for cost80_before25_after75

日期：2026-06-29

BEA-v1-N10BW 是使用现有 default-off eval-only adapter path 复现 selected operating point `cost80_before25_after75` 的 empirical smoke。该 label 表示 fixed ratio 25/75 且 total cost proxy 80，即 before-window 20、after-window 60。这不是 runtime/default integration，也不 hook existing evaluators。

## 结果

```text
status: adapter_operating_point_smoke_pass_n10bx_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
operating point: cost80_before25_after75
before/after windows: 20 / 60
top10/top20 span overlap: 20 / 24
lost plateau core: 0
file-hit top10 count: 34
candidate pool/order changed: false / false
N10BX authorized: true
```

## Adapter boundary

N10BW imports default-off eval-only adapter/helper path，不 import、call 或 hook existing N10BS/N10BU evaluators。Adapter copy path 是 default-off；该 smoke 仅对单个预声明 operating point 本地应用 fixed operating-point projection。它不进行 runtime/default hook，也不进行 existing evaluator hook-in。

## Comparison

Adapter-produced operating-point aggregate 匹配 N10BS/N10BT/N10BU public expectations：top10/top20 `20/24`，lost plateau core `0`，cost proxy `80`，file-hit top10 count `34`，candidate pool/order unchanged。

## Handoff

N10BW 只授权 `BEA-v1-N10BX Adapter Operating-Point Package`，即 public audit/package。它不授权 runtime/default promotion、existing evaluator hook-in、new variants、adaptive tuning、broad private reads、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、heldout/generalization claims、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10bw_adapter_operating_point_smoke.py`
- Report: `artifacts/bea_v1_n10bw_adapter_operating_point_smoke/bea_v1_n10bw_adapter_operating_point_smoke_report.json`
