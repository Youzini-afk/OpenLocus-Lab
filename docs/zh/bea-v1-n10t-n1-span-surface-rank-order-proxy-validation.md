# BEA-v1-N10T N1 Span-Surface Fixed-Pool Rank-Order Proxy Validation

日期：2026-06-29

BEA-v1-N10T 是 proxy/span-surface experiment，不是 N2-equivalent validation。它只读取一个 scoped private N1 span-surface row file，在已有 `p4_evidence` list order 上评估 fixed-pool order transforms，并只公开 scanner-safe aggregate buckets 与 counts。

## 结果

```text
status: n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized
self-test: 15 / 15
forbidden scan: pass
eligible denominator: 213
reachable in pool: 52
baseline top10 file reach: 0
best arm: span_extra_depth_promote_before_primary_prefix_4
best top10 file reach: 34
best top20 file reach: 44
best delta top10 vs baseline: 34
best regressions vs baseline: 0
threshold: delta >= 11 and regressions <= 3
```

## Boundary

N10T 只在 ordering 之后进行 file-level gold matching。它不公开 private paths、file names、content、spans、snippets、candidate lists、gold paths、exact ranks、source hashes、provider payloads 或 raw rows。它不读取其他 private files，不运行 retrieval，不 rerun P4L/N1/N2/N3，不执行 OpenLocus，不生成或 materialize candidates，不 add/remove candidates，不 search new arms，不运行 selector/reranker logic，不运行 support labeling，不进入 P5/BEA-v1-A，不改变 runtime/default policy，也不提出 method-winner/downstream-value 声明。

## Proxy arm results

- `baseline_n1_span_order`：top10 file reach 0，top20 file reach 0。
- `span_extra_depth_promote_before_primary_prefix_4`：top10 file reach 34，top20 file reach 44，delta +34，regressions 0。
- `span_bounded_interleave_primary2_extra1`：top10 file reach 17，top20 file reach 22，delta +17，regressions 0。
- `span_late_extra_depth_demote_after_primary_prefix_8`：top10 file reach 0，top20 file reach 0，delta 0，regressions 0。

## 决策

N10T 只授权 `BEA-v1-N10U N1 Span-Surface Proxy Result Audit`。它不授权 runtime/default promotion、P5、BEA-v1-A、selector/reranker execution、retrieval/reruns、candidate generation/materialization、method-winner 声明或 downstream-value 声明。

## Artifact

- Script: `eval/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation.py`
- Report: `artifacts/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation_report.json`
