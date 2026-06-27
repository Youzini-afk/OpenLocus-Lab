# BEA-v1-P0-5 Support-Link Labeling Harness

日期：2026-06-27

BEA-v1-P0-5 将 P0-4 的 support-link input contract 转换为 private labeling harness。它可以在 `.openlocus/research-private/` 下生成未标注 JSONL template，也可以验证已完成的 private label JSONL，同时不暴露 raw rows。

本阶段不自行标注 records，不执行 support counterfactual，不调用 provider，不运行 retrieval，也不实现 policy。

## 结果

```text
status: support_link_labeling_harness_contract_pass
self-test: 9 / 9
forbidden scan: pass
harness records: 18
private template rows: 18
private labels supplied: false
```

Public artifact 只包含 sanitized harness rows、summary gates 与 private-template manifest。生成的 private template 位于 ignored 的项目内 research-private directory，不会提交。

## Private Schema

Private label rows 使用 schema `bea_v1_p0_5_support_link_private_label.v1`，需要 P0-4 label fields 与 annotation status。Harness 会验证枚举值、重复 design IDs、未知 design IDs，以及 `conjunction_bucket` 是否由 `target_hit_bucket` 和 `support_hit_bucket` 推导得到。

## 决策

P0-5 补齐 private labeling harness contract，但没有补齐 labels 本身。后续 phase 可以填写 private template，并用 `--private-labels-jsonl` 重跑该 harness；在 private labels 完整且 scanner-validated 之前，support counterfactual execution 仍未授权。

P0-5 不授权 P5、BEA-v1-A、selector/reranker execution、implementation、runtime/default promotion、broad retrieval expansion、method-winner 声明、downstream-value 声明、support counterfactual execution 或 support marginal-utility 声明。

## Artifact

- Script：`eval/bea_v1_p0_5_support_link_labeling_harness.py`
- Report：`artifacts/bea_v1_p0_5_support_link_labeling_harness/bea_v1_p0_5_support_link_labeling_harness_report.json`

