# BEA-v1-N10CB Same-File Span Cluster Bridge Audit Package

日期：2026-06-29

BEA-v1-N10CB 是 N10CA same-file span cluster bridge smoke 的 public-only audit/package。它只读取 public artifacts。不进行 private reads、不 recompute、不添加 new variants、不 adaptive tuning、不运行 retrieval/rerun/OpenLocus、不生成/添加/删除/重排 candidates，也不进行 runtime/default promotion。

## 结果

```text
status: cluster_bridge_audit_package_complete_n10cc_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10CB: 0
recomputes in N10CB: 0
N10CC authorized: true
```

## Packaged N10CA facts

- N10CA 已完成，包含 9 个预声明 variants。
- Top10-bridge variants 全部得到 top10/top20 `15 / 16`，并丢失 5 个 cost80 anchor top10 hits。
- Top20-bridge variants 全部得到 top10/top20 `15 / 19`，并丢失 5 个 cost80 anchor top10 hits。
- `top10_no_bridge_pad20` 得到 top10/top20 `15 / 16`，并丢失 5 个 cost80 anchor top10 hits。
- Best observed result 为 `15 / 19`，低于 cost80 anchor `20 / 24` 与 pm200 anchor `25 / 30`。
- `cluster_bridge_improves_anchor_count=0`，`cluster_bridge_cost_efficient_count=0`。
- Candidate pool/order 保持不变；没有 candidate add/remove/reorder；gold 未用于 cluster formation。

Mechanism conclusion：在预声明 variants 下，same-file cluster/bridge 弱于 local-window anchor。当前 same-source N1 surface 中的正向信号仍更像是 local single-candidate boundary expansion，而不是 multi-candidate bridging。

## Handoff

N10CB 只授权 `BEA-v1-N10CC Next Mechanism Search Outside Fixed-Window and Cluster-Bridge Families`。它不授权 runtime/default promotion、heldout/generalization claims、retrieval/rerun、candidate generation/add/remove/reorder、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10cb_cluster_bridge_audit_package.py`
- Report: `artifacts/bea_v1_n10cb_cluster_bridge_audit_package/bea_v1_n10cb_cluster_bridge_audit_package_report.json`
