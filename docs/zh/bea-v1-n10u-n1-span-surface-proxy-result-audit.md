# BEA-v1-N10U N1 Span-Surface Proxy Result Audit

日期：2026-06-29

BEA-v1-N10U 是对 N10T N1 span-surface proxy validation 的 public-artifact-only audit。它只读取 public N10T/N10R/N9 artifacts。它不读取 private rows，不扫描 private storage，不 recompute proxy result，不调用 N10T code，不运行 retrieval，不 rerun P4L/N1/N2/N3，不生成 candidates，不运行 selector/reranker logic，不进入 P5/BEA-v1-A，也不推广 runtime/default behavior。

## 结果

```text
status: n1_span_surface_proxy_result_audit_pass_n10v_authorized
self-test: 15 / 15
forbidden scan: pass
surface: n1_span_p4_evidence_order_proxy
proxy surface: true
N2-equivalent validation: false
eligible denominator: 213
reachable in pool: 52
baseline top10/top20: 0 / 0
best arm: span_extra_depth_promote_before_primary_prefix_4
best top10/top20: 34 / 44
best delta top10 vs baseline: 34
regressions: 0
threshold: delta >= 11 and regressions <= 3
threshold passed: true
```

## Audit findings

- N10T status 为 `n1_span_surface_rank_order_proxy_validation_pass_n10u_authorized`，且 forbidden scan 通过。
- Audited surface 明确是 `n1_span_p4_evidence_order_proxy`，其中 `proxy_surface_bool=true` 且 `n2_equivalent_validation_bool=false`。
- Result consistency 与 N10T 完全一致：eligible denominator 213、reachable-in-pool 52、baseline top10/top20 0/0、best arm `span_extra_depth_promote_before_primary_prefix_4`、best top10/top20 34/44、delta 34、regressions 0。
- Threshold audit 通过：observed delta 34 高于 threshold 11，observed regressions 0 低于 threshold 3。
- Privacy 与 claim boundaries 通过：无 private paths、file names、candidate lists、gold paths、spans、snippets、hashes、provider payloads、runtime/default claims、method-winner claims、downstream-value claims、P5 或 BEA-v1-A。

## 决策

N10U 只授权 `BEA-v1-N10V Independent Recompute N1 Span-Surface Proxy`，并要求使用 same private span rows。Broad private reads 仍未授权。N10U 不授权 runtime/default promotion、method-winner 声明、downstream-value 声明、P5、BEA-v1-A、selector/reranker execution、retrieval、reruns、new-arm search、counterfactuals 或 policy changes。

## Artifact

- Script: `eval/bea_v1_n10u_n1_span_surface_proxy_result_audit.py`
- Report: `artifacts/bea_v1_n10u_n1_span_surface_proxy_result_audit/bea_v1_n10u_n1_span_surface_proxy_result_audit_report.json`
