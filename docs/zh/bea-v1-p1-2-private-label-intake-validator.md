# BEA-v1-P1-2 Private Label Intake Validator

日期：2026-06-28

BEA-v1-P1-2 基于 P1-1 queue 验证 project-private support-label intake 路径。它检查 private queue rows 是否可从 `.openlocus/research-private/` 读取、是否匹配必需的 queue 与 private-label schemas、是否能和 public sanitized queue shape 对齐，以及是否能接收真实 private labels 且不公开 private ids 或 source-linkable data。

## 结果

```text
status: private_label_intake_validator_contract_pass
self-test: 8 / 8
forbidden scan: pass
valid private queue records: 18
valid real labels: 0
```

本轮未提供真实 private labels。因此 public artifact 只报告 validator contract、private queue intake manifest、private label intake manifest、gates，以及空的 sanitized real-label summaries。

## 决策

P1-2 只授权 private support-label intake validation。它不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、implementation、runtime/default promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## Artifact

- Script：`eval/bea_v1_p1_2_private_label_intake_validator.py`
- Report：`artifacts/bea_v1_p1_2_private_label_intake_validator/bea_v1_p1_2_private_label_intake_validator_report.json`
