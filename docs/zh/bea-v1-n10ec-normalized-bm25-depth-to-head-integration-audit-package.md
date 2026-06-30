# BEA-v1-N10EC Normalized-BM25 Depth-to-Head Integration Audit Package

日期：2026-06-30

BEA-v1-N10EC 是 N10EB 的 public-only package。它只读取 N10EB public artifact，不进行 private reads、retrieval、OpenLocus execution 或 recompute。

## 结果

```text
status: normalized_bm25_depth_to_head_integration_audit_package_complete_n10ed_authorized
self-test: 8 / 8
forbidden scan: pass
private reads: 0
retrieval executions: 0
recomputes: 0
packaged baseline top10/top20/top50/top100: 5 / 11 / 17 / 26
packaged best top10: 11
success variants: 3
```

N10EC 打包 N10EB 的发现：把相对旧 N1 pool 新颖的 normalized-BM25 文件优先放前，可以把 depth-only source signal 转成 top10 recovery。最强 top10 规则达到 `11/60`，且没有丢失 baseline top10 hits。

这仍是 same-source smoke package，不是 runtime/default readiness、scaled retrieval、heldout/generalization、method-winner 或 downstream evidence。

## Handoff

N10EC 只授权 `BEA-v1-N10ED Novel-First Depth-to-Head Mechanism Analysis`。

## Artifact

- Script: `eval/bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package.py`
- Report: `artifacts/bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package/bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package_report.json`
