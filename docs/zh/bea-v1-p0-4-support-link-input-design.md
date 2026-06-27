# BEA-v1-P0-4 Support-Link Input Design

日期：2026-06-27

BEA-v1-P0-4 将 P0-1/P0-2 的 support-link 缺口转换为 scanner-validated labeling input contract。它不标注 private rows，不执行 counterfactual，不调用 provider，不运行 retrieval，也不实现 policy。

## 结果

```text
status: support_link_input_design_pass
self-test: 8 / 8
forbidden scan: pass
support-link design records: 18
label contract fields: 6
```

该 artifact 将 P0-1 的 `support_link_trace` gaps 与 P0-2 的 18 个 `blocked_missing_label` matrix cells join 起来。它只发布 sanitized design rows 与 labeling contract。所有 target/support hit states 仍为 `unknown_not_labeled`；本阶段只是 input design。

## Contract

公开 contract 定义这些 label fields：

- `support_relation_bucket`
- `target_hit_bucket`
- `support_hit_bucket`
- `conjunction_bucket`
- `support_evidence_role_bucket`
- `leakage_risk_bucket`

这些字段用于支持后续 counterfactual phase，同时不暴露 raw paths、snippets、candidates、ranks、scores、task IDs、private record IDs、provider payloads 或 source-linkable private data。

## 决策

P0-4 只授权 support-link labeling input work。后续 phase 可以使用该 contract 标注 private rows，然后再判断是否执行 support counterfactual。它不授权 P5、BEA-v1-A、selector/reranker execution、implementation、runtime/default promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## Artifact

- Script：`eval/bea_v1_p0_4_support_link_input_design.py`
- Report：`artifacts/bea_v1_p0_4_support_link_input_design/bea_v1_p0_4_support_link_input_design_report.json`

