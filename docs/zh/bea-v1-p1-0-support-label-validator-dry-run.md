# BEA-v1-P1-0 Support-Label Validator Dry Run

日期：2026-06-27

BEA-v1-P1-0 使用 synthetic private fixture 端到端验证 P0-5 private support-label harness。该 fixture 生成在 `.openlocus/research-private/` 下，并明确不是真实 label data。

## 结果

```text
status: support_label_validator_dry_run_pass
self-test: 6 / 6
forbidden scan: pass
synthetic labels validated: 18
```

Dry run 证明 private label schema、conjunction derivation、duplicate/id validation、sanitizer 与 public summary path 能端到端工作。它不填充真实 labels，也不执行 support counterfactual。

## 决策

P1-0 授权使用已验证 schema 与 harness 进行真实 private support labeling。Support counterfactual execution 仍被阻断，直到真实 private labels 完整且 scanner-validated。

P1-0 不授权 P5、BEA-v1-A、selector/reranker execution、implementation、runtime/default promotion、broad retrieval expansion、method-winner 声明、downstream-value 声明、support counterfactual execution 或 support marginal-utility 声明。

## Artifact

- Script：`eval/bea_v1_p1_0_support_label_validator_dry_run.py`
- Report：`artifacts/bea_v1_p1_0_support_label_validator_dry_run/bea_v1_p1_0_support_label_validator_dry_run_report.json`

