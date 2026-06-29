# BEA-v1-N10BX Adapter Operating-Point Package

日期：2026-06-29

BEA-v1-N10BX 是 N10BW adapter operating-point smoke 的 public-only package。它只读取 public artifacts。不进行 private reads、不 recompute、不运行 retrieval/rerun/OpenLocus、不生成 candidates、不进行 existing evaluator hook-in，也不进行 runtime/default promotion。

## 结果

```text
status: adapter_operating_point_package_complete_n10by_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BX: 0
recomputes in N10BX: 0
N10BY authorized: true
```

## Packaged adapter operating point

N10BX 打包确认 N10BW 使用 default-off eval-only adapter/helper path 精确复现 `cost80_before25_after75`：

- N10BW private span rows read：`213`（N10BX 不读取）
- before/after windows：`20 / 60`
- cost proxy：`80`
- top10/top20 span overlap：`20 / 24`
- lost plateau core：`0`
- file-hit top10 count：`34`
- candidate pool/order changed：`false / false`
- existing evaluator hook/runtime default：`false / false`
- N10BS/N10BT/N10BU expected values matched：`true`

## Handoff

N10BX 只授权 `BEA-v1-N10BY Cost-Aware Operating-Point Exploratory Optimization`：same-source exploratory work over the scoped N1 span rows，重点是尝试在不丢失 20/24 的情况下降低 cost below 80，或以 moderate cost 提升 top10/top20 beyond 20/24。它不授权 runtime/default promotion、existing evaluator hook-in、heldout/generalization claims、method-winner claims、downstream-value claims、retrieval/rerun、candidate generation、selector/reranker execution、P5 或 BEA-v1-A。

## Artifact

- Script: `eval/bea_v1_n10bx_adapter_operating_point_package.py`
- Report: `artifacts/bea_v1_n10bx_adapter_operating_point_package/bea_v1_n10bx_adapter_operating_point_package_report.json`
