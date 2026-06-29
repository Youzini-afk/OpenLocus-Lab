# BEA-v1-N10W N1 Span-Surface Proxy Replication Package

日期：2026-06-29

BEA-v1-N10W 是 N10T/N10U/N10V N1 span-surface proxy result 的 public replication/package 阶段。它不执行新实验：只读取 public artifacts，并打包已验证的 aggregate proxy result 与 claim boundary。

## 结果

```text
status: n1_span_surface_proxy_replication_package_complete
self-test: 15 / 15
forbidden scan: pass
chain: N10T pass -> N10U audit pass -> N10V recompute pass
surface: n1_span_p4_evidence_order_proxy
N2-equivalent validation: false
eligible denominator: 213
reachable in pool: 52
baseline top10/top20: 0 / 0
best arm: span_extra_depth_promote_before_primary_prefix_4
best top10/top20: 34 / 44
best delta top10 vs baseline: 34
regressions: 0
thresholds: 11 / 3
threshold passed: true
```

## Package boundary

N10W 只包含 public aggregate pointers 与 sanitized summary records。它不读取 private data，不 recompute outcomes，不运行 retrieval，不 rerun P4L/N1/N2/N3，不执行 OpenLocus，不 generate/materialize candidates，不 search new arms，不运行 selector/reranker logic，不进入 P5/BEA-v1-A，不运行 counterfactuals，不推广 runtime/default behavior，也不提出 method-winner/downstream-value 声明。

## Claim boundary

该 packaged result 只是 proxy/span-surface finding。它不是 N2-equivalent validation，不是 runtime/policy/default result，不是 method winner，也不是 downstream-value evidence。

## 决策

N10W 只授权 `BEA-v1-N10X N1 Span-Surface Stronger Validation Preflight`，scope 为 `preflight_only_no_execution`。Execution、private reads、recompute、runtime/default promotion、P5、BEA-v1-A、selector/reranker execution、retrieval/reruns、new-arm search、method-winner claims 与 downstream-value claims 均仍未授权。

## Artifact

- Script: `eval/bea_v1_n10w_n1_span_surface_proxy_replication_package.py`
- Report: `artifacts/bea_v1_n10w_n1_span_surface_proxy_replication_package/bea_v1_n10w_n1_span_surface_proxy_replication_package_report.json`
